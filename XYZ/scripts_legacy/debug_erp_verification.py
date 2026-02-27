
import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models import BoletoImportado, Venta

def verify_latest_ticket():
    b = BoletoImportado.objects.last()
    if not b:
        print("No boletos found.")
        return

    print(f"--- BOLETO PK: {b.pk} ---")
    print(f"File: {b.archivo_boleto.name}")
    print(f"Impuestos (Text): {b.impuestos_descripcion}")
    print(f"IVA Monto: {b.iva_monto} (Expected > 0 if breakdown worked)")
    print(f"Inatur Monto: {b.inatur_monto}")
    print(f"Otros Impuestos: {b.otros_impuestos_monto}")
    print(f"Proveedor Link: {b.proveedor_emisor}")
    print(f"Log: {b.log_parseo}")

    if b.datos_parseados:
        print("\n--- JSON OUTPUT ---")
        # Print only relevant keys
        d = b.datos_parseados
        subset = {
            'impuestos_desglose': d.get('impuestos_desglose'),
            'total': d.get('total'),
            'moneda': d.get('moneda') or d.get('TOTAL_MONEDA'),
            'agencia_iata': d.get('agencia_iata'),
            'gds_detected': d.get('gds_detected')
        }
        print(json.dumps(subset, indent=2))
    
    if b.venta_asociada:
        v = b.venta_asociada
        print(f"\n--- VENTA ASOCIADA PK: {v.pk} ---")
        print(f"Total: {v.total_venta}")
        print(f"Moneda: {v.moneda.codigo_iso if v.moneda else 'None'}")

if __name__ == "__main__":
    verify_latest_ticket()
