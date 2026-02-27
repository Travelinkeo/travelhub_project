# contabilidad/services.py
"""
Servicios de contabilidad integrada para Venezuela bajo VEN-NIF.
Implementa la lógica de generación automática de asientos contables desde facturación.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import date

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import AsientoContable, DetalleAsiento, PlanContable, TasaCambioBCV
from apps.finance.models import Factura, ItemFactura
from apps.bookings.models import Venta, PagoVenta

logger = logging.getLogger(__name__)


class ContabilidadService:
    """
    Servicio principal para integración Facturación -> Contabilidad.
    Implementa lógica VEN-NIF para agencias de viajes.
    """
    
    @staticmethod
    def obtener_tasa_bcv(fecha: date) -> Decimal:
        """
        Obtiene la tasa de cambio BCV para una fecha específica.
        Si no existe, intenta obtener la más reciente.
        """
        try:
            tasa = TasaCambioBCV.objects.filter(fecha=fecha).first()
            if not tasa:
                # Fallback: tasa más reciente
                tasa = TasaCambioBCV.objects.order_by('-fecha').first()
                if tasa:
                    logger.warning(f"Usando tasa BCV de {tasa.fecha} para fecha {fecha}")
            
            if not tasa:
                raise ValueError(f"No hay tasa BCV disponible para {fecha}")
            
            return tasa.tasa_bsd_por_usd
        except Exception as e:
            logger.error(f"Error obteniendo tasa BCV: {e}")
            raise
    
    @staticmethod
    @transaction.atomic
    def generar_asiento_desde_factura(factura: Factura) -> AsientoContable:
        """
        Genera asiento contable automáticamente desde una factura.
        Implementa lógica Agente vs Principal según tipo_factura.
        
        Args:
            factura: Instancia de Factura
        """
        try:
            # 1. Obtener tasa de cambio
            tasa_dia = factura.tasa_cambio or ContabilidadService.obtener_tasa_bcv(
                factura.fecha_emision.date() if hasattr(factura.fecha_emision, 'date') else factura.fecha_emision
            )
            
            # 2. Crear asiento contable
            asiento = AsientoContable.objects.create(
                fecha_contable=factura.fecha_emision,
                descripcion_general=f"Factura {factura.numero_factura} - {factura.cliente.nombre if factura.cliente else 'Cliente'}",
                tipo_asiento=AsientoContable.TipoAsiento.VENTAS,
                referencia_documento=factura.numero_factura,
                estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
                tasa_cambio_aplicada=tasa_dia,
                moneda=factura.moneda
            )
            
            linea_num = 1
            
            # 3. Generar líneas según tipo de operación
            if factura.tipo_factura == Factura.TipoFactura.TERCEROS:
                # AGENTE: Solo registrar comisión como ingreso
                linea_num = ContabilidadService._generar_lineas_intermediacion(
                    asiento, factura, tasa_dia, linea_num
                )
            else:
                # PRINCIPAL: Registrar ingreso bruto
                linea_num = ContabilidadService._generar_lineas_venta_propia(
                    asiento, factura, tasa_dia, linea_num
                )
            
            # 4. Calcular totales del asiento
            asiento.calcular_totales()
            
            # 5. Vincular asiento a la venta si existe
            if hasattr(factura, 'venta_asociada') and factura.venta_asociada:
                factura.venta_asociada.asiento_contable_venta = asiento
                factura.venta_asociada.save(update_fields=['asiento_contable_venta'])
            
            logger.info(f"Asiento {asiento.numero_asiento} generado para factura {factura.numero_factura}")
            return asiento
            
        except Exception as e:
            logger.error(f"Error generando asiento desde factura {factura.numero_factura}: {e}")
            raise
    
    @staticmethod
    def _generar_lineas_intermediacion(
        asiento: AsientoContable, 
        factura: Factura, 
        tasa: Decimal, 
        linea_num: int
    ) -> int:
        """
        Genera líneas para operación de INTERMEDIACIÓN (Agente).
        Registra: Cuenta por Cobrar (Débito), Ingreso Comisión (Crédito), 
        Cuenta por Pagar Tercero (Crédito), IVA (Crédito).
        """
        # Calcular comisión (ingreso neto de la agencia)
        # En intermediación, el ingreso es solo la comisión
        comision_usd = factura.base_imponible  # Asumimos que la base gravada es la comisión
        
        # Línea 1: DÉBITO - Cuenta por Cobrar
        DetalleAsiento.objects.create(
            asiento=asiento,
            linea=linea_num,
            cuenta_contable=PlanContable.objects.get(codigo_cuenta='1.1.02.02'),  # Cuentas por Cobrar USD
            debe=comision_usd + factura.monto_iva_16 + factura.monto_igtf,
            debe_bsd=(comision_usd + factura.monto_iva_16 + factura.monto_igtf) * tasa,
            haber=Decimal('0.00'),
            haber_bsd=Decimal('0.00'),
            descripcion_linea=f"Cuenta por cobrar factura {factura.numero_factura}"
        )
        linea_num += 1
        
        # Línea 2: CRÉDITO - Ingreso por Comisiones
        DetalleAsiento.objects.create(
            asiento=asiento,
            linea=linea_num,
            cuenta_contable=PlanContable.objects.get(codigo_cuenta='4.1.01'),  # Comisiones Boletos Aéreos
            debe=Decimal('0.00'),
            debe_bsd=Decimal('0.00'),
            haber=comision_usd,
            haber_bsd=comision_usd * tasa,
            descripcion_linea=f"Comisión por intermediación"
        )
        linea_num += 1
        
        # Línea 3: CRÉDITO - Cuenta por Pagar al Tercero (Aerolínea/Proveedor)
        # Nota: En Factura (base) no tenemos tercero_razon_social, usamos descripcion generica o accedemos a boleto
        monto_tercero = factura.monto_total - comision_usd - factura.iva_monto - factura.igtf_monto
        if monto_tercero > 0:
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=linea_num,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='2.1.01.02'),  # Cuentas por Pagar USD
                debe=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber=monto_tercero,
                haber_bsd=monto_tercero * tasa,
                descripcion_linea=f"Cuenta por pagar a proveedor (Terceros)"
            )
            linea_num += 1
        
        # Línea 4: CRÉDITO - IVA Débito Fiscal
        if factura.monto_iva_16 > 0:
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=linea_num,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='2.1.02.01'),  # IVA Débito Fiscal
                debe=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber=factura.monto_iva_16,
                haber_bsd=factura.monto_iva_16 * tasa,
                descripcion_linea="IVA 16% por pagar"
            )
            linea_num += 1
        
        # Línea 5: CRÉDITO - IGTF por Pagar (si aplica)
        if factura.monto_igtf > 0:
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=linea_num,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='2.1.02.03'),  # IGTF por Pagar
                debe=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber=factura.monto_igtf,
                haber_bsd=factura.monto_igtf * tasa,
                descripcion_linea="IGTF 3% por pagar"
            )
            linea_num += 1
        
        return linea_num
    
    @staticmethod
    def _generar_lineas_venta_propia(
        asiento: AsientoContable, 
        factura: Factura, 
        tasa: Decimal, 
        linea_num: int
    ) -> int:
        """
        Genera líneas para operación de VENTA PROPIA (Principal).
        Registra: Cuenta por Cobrar (Débito), Ingreso Bruto (Crédito), IVA (Crédito).
        """
        # Línea 1: DÉBITO - Cuenta por Cobrar
        DetalleAsiento.objects.create(
            asiento=asiento,
            linea=linea_num,
            cuenta_contable=PlanContable.objects.get(codigo_cuenta='1.1.02.02'),  # Cuentas por Cobrar USD
            debe=factura.monto_total,
            debe_bsd=factura.monto_total * tasa,
            haber=Decimal('0.00'),
            haber_bsd=Decimal('0.00'),
            descripcion_linea=f"Cuenta por cobrar factura {factura.numero_factura}"
        )
        linea_num += 1
        
        # Línea 2: CRÉDITO - Ingreso por Venta de Paquetes
        subtotal = factura.base_imponible + factura.base_exenta
        DetalleAsiento.objects.create(
            asiento=asiento,
            linea=linea_num,
            cuenta_contable=PlanContable.objects.get(codigo_cuenta='4.2'),  # Ingresos por Venta de Paquetes
            debe=Decimal('0.00'),
            debe_bsd=Decimal('0.00'),
            haber=subtotal,
            haber_bsd=subtotal * tasa,
            descripcion_linea="Ingreso por venta de paquete turístico"
        )
        linea_num += 1
        
        # Línea 3: CRÉDITO - IVA Débito Fiscal
        if factura.monto_iva_16 > 0:
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=linea_num,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='2.1.02.01'),  # IVA Débito Fiscal
                debe=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber=factura.monto_iva_16,
                haber_bsd=factura.monto_iva_16 * tasa,
                descripcion_linea="IVA 16% por pagar"
            )
            linea_num += 1
        
        # Línea 4: CRÉDITO - IGTF por Pagar (si aplica)
        if factura.monto_igtf > 0:
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=linea_num,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='2.1.02.03'),  # IGTF por Pagar
                debe=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber=factura.monto_igtf,
                haber_bsd=factura.monto_igtf * tasa,
                descripcion_linea="IGTF 3% por pagar"
            )
            linea_num += 1
        
        return linea_num
    
    @staticmethod
    @transaction.atomic
    def registrar_pago_y_diferencial(pago: PagoVenta) -> Optional[AsientoContable]:
        """
        Registra el pago y calcula/contabiliza el diferencial cambiario.
        Implementa lógica de ganancia/pérdida cambiaria según VEN-NIF.
        
        Args:
            pago: Instancia de PagoVenta
            
        Returns:
            AsientoContable del pago (con diferencial si aplica)
        """
        try:
            venta = pago.venta
            
            # Obtener factura asociada
            factura = venta.factura
            if not factura:
                logger.warning(f"Pago {pago.id_pago_venta} sin factura asociada")
                return None
            
            # Obtener tasas de cambio
            tasa_factura = factura.tasa_cambio
            tasa_pago = ContabilidadService.obtener_tasa_bcv(
                pago.fecha_pago.date() if hasattr(pago.fecha_pago, 'date') else pago.fecha_pago
            )
            
            # Crear asiento de pago
            asiento = AsientoContable.objects.create(
                fecha_contable=pago.fecha_pago,
                descripcion_general=f"Pago {pago.referencia or pago.id_pago_venta} - Venta {venta.localizador}",
                tipo_asiento=AsientoContable.TipoAsiento.DIARIO,
                referencia_documento=f"PAGO-{pago.id_pago_venta}",
                estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
                tasa_cambio_aplicada=tasa_pago,
                moneda=pago.moneda
            )
            
            linea_num = 1
            
            # Línea 1: DÉBITO - Banco/Caja
            cuenta_banco = PlanContable.objects.get(codigo_cuenta='1.1.01.04')  # Bancos USD
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=linea_num,
                cuenta_contable=cuenta_banco,
                debe=pago.monto,
                debe_bsd=pago.monto * tasa_pago,
                haber=Decimal('0.00'),
                haber_bsd=Decimal('0.00'),
                descripcion_linea=f"Ingreso por {pago.get_metodo_display()}"
            )
            linea_num += 1
            
            # Línea 2: CRÉDITO - Cuenta por Cobrar (al valor histórico)
            bsd_factura = pago.monto * tasa_factura
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=linea_num,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='1.1.02.02'),
                debe=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber=pago.monto,
                haber_bsd=bsd_factura,
                descripcion_linea="Cancelación cuenta por cobrar"
            )
            linea_num += 1
            
            # Calcular diferencial cambiario
            bsd_pago = pago.monto * tasa_pago
            diferencial_bsd = bsd_pago - bsd_factura
            
            if abs(diferencial_bsd) > Decimal('0.01'):  # Tolerancia
                if diferencial_bsd > 0:
                    # GANANCIA CAMBIARIA
                    DetalleAsiento.objects.create(
                        asiento=asiento,
                        linea=linea_num,
                        cuenta_contable=PlanContable.objects.get(codigo_cuenta='7.1.01'),  # Ingreso Diferencial
                        debe=Decimal('0.00'),
                        debe_bsd=Decimal('0.00'),
                        haber=Decimal('0.00'),  # Solo en BSD
                        haber_bsd=diferencial_bsd,
                        descripcion_linea=f"Ganancia cambiaria (tasa {tasa_factura} -> {tasa_pago})"
                    )
                    linea_num += 1
                    
                    # Generar Nota de Débito por IVA sobre ganancia cambiaria
                    nota_debito = ContabilidadService._generar_nota_debito_diferencial(
                        factura=factura,
                        pago=pago,
                        ganancia_bsd=diferencial_bsd,
                        tasa_factura=tasa_factura,
                        tasa_pago=tasa_pago
                    )
                    
                    if nota_debito:
                        # Registrar IVA de la nota de débito en el asiento
                        DetalleAsiento.objects.create(
                            asiento=asiento,
                            linea=linea_num,
                            cuenta_contable=PlanContable.objects.get(codigo_cuenta='1.1.02.02'),  # Cuentas por Cobrar
                            debe=Decimal('0.00'),
                            debe_bsd=nota_debito.monto_iva_bsd,
                            haber=Decimal('0.00'),
                            haber_bsd=Decimal('0.00'),
                            descripcion_linea=f"IVA s/ganancia cambiaria - ND {nota_debito.numero_nota_debito}"
                        )
                        linea_num += 1
                        
                        DetalleAsiento.objects.create(
                            asiento=asiento,
                            linea=linea_num,
                            cuenta_contable=PlanContable.objects.get(codigo_cuenta='2.1.02.01'),  # IVA Débito Fiscal
                            debe=Decimal('0.00'),
                            debe_bsd=Decimal('0.00'),
                            haber=Decimal('0.00'),
                            haber_bsd=nota_debito.monto_iva_bsd,
                            descripcion_linea=f"IVA por pagar - ND {nota_debito.numero_nota_debito}"
                        )
                        linea_num += 1
                        
                        logger.info(f"Nota de Débito {nota_debito.numero_nota_debito} generada: IVA {nota_debito.monto_iva_bsd} BSD")
                    
                else:
                    # PÉRDIDA CAMBIARIA
                    DetalleAsiento.objects.create(
                        asiento=asiento,
                        linea=linea_num,
                        cuenta_contable=PlanContable.objects.get(codigo_cuenta='7.2.01'),  # Pérdida Diferencial
                        debe=Decimal('0.00'),  # Solo en BSD
                        debe_bsd=abs(diferencial_bsd),
                        haber=Decimal('0.00'),
                        haber_bsd=Decimal('0.00'),
                        descripcion_linea=f"Pérdida cambiaria (tasa {tasa_factura} -> {tasa_pago})"
                    )
                    linea_num += 1
            
            # Calcular totales
            asiento.calcular_totales()
            
            logger.info(f"Asiento de pago {asiento.numero_asiento} generado con diferencial {diferencial_bsd} BSD")
            return asiento
            
        except Exception as e:
            logger.error(f"Error registrando pago {pago.id_pago_venta}: {e}")
            raise
    
    @staticmethod
    @transaction.atomic
    def provisionar_contribucion_inatur(mes: int, anio: int) -> AsientoContable:
        """
        Calcula y provisiona la contribución del 1% a INATUR.
        Debe ejecutarse al final de cada mes.
        
        Args:
            mes: Mes a procesar (1-12)
            anio: Año a procesar
            
        Returns:
            AsientoContable de la provisión
        """
        try:
            from django.db.models import Sum
            from datetime import date
            
            # Calcular primer y último día del mes
            primer_dia = date(anio, mes, 1)
            if mes == 12:
                ultimo_dia = date(anio, 12, 31)
            else:
                ultimo_dia = date(anio, mes + 1, 1) - timezone.timedelta(days=1)
            
            # Sumar ingresos del mes (en BSD)
            ingresos_mes = DetalleAsiento.objects.filter(
                asiento__fecha_contable__range=(primer_dia, ultimo_dia),
                cuenta_contable__tipo_cuenta=PlanContable.TipoCuentaChoices.INGRESO,
                asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
            ).aggregate(total=Sum('haber_bsd'))['total'] or Decimal('0.00')
            
            # Calcular contribución 1%
            contribucion = ingresos_mes * Decimal('0.01')
            
            # Crear asiento de provisión
            asiento = AsientoContable.objects.create(
                fecha_contable=ultimo_dia,
                descripcion_general=f"Provisión INATUR 1% - {mes}/{anio}",
                tipo_asiento=AsientoContable.TipoAsiento.AJUSTE,
                referencia_documento=f"INATUR-{anio}{mes:02d}",
                estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
                tasa_cambio_aplicada=Decimal('1.00'),
                moneda=None  # Solo en BSD
            )
            
            # Línea 1: DÉBITO - Gasto INATUR
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=1,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='6.1.05'),  # Gasto INATUR
                debe=Decimal('0.00'),
                debe_bsd=contribucion,
                haber=Decimal('0.00'),
                haber_bsd=Decimal('0.00'),
                descripcion_linea=f"Gasto contribución INATUR 1% sobre {ingresos_mes} BSD"
            )
            
            # Línea 2: CRÉDITO - Pasivo INATUR por Pagar
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=2,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='2.1.02.02'),  # INATUR por Pagar
                debe=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber=Decimal('0.00'),
                haber_bsd=contribucion,
                descripcion_linea="Provisión INATUR por pagar"
            )
            
            asiento.calcular_totales()
            
            logger.info(f"Provisión INATUR {mes}/{anio}: {contribucion} BSD sobre ingresos {ingresos_mes} BSD")
            return asiento
            
        except Exception as e:
            logger.error(f"Error provisionando INATUR {mes}/{anio}: {e}")
            raise
    
    @staticmethod
    def _generar_nota_debito_diferencial(
        factura,
        pago,
        ganancia_bsd: Decimal,
        tasa_factura: Decimal,
        tasa_pago: Decimal
    ):
        """
        Genera Nota de Débito por IVA sobre ganancia cambiaria.
        Según normativa venezolana, la ganancia incrementa la base imponible.
        
        Args:
        Args:
            factura: Factura origen
            pago: PagoVenta que generó el diferencial
            ganancia_bsd: Monto de la ganancia en BSD
            tasa_factura: Tasa BCV al momento de la factura
            tasa_pago: Tasa BCV al momento del pago
            
        Returns:
            Factura (Nota Debito) creada o None si no aplica
        """
        try:
            # Crear Factura tipo ND
            # Nota: Esto crea una factura real. Si se prefiere solo un registro contable, usar otro modelo.
            # Aquí asumimos que se emite una Nota de Débito fiscal.
            
            # IVA 16% sobre la ganancia
            iva_bsd = ganancia_bsd * Decimal('0.16')
            # Convertir a USD para la ND (aproximado, ya que la ND es en base a ganancia cambiaria que es en Bs)
            # Generalmente estas ND son solo en Bs. Pero el sistema es multimoneda.
            # Usamos tasa pago para la conversion base
            
            monto_iva_usd = iva_bsd / tasa_pago
            
            nota_debito = Factura.objects.create(
                tipo_factura=Factura.TipoFactura.NOTA_DEBITO,
                factura_asociada=factura,
                cliente=factura.cliente,
                moneda=factura.moneda,
                tasa_cambio=tasa_pago,
                notas=f"Nota de Débito por Diferencial Cambiario. Factura {factura.numero_factura}. Ganancia {ganancia_bsd} BSD",
                # Totales (Reflejar IVA)
                iva_monto=monto_iva_usd,
                monto_impuestos=monto_iva_usd,
                monto_total=monto_iva_usd, # ND por el IVA solamente? O base? Leyes venezolanas: Se factura el diferencial??
                # Normalmente se emite ND sobre el valor que aumentó.
                # Simplificación: Crear ND con los montos calculados.
                estado=Factura.EstadoFactura.EMITIDA
            )
            
            # Agregar Item explicando
            ItemFactura.objects.create(
                factura=nota_debito,
                descripcion=f"Ajuste por Diferencial Cambiario",
                cantidad=1,
                precio_unitario=Decimal('0.00'), # La base es el diferencial, pero en este caso es un ajuste
                subtotal_item=Decimal('0.00')
            )
            # Actualizar totales manualmente para reflejar lo deseado
            nota_debito.iva_monto = monto_iva_usd
            nota_debito.monto_total = monto_iva_usd
            nota_debito.save()

            logger.info(
                f"Nota de Débito {nota_debito.numero_factura} generada: "
                f"Ganancia {ganancia_bsd} BSD, IVA {iva_bsd} BSD"
            )
            
            # Retornamos un objeto que tenga atributos esperados por quien llama, o adaptamos el llamador.
            # El llamador espera 'monto_iva_bsd' y 'numero_nota_debito'
            nota_debito.monto_iva_bsd = iva_bsd
            nota_debito.numero_nota_debito = nota_debito.numero_factura
            
            return nota_debito
            
        except Exception as e:
            logger.error(f"Error generando Nota de Débito: {e}")
            return None
