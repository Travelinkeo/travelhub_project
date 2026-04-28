import os
import django
import sys

# Setup Django
sys.path.append('C:\\Users\\ARMANDO\\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.services.revenue_auditor import RevenueAuditorService
from apps.bookings.models import Venta

def test():
    auditor = RevenueAuditorService()
    # Usar .all_objects para bypass del TenantManager en debug
    venta = Venta.all_objects.filter(localizador='WPYVSD').first()
    if venta:
        print(f"Auditing Venta: {venta.localizador}")
        findings = auditor.audit_venta(venta)
        for f in findings:
            print(f" - [{f['type']}] {f['message']}")
    else:
        print("Venta WPYVSD not found. Auditing latest 5 sales:")
        for v in Venta.all_objects.all()[:5]:
            print(f"PNR: {v.localizador} | Total: {v.total_venta}")
            findings = auditor.audit_venta(v)
            for f in findings:
                print(f"   ! [{f['type']}] {f['message']}")

if __name__ == "__main__":
    test()
