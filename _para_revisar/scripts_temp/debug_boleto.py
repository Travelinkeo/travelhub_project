"""
Script de diagnóstico para problemas de parseo, PDF y eliminación.
Ejecutar con: python debug_boleto.py
"""
import os
import sys
import django

# Cargar variables de entorno
from pathlib import Path
env_path = Path(__file__).parent / ".env.local"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

print("=" * 70)
print("🔍 DIAGNÓSTICO COMPLETO DE BOLETOS")
print("=" * 70)

from apps.bookings.models import BoletoImportado

# 1. Obtener el boleto más reciente
manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
boletos = manager.order_by("-fecha_subida")[:5]

if not boletos:
    print("❌ No hay boletos en la base de datos")
    sys.exit(1)

print(f"\n📋 Últimos {min(5, len(boletos))} boletos:")
for b in boletos:
    print(
        f"  ID={b.pk} | Estado={b.estado_parseo} | PDF={'✅' if b.archivo_pdf_generado else '❌'} "
        f"| Nombre={b.nombre_pasajero_completo or 'N/A'} | PNR={b.localizador_pnr or 'N/A'}"
    )

# Usar el más reciente
boleto = boletos[0]
print(f"\n🎯 Analizando boleto más reciente: ID={boleto.pk}")
print(f"   Archivo: {boleto.archivo_boleto.name if boleto.archivo_boleto else 'SIN ARCHIVO'}")
print(f"   Estado parseo: {boleto.estado_parseo}")
print(f"   Log parseo: {str(boleto.log_parseo or '')[:300]}")
print(f"   Datos parseados: {'✅ SÍ' if boleto.datos_parseados else '❌ VACÍOS'}")
if boleto.datos_parseados and isinstance(boleto.datos_parseados, dict):
    keys = list(boleto.datos_parseados.keys())
    print(f"   Keys en datos: {keys[:15]}")
    pax = boleto.datos_parseados.get("NOMBRE_DEL_PASAJERO") or boleto.datos_parseados.get("passenger_name") or boleto.datos_parseados.get("nombre_pasajero")
    print(f"   Nombre en datos: {pax}")

print("\n" + "=" * 70)
print("🧪 TEST 1: Extracción de texto")
print("=" * 70)
try:
    from apps.automation.parsers.extraction import ExtractionService
    raw_file = ExtractionService.get_open_file(boleto)
    texto = ExtractionService.extract_text(raw_file, boleto.archivo_boleto.name)
    if texto:
        print(f"✅ Texto extraído: {len(texto)} caracteres")
        print(f"   Primeras 500 chars:\n{texto[:500]}")
        print(f"   ...")
        print(f"   Últimas 200 chars:\n{texto[-200:]}")
    else:
        print("❌ FALLO: No se pudo extraer texto del archivo")
except Exception as e:
    print(f"❌ ERROR en extracción: {e}")
    import traceback
    traceback.print_exc()
    texto = None

print("\n" + "=" * 70)
print("🧪 TEST 2: Parseo GDS (Regex/KIU/Sabre)")
print("=" * 70)
if texto:
    try:
        from apps.automation.parsers.adapter import parse_ticket_with_new_parsers
        result = parse_ticket_with_new_parsers(texto)
        print(f"Resultado parseo GDS: {result}")
        if result.get("error"):
            print(f"❌ Error del parser: {result['error']}")
        else:
            print(f"✅ Nombre: {result.get('NOMBRE DEL PASAJERO') or result.get('passenger_name')}")
            print(f"✅ PNR: {result.get('CODIGO RESERVA') or result.get('pnr')}")
            flights = result.get("vuelos") or result.get("flights", [])
            print(f"✅ Vuelos: {len(flights)}")
    except Exception as e:
        print(f"❌ ERROR en parseo GDS: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⏭️ Saltado (sin texto)")

print("\n" + "=" * 70)
print("🧪 TEST 3: Generación de PDF")
print("=" * 70)
if boleto.datos_parseados:
    try:
        from apps.automation.parsers.normalization import DataNormalizationService
        from apps.automation.parsers.pdf_generation import PdfGenerationService
        datos_norm = DataNormalizationService.normalize_ticket_data(boleto.datos_parseados)
        print(f"   NOMBRE_DEL_PASAJERO en normalizados: {datos_norm.get('NOMBRE_DEL_PASAJERO')}")
        print(f"   CODIGO_RESERVA en normalizados: {datos_norm.get('CODIGO_RESERVA')}")
        pdf_bytes, fname = PdfGenerationService.generate_ticket(
            datos_norm, agencia_obj=boleto.agencia, boleto_obj=boleto
        )
        print(f"   PDF resultado: {len(pdf_bytes) if pdf_bytes else 0} bytes, nombre: {fname}")
        if pdf_bytes and len(pdf_bytes) > 100:
            print("✅ PDF generado correctamente")
        else:
            print("❌ PDF vacío o muy pequeño - FALLO en WeasyPrint o plantilla")
    except Exception as e:
        print(f"❌ ERROR en generación PDF: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⏭️ Saltado (sin datos_parseados)")

print("\n" + "=" * 70)
print("🧪 TEST 4: Eliminación lógica (dry-run)")
print("=" * 70)
try:
    # Solo probar el método delete sin ejecutarlo realmente
    has_hard_delete = hasattr(boleto, "hard_delete")
    has_all_objects = hasattr(BoletoImportado, "all_objects")
    print(f"   ¿Tiene hard_delete()? {'✅' if has_hard_delete else '❌'}")
    print(f"   ¿Tiene all_objects manager? {'✅' if has_all_objects else '❌'}")
    
    # Verificar SoftDeleteModel
    from core.api import SoftDeleteModel
    is_soft_delete = isinstance(boleto, SoftDeleteModel)
    print(f"   ¿Es SoftDeleteModel? {'✅' if is_soft_delete else '❌'}")
    
    # Verificar si el boleto tiene referencias protegidas
    from django.db.models import ProtectedError
    from apps.bookings.models import Venta
    if boleto.venta_asociada:
        print(f"   ⚠️ Boleto tiene venta_asociada: Venta #{boleto.venta_asociada_id}")
        print(f"   Para eliminar, primero desasocia la venta")
    else:
        print(f"   ✅ Boleto sin venta asociada, puede eliminarse")
except Exception as e:
    print(f"❌ ERROR en test eliminación: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("🧪 TEST 5: Error de Celery (settings.CELERY_BEAT_SCHEDULE)")
print("=" * 70)
try:
    from django.conf import settings
    has_beat = hasattr(settings, "CELERY_BEAT_SCHEDULE")
    print(f"   ¿CELERY_BEAT_SCHEDULE en settings? {'✅' if has_beat else '❌ FALTANTE'}")
    if not has_beat:
        print("   ⚠️ Esto causa que celery.py falle al importar settings")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ Diagnóstico completado")
print("=" * 70)
