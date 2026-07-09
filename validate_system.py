"""
validate_system.py - Validación integral de todos los sistemas corregidos
Ejecutar con: docker exec travelhub_web python validate_system.py
"""

import inspect
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")

import django

django.setup()

errors = []
warnings = []
ok = []

print("\n" + "=" * 65)
print("  VALIDACIÓN INTEGRAL DEL SISTEMA - TravelHub")
print("=" * 65 + "\n")

# ============================================================
# VALIDACIÓN 1: MAILBOT - Fix de la agencia (AttributeError)
# ============================================================
print("▶ [1/6] Mailbot: Seguridad en obtención de agencia")
try:

    class FakeConsultor:
        pass  # No tiene atributo 'agencias'

    consultor = FakeConsultor()
    relacion_agencia = (
        consultor.agencias.filter(activa=True).first() if hasattr(consultor, "agencias") else None
    )
    agencia = relacion_agencia.agencia if relacion_agencia else None
    ok.append("Mailbot: sin crash con consultor sin agencias (agencia=None)")
    print(f"  ✅ OK: agencia={agencia!r} sin crash")
except AttributeError as e:
    errors.append(f"Mailbot: AttributeError aún presente -> {e}")
    print(f"  ❌ ERROR: AttributeError -> {e}")

# ============================================================
# VALIDACIÓN 2: send_whatsapp_task → enviar_whatsapp
# ============================================================
print("\n▶ [2/6] send_whatsapp_task: Import y firma de enviar_whatsapp")
try:
    from apps.communications.services.whatsapp_unified import enviar_whatsapp

    sig = inspect.signature(enviar_whatsapp)
    params_str = str(sig)
    ok.append("enviar_whatsapp importado correctamente")
    print(f"  ✅ OK: firma: enviar_whatsapp{sig}")
    if "**kwargs" in params_str:
        ok.append("enviar_whatsapp acepta agencia via **kwargs")
        print("  ✅ OK: acepta agencia=... via **kwargs")
    else:
        warnings.append("enviar_whatsapp puede no aceptar agencia via kwargs - revisar")
        print("  ⚠️  ADVERTENCIA: revisar firma de kwargs")
except ImportError as e:
    errors.append(f"enviar_whatsapp no importable: {e}")
    print(f"  ❌ ERROR: ImportError -> {e}")

# ============================================================
# VALIDACIÓN 3: TelegramNotificationService.send_message **kwargs
# ============================================================
print("\n▶ [3/6] Telegram: TelegramNotificationService.send_message")
try:
    from apps.communications.services.telegram_unified import TelegramNotificationService

    sig = inspect.signature(TelegramNotificationService.send_message)
    params = sig.parameters
    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    param_names = list(params.keys())
    print(f"  Firma: send_message{sig}")
    print(f"  Parámetros: {param_names}")

    if has_var_keyword:
        ok.append("TelegramNotificationService.send_message acepta **kwargs (reply_markup OK)")
        print("  ✅ OK: acepta **kwargs — reply_markup pasará correctamente")
    else:
        errors.append(
            "CRÍTICO: TelegramNotificationService.send_message NO acepta **kwargs. "
            "La llamada en bookings/tasks.py con **payload (reply_markup) lanzará TypeError"
        )
        print("  ❌ CRÍTICO: NO acepta **kwargs → TypeError en bookings/tasks.py")
        print("     Solución: agregar **kwargs a la firma del método")
except Exception as e:
    errors.append(f"Error validando TelegramNotificationService: {e}")
    print(f"  ❌ ERROR: {e}")

# ============================================================
# VALIDACIÓN 4: Evolution API - Conectividad real
# ============================================================
print("\n▶ [4/6] Evolution API: Conectividad y estado de instancia")
try:
    from apps.communications.services.evolution_api_service import EvolutionService

    state = EvolutionService.get_instance_state("travelinkeo")
    print(f"  Estado de instancia 'travelinkeo': {state!r}")
    if state == "open":
        ok.append("Evolution API: instancia 'travelinkeo' conectada (open)")
        print("  ✅ OK: Instancia conectada y lista para enviar mensajes")
    elif state:
        warnings.append(f"Evolution API: instancia en estado '{state}' (esperado 'open')")
        print(f"  ⚠️  ADVERTENCIA: estado={state!r}, no es 'open'")
    else:
        errors.append("Evolution API: instancia no conectada (None/vacío)")
        print("  ❌ ERROR: instancia no responde o no conectada")
except Exception as e:
    errors.append(f"Evolution API excepción: {e}")
    print(f"  ❌ ERROR: {e}")

# ============================================================
# VALIDACIÓN 5: Celery - Tareas accesibles
# ============================================================
print("\n▶ [5/6] Celery: Importación de tareas críticas")
tasks_to_check = [
    ("apps.common.tasks", "send_whatsapp_task"),
    ("apps.common.tasks", "send_telegram_task"),
    ("apps.common.tasks", "send_email_task"),
    ("apps.bookings.tasks", "parsear_boleto_individual"),
    ("apps.bookings.tasks", "cls_notificar_infraccion_pasaporte"),
    ("apps.crm.tasks_bot", "whatsapp_ai_task"),
]
for module_path, task_name in tasks_to_check:
    try:
        import importlib

        mod = importlib.import_module(module_path)
        task = getattr(mod, task_name)
        ok.append(f"{task_name} importable")
        print(f"  ✅ {module_path}.{task_name}")
    except (ImportError, AttributeError) as e:
        errors.append(f"{task_name} NO importable: {e}")
        print(f"  ❌ {module_path}.{task_name} → {e}")

# ============================================================
# VALIDACIÓN 6: URL del webhook registrada
# ============================================================
print("\n▶ [6/6] URLs del sistema (webhook mailbot, WhatsApp, API)")
try:
    from django.urls import NoReverseMatch, reverse

    urls_to_check = [
        ("crm:whatsapp_webhook", "WhatsApp webhook"),
        ("core:webhook_resend_inbound", "Resend mailbot webhook"),
    ]
    for url_name, description in urls_to_check:
        try:
            url = reverse(url_name)
            ok.append(f"URL registrada: {description} → {url}")
            print(f"  ✅ {description}: {url}")
        except NoReverseMatch:
            # Intentar sin namespace
            base_name = url_name.split(":")[-1]
            try:
                url = reverse(base_name)
                ok.append(f"URL registrada: {description} → {url}")
                print(f"  ✅ {description}: {url}")
            except NoReverseMatch:
                warnings.append(f"URL no encontrada por nombre: {url_name}")
                print(f"  ⚠️  URL '{url_name}' no tiene reverse - verificar manualmente")
except Exception as e:
    warnings.append(f"Error validando URLs: {e}")
    print(f"  ⚠️  {e}")

# ============================================================
# RESUMEN FINAL
# ============================================================
print("\n" + "=" * 65)
print("  RESUMEN FINAL")
print("=" * 65)
print(f"\n  ✅ OK:          {len(ok)}")
print(f"  ⚠️  Advertencias: {len(warnings)}")
print(f"  ❌ Errores:     {len(errors)}")

if errors:
    print("\n--- ERRORES CRÍTICOS ---")
    for e in errors:
        print(f"  ❌ {e}")
if warnings:
    print("\n--- ADVERTENCIAS ---")
    for w in warnings:
        print(f"  ⚠️  {w}")

if not errors:
    print("\n  🎉 Sistema validado sin errores críticos.")
else:
    print(f"\n  ⚠️  {len(errors)} error(es) requieren corrección.")
print()
