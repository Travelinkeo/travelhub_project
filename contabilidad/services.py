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
from core.models.facturacion_venezuela import FacturaVenezuela
from core.models.ventas import Venta, PagoVenta

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
    def generar_asiento_desde_factura(factura: FacturaVenezuela) -> AsientoContable:
        """
        Genera asiento contable automáticamente desde una factura.
        Implementa lógica Agente vs Principal según tipo_operacion.
        
        Args:
            factura: Instancia de FacturaVenezuela
            
        Returns:
            AsientoContable creado
        """
        try:
            # 1. Obtener tasa de cambio
            tasa_dia = factura.tasa_cambio_bcv or ContabilidadService.obtener_tasa_bcv(
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
            if factura.tipo_operacion == FacturaVenezuela.TipoOperacion.INTERMEDIACION:
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
        factura: FacturaVenezuela, 
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
        comision_usd = factura.subtotal_base_gravada  # Asumimos que la base gravada es la comisión
        
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
        monto_tercero = factura.monto_total - comision_usd - factura.monto_iva_16 - factura.monto_igtf
        if monto_tercero > 0:
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=linea_num,
                cuenta_contable=PlanContable.objects.get(codigo_cuenta='2.1.01.02'),  # Cuentas por Pagar USD
                debe=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber=monto_tercero,
                haber_bsd=monto_tercero * tasa,
                descripcion_linea=f"Cuenta por pagar a {factura.tercero_razon_social or 'proveedor'}"
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
        factura: FacturaVenezuela, 
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
        subtotal = factura.subtotal_base_gravada + factura.subtotal_exento + factura.subtotal_exportacion
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
            if not factura or not isinstance(factura, FacturaVenezuela):
                logger.warning(f"Pago {pago.id_pago_venta} sin factura Venezuela asociada")
                return None
            
            # Obtener tasas de cambio
            tasa_factura = factura.tasa_cambio_bcv
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
            factura: FacturaVenezuela origen
            pago: PagoVenta que generó el diferencial
            ganancia_bsd: Monto de la ganancia en BSD
            tasa_factura: Tasa BCV al momento de la factura
            tasa_pago: Tasa BCV al momento del pago
            
        Returns:
            NotaDebitoVenezuela creada o None si no aplica
        """
        try:
            from core.models.facturacion_venezuela import NotaDebitoVenezuela
            
            # Calcular IVA 16% sobre la ganancia
            iva_bsd = ganancia_bsd * Decimal('0.16')
            
            # Crear nota de débito
            nota_debito = NotaDebitoVenezuela.objects.create(
                factura_origen=factura,
                ganancia_cambiaria_bsd=ganancia_bsd,
                monto_iva_bsd=iva_bsd,
                tasa_factura=tasa_factura,
                tasa_pago=tasa_pago,
                referencia_pago=pago.referencia or f"PAGO-{pago.id_pago_venta}",
                observaciones=f"IVA sobre ganancia cambiaria. Factura {factura.numero_factura} pagada con tasa {tasa_pago} vs tasa original {tasa_factura}"
            )
            
            logger.info(
                f"Nota de Débito {nota_debito.numero_nota_debito} generada: "
                f"Ganancia {ganancia_bsd} BSD, IVA {iva_bsd} BSD"
            )
            
            return nota_debito
            
        except Exception as e:
            logger.error(f"Error generando Nota de Débito: {e}")
            return None
