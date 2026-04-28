import logging
from decimal import Decimal
from django.db.models import Q
from apps.bookings.models import Venta, ItemVenta

logger = logging.getLogger(__name__)

class RevenueAuditorService:
    """
    🧠 REVENUE LEAK AI (SaaS Auditor)
    Servicio encargado de detectar anomalías financieras en las ventas del sistema.
    
    Busca 3 tipos de fugas:
    1. Fuga de Margen: Ventas con rentabilidad negativa o <= 0.
    2. Fuga de Datos: Discrepancias entre lo que reportó el GDS (metadata) y lo que se guardó en el ERP.
    3. Fuga de Costos: Items sin costo neto registrado (lo que impide calcular la liquidación al proveedor).
    """

    def audit_venta(self, venta: Venta, persist=True):
        """Audita una venta específica y retorna un reporte de hallazgos."""
        from apps.bookings.models import VentaAuditFinding
        findings = []
        
        # 1. Verificar Margen
        if venta.total_venta <= 0:
            findings.append({
                'type': VentaAuditFinding.FindingType.CRITICAL_ZERO_SALE,
                'message': f"Venta {venta.localizador} tiene un total de 0. Posible error de parseo o carga manual.",
                'severity': 'HIGH'
            })
        
        # 2. Verificar Discrepancias GDS vs ERP
        md = venta._latest_metadata()
        if md:
            if not md.amount_consistency:
                findings.append({
                    'type': VentaAuditFinding.FindingType.GDS_ERP_DISCREPANCY,
                    'message': f"Discrepancia detectada: GDS reportó {md.total_amount_gds} pero el ERP tiene {venta.total_venta}. Diferencia: {md.amount_difference}",
                    'severity': 'MEDIUM'
                })

        # 3. Verificar Items sin costo
        items_sin_costo = venta.items_venta.filter(Q(costo_neto_proveedor__isnull=True) | Q(costo_neto_proveedor=0))
        if items_sin_costo.exists():
            findings.append({
                'type': VentaAuditFinding.FindingType.MISSING_COSTS,
                'message': f"{items_sin_costo.count()} items no tienen costo neto registrado. Esto afectará la liquidación a proveedores.",
                'severity': 'HIGH'
            })

        if persist and findings:
            for f in findings:
                # Evitar duplicados (mensaje + venta)
                VentaAuditFinding.objects.get_or_create(
                    venta=venta,
                    tipo=f['type'],
                    mensaje=f['message'],
                    defaults={'agencia': venta.agencia}
                )

        return findings

    def run_full_audit(self, days=30):
        """Ejecuta una auditoría sobre las ventas de los últimos X días."""
        from django.utils import timezone
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        # Auditoría profunda: solo ventas activas para evitar ruido
        ventas = Venta.all_objects.filter(fecha_venta__gte=start_date, is_deleted=False)
        report = {
            'total_ventas_auditadas': ventas.count(),
            'ventas_con_fugas': 0,
            'hallazgos_criticos': 0,
            'detalles': []
        }

        for venta in ventas:
            findings = self.audit_venta(venta, persist=True)
            if findings:
                report['ventas_con_fugas'] += 1
                critical_count = len([f for f in findings if f.get('severity') == 'HIGH'])
                report['hallazgos_criticos'] += critical_count
                report['detalles'].append({
                    'venta_id': venta.pk,
                    'localizador': venta.localizador,
                    'findings': findings
                })

        logger.info(f"AUDITORIA COMPLETADA: {report['total_ventas_auditadas']} auditadas, {report['ventas_con_fugas']} fugas.")
        return report
