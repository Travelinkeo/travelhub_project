# Archivo: core/management/commands/migrar_facturas_venezuela.py
"""
Comando para migrar facturas existentes al nuevo formato venezolano.
Convierte facturas básicas en FacturaVenezuela con campos fiscales completos.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal

from core.models.facturacion import Factura, ItemFactura
from core.models.facturacion_venezuela import FacturaVenezuela, ItemFacturaVenezuela
from core.models_catalogos import Moneda


class Command(BaseCommand):
    help = 'Migra facturas existentes al formato venezolano con campos fiscales'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la migración sin hacer cambios reales',
        )
        
        parser.add_argument(
            '--factura-id',
            type=int,
            help='Migra solo una factura específica por ID',
        )
        
        parser.add_argument(
            '--emisor-rif',
            type=str,
            default='J-12345678-9',
            help='RIF del emisor (agencia) para las facturas migradas',
        )
        
        parser.add_argument(
            '--emisor-razon-social',
            type=str,
            default='Agencia de Viajes TravelHub C.A.',
            help='Razón social del emisor para las facturas migradas',
        )
        
        parser.add_argument(
            '--emisor-direccion',
            type=str,
            default='Av. Principal, Caracas, Venezuela',
            help='Dirección fiscal del emisor para las facturas migradas',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        factura_id = options['factura_id']
        emisor_rif = options['emisor_rif']
        emisor_razon_social = options['emisor_razon_social']
        emisor_direccion = options['emisor_direccion']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY-RUN: No se harán cambios reales')
            )
        
        # Obtener facturas a migrar
        if factura_id:
            try:
                facturas = Factura.objects.filter(pk=factura_id)
                if not facturas.exists():
                    raise CommandError(f'Factura con ID {factura_id} no encontrada')
            except Factura.DoesNotExist:
                raise CommandError(f'Factura con ID {factura_id} no encontrada')
        else:
            # Migrar solo facturas que no sean ya FacturaVenezuela
            facturas = Factura.objects.exclude(
                pk__in=FacturaVenezuela.objects.values_list('pk', flat=True)
            )
        
        total_facturas = facturas.count()
        
        if total_facturas == 0:
            self.stdout.write(
                self.style.SUCCESS('No hay facturas para migrar')
            )
            return
        
        self.stdout.write(
            f'Iniciando migración de {total_facturas} factura(s)...'
        )
        
        migradas = 0
        errores = 0
        
        for factura in facturas:
            try:
                with transaction.atomic():
                    if dry_run:
                        self._simular_migracion(factura, emisor_rif, emisor_razon_social, emisor_direccion)
                    else:
                        self._migrar_factura(factura, emisor_rif, emisor_razon_social, emisor_direccion)
                    
                    migradas += 1
                    
                    if migradas % 10 == 0:
                        self.stdout.write(f'Migradas {migradas}/{total_facturas} facturas...')
                        
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Error migrando factura {factura.numero_factura}: {e}'
                    )
                )
        
        # Resumen final
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'SIMULACIÓN COMPLETADA: {migradas} facturas se migrarían, {errores} errores'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'MIGRACIÓN COMPLETADA: {migradas} facturas migradas, {errores} errores'
                )
            )
    
    def _simular_migracion(self, factura, emisor_rif, emisor_razon_social, emisor_direccion):
        """Simula la migración de una factura sin hacer cambios reales"""
        self.stdout.write(f'  [SIMULACIÓN] Migrando factura {factura.numero_factura}')
        
        # Validar datos requeridos
        if not factura.cliente:
            self.stdout.write(
                self.style.WARNING(f'    Factura {factura.numero_factura} no tiene cliente asignado')
            )
        
        # Simular clasificación de items
        items_gravados = 0
        items_exentos = 0
        items_exportacion = 0
        
        for item in factura.items_factura.all():
            tipo_servicio = self._determinar_tipo_servicio(item)
            if tipo_servicio == ItemFacturaVenezuela.TipoServicio.TRANSPORTE_AEREO_NACIONAL:
                items_exentos += 1
            elif tipo_servicio == ItemFacturaVenezuela.TipoServicio.SERVICIO_EXPORTACION:
                items_exportacion += 1
            else:
                items_gravados += 1
        
        self.stdout.write(
            f'    Items: {items_gravados} gravados, {items_exentos} exentos, {items_exportacion} exportación'
        )
    
    def _migrar_factura(self, factura, emisor_rif, emisor_razon_social, emisor_direccion):
        """Migra una factura al formato venezolano"""
        
        # Crear FacturaVenezuela basada en la factura original
        factura_venezuela = FacturaVenezuela()
        
        # Copiar campos básicos
        for field in factura._meta.fields:
            if hasattr(factura_venezuela, field.name) and field.name != 'id':
                setattr(factura_venezuela, field.name, getattr(factura, field.name))
        
        # Establecer campos específicos de Venezuela
        factura_venezuela.emisor_rif = emisor_rif
        factura_venezuela.emisor_razon_social = emisor_razon_social
        factura_venezuela.emisor_direccion_fiscal = emisor_direccion
        
        # Determinar tipo de operación (por defecto venta propia)
        factura_venezuela.tipo_operacion = FacturaVenezuela.TipoOperacion.VENTA_PROPIA
        
        # Determinar moneda de operación
        if factura.moneda and factura.moneda.codigo_iso in ['USD', 'EUR']:
            factura_venezuela.moneda_operacion = FacturaVenezuela.MonedaOperacion.DIVISA
        else:
            factura_venezuela.moneda_operacion = FacturaVenezuela.MonedaOperacion.BOLIVAR
        
        # Datos del cliente
        if factura.cliente:
            factura_venezuela.cliente_identificacion = (
                factura.cliente.numero_documento or 
                factura.cliente.cedula_identidad or 
                'N/A'
            )
            factura_venezuela.cliente_direccion = getattr(factura.cliente, 'direccion', '')
            # Por defecto, asumir que es residente (puede ajustarse manualmente después)
            factura_venezuela.cliente_es_residente = True
        
        # Modalidad de emisión (por defecto digital)
        factura_venezuela.modalidad_emision = FacturaVenezuela.ModalidadEmision.DIGITAL
        
        # Guardar la factura venezuela (sin calcular impuestos aún)
        factura_venezuela.pk = factura.pk  # Mantener el mismo ID
        factura_venezuela.save()
        
        # Migrar items
        for item in factura.items_factura.all():
            item_venezuela = ItemFacturaVenezuela()
            
            # Copiar campos básicos
            for field in item._meta.fields:
                if hasattr(item_venezuela, field.name) and field.name not in ['id', 'factura']:
                    setattr(item_venezuela, field.name, getattr(item, field.name))
            
            # Establecer factura venezuela
            item_venezuela.factura = factura_venezuela
            
            # Determinar tipo de servicio
            item_venezuela.tipo_servicio = self._determinar_tipo_servicio(item)
            
            # Configurar gravabilidad
            if item_venezuela.tipo_servicio == ItemFacturaVenezuela.TipoServicio.TRANSPORTE_AEREO_NACIONAL:
                item_venezuela.es_gravado = False
                item_venezuela.alicuota_iva = Decimal('0.00')
            else:
                item_venezuela.es_gravado = True
                item_venezuela.alicuota_iva = Decimal('16.00')
            
            # Extraer datos de boleto si es posible
            if 'boleto' in item.descripcion.lower():
                item_venezuela.nombre_pasajero = self._extraer_nombre_pasajero(item.descripcion)
                item_venezuela.numero_boleto = self._extraer_numero_boleto(item.descripcion)
                item_venezuela.itinerario = self._extraer_itinerario(item.descripcion)
            
            item_venezuela.pk = item.pk  # Mantener el mismo ID
            item_venezuela.save()
        
        # Calcular impuestos venezolanos
        factura_venezuela.calcular_impuestos_venezuela()
        factura_venezuela.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'  Migrada factura {factura.numero_factura}')
        )
    
    def _determinar_tipo_servicio(self, item):
        """Determina el tipo de servicio fiscal basado en la descripción del item"""
        descripcion = item.descripcion.lower()
        
        if any(palabra in descripcion for palabra in ['boleto', 'aereo', 'vuelo', 'ticket']):
            # Asumir que es transporte aéreo nacional (puede ajustarse manualmente)
            return ItemFacturaVenezuela.TipoServicio.TRANSPORTE_AEREO_NACIONAL
        elif any(palabra in descripcion for palabra in ['comision', 'intermediacion']):
            return ItemFacturaVenezuela.TipoServicio.COMISION_INTERMEDIACION
        elif any(palabra in descripcion for palabra in ['exportacion', 'turismo receptivo']):
            return ItemFacturaVenezuela.TipoServicio.SERVICIO_EXPORTACION
        else:
            # Por defecto, servicio gravado
            return ItemFacturaVenezuela.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS
    
    def _extraer_nombre_pasajero(self, descripcion):
        """Intenta extraer el nombre del pasajero de la descripción"""
        # Lógica simple - puede mejorarse
        if 'para' in descripcion.lower():
            partes = descripcion.lower().split('para')
            if len(partes) > 1:
                return partes[1].strip()[:200]  # Limitar a 200 caracteres
        return ''
    
    def _extraer_numero_boleto(self, descripcion):
        """Intenta extraer el número de boleto de la descripción"""
        import re
        # Buscar patrones como "Tkt: 123456" o "Boleto: 123456"
        match = re.search(r'(?:tkt|boleto|ticket):\s*(\w+)', descripcion, re.IGNORECASE)
        if match:
            return match.group(1)[:50]  # Limitar a 50 caracteres
        return ''
    
    def _extraer_itinerario(self, descripcion):
        """Intenta extraer el itinerario de la descripción"""
        # Buscar patrones como "CCS-MIA-CCS" o "Ruta: CCS-MIA"
        import re
        match = re.search(r'(?:ruta|itinerario):\s*([A-Z]{3}(?:-[A-Z]{3})*)', descripcion, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Buscar patrones directos como "CCS-MIA-CCS"
        match = re.search(r'([A-Z]{3}(?:-[A-Z]{3})+)', descripcion)
        if match:
            return match.group(1)
        
        return ''