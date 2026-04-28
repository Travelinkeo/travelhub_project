# core/management/commands/consolidar_facturas.py
"""
Comando para migrar datos de Factura antigua a FacturaVenezuela consolidada
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models.facturacion import Factura, ItemFactura
from core.models.facturacion_consolidada import FacturaConsolidada, ItemFacturaConsolidada


class Command(BaseCommand):
    help = 'Migra facturas del modelo antiguo al consolidado FacturaVenezuela'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la migración sin guardar cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== MODO DRY-RUN (no se guardarán cambios) ===\n'))
        
        facturas_antiguas = Factura.objects.all()
        total = facturas_antiguas.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay facturas para migrar.'))
            return
        
        self.stdout.write(f'Encontradas {total} facturas para migrar...\n')
        
        migradas = 0
        errores = 0
        
        for factura in facturas_antiguas:
            try:
                with transaction.atomic():
                    # Verificar si ya existe
                    if FacturaConsolidada.objects.filter(numero_factura=factura.numero_factura).exists():
                        self.stdout.write(self.style.WARNING(
                            f'AVISO: Factura {factura.numero_factura} ya existe en FacturaConsolidada, omitiendo...'
                        ))
                        continue
                    
                    # Obtener agencia del usuario (asumiendo que existe)
                    agencia = None
                    if hasattr(factura, 'venta_asociada') and factura.venta_asociada:
                        if hasattr(factura.venta_asociada, 'agencia'):
                            agencia = factura.venta_asociada.agencia
                    
                    # Valores por defecto para campos nuevos
                    emisor_rif = agencia.rif if agencia and hasattr(agencia, 'rif') else 'J-00000000-0'
                    emisor_razon_social = agencia.nombre if agencia else 'Agencia de Viajes'
                    emisor_direccion = agencia.direccion if agencia and hasattr(agencia, 'direccion') else 'Dirección fiscal'
                    
                    # Determinar tipo de operación (por defecto VENTA_PROPIA)
                    tipo_operacion = 'VENTA_PROPIA'
                    
                    # Determinar moneda de operación
                    moneda_operacion = 'DIVISA' if factura.moneda.codigo_iso == 'USD' else 'BOLIVAR'
                    
                    # Cliente identificación
                    cliente_identificacion = ''
                    if factura.cliente:
                        if hasattr(factura.cliente, 'cedula') and factura.cliente.cedula:
                            cliente_identificacion = factura.cliente.cedula
                        elif hasattr(factura.cliente, 'rif') and factura.cliente.rif:
                            cliente_identificacion = factura.cliente.rif
                        elif hasattr(factura.cliente, 'pasaporte') and factura.cliente.pasaporte:
                            cliente_identificacion = factura.cliente.pasaporte
                    
                    # Crear FacturaConsolidada
                    nueva_factura = FacturaConsolidada(
                        numero_factura=factura.numero_factura,
                        venta_asociada=factura.venta_asociada,
                        cliente=factura.cliente,
                        moneda=factura.moneda,
                        fecha_emision=factura.fecha_emision,
                        fecha_vencimiento=factura.fecha_vencimiento,
                        
                        # Emisor
                        emisor_rif=emisor_rif,
                        emisor_razon_social=emisor_razon_social,
                        emisor_direccion_fiscal=emisor_direccion,
                        
                        # Cliente
                        cliente_identificacion=cliente_identificacion,
                        cliente_es_residente=True,
                        
                        # Tipo de operación
                        tipo_operacion=tipo_operacion,
                        moneda_operacion=moneda_operacion,
                        
                        # Bases imponibles (asumiendo todo gravado)
                        subtotal_base_gravada=factura.subtotal or Decimal('0.00'),
                        subtotal_exento=Decimal('0.00'),
                        subtotal_exportacion=Decimal('0.00'),
                        
                        # Impuestos
                        monto_iva_16=factura.monto_impuestos or Decimal('0.00'),
                        monto_iva_adicional=Decimal('0.00'),
                        monto_igtf=Decimal('0.00'),
                        
                        # Totales
                        saldo_pendiente=factura.saldo_pendiente or Decimal('0.00'),
                        
                        # Estado
                        estado=factura.estado,
                        notas=factura.notas or '',
                        
                        # Archivos
                        archivo_pdf=factura.archivo_pdf,
                        asiento_contable_factura=factura.asiento_contable_factura,
                    )
                    
                    if not dry_run:
                        nueva_factura.save()
                        
                        # Migrar items
                        items_migrados = 0
                        for item in factura.items_factura.all():
                            ItemFacturaConsolidada.objects.create(
                                factura=nueva_factura,
                                descripcion=item.descripcion,
                                cantidad=item.cantidad,
                                precio_unitario=item.precio_unitario,
                                tipo_servicio='ALOJAMIENTO_Y_OTROS_GRAVADOS',
                                es_gravado=True,
                                alicuota_iva=Decimal('16.00'),
                            )
                            items_migrados += 1
                        
                        self.stdout.write(self.style.SUCCESS(
                            f'OK Migrada: {factura.numero_factura} ({items_migrados} items)'
                        ))
                    else:
                        self.stdout.write(self.style.SUCCESS(
                            f'OK [DRY-RUN] Migraria: {factura.numero_factura}'
                        ))
                    
                    migradas += 1
                    
            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(
                    f'ERROR migrando {factura.numero_factura}: {str(e)}'
                ))
        
        # Resumen
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'OK Facturas migradas: {migradas}'))
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'ERRORES: {errores}'))
        self.stdout.write('='*60)
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nAVISO: Esto fue una simulacion. Ejecuta sin --dry-run para aplicar cambios.'
            ))
