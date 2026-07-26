import django

django.setup()
from django.contrib import admin
from django.urls import reverse

print("=== ADMIN REGISTRATIONS ===")
core_models = {}
for m, ma in admin.site._registry.items():
    lbl = f"{m._meta.app_label}.{m._meta.model_name}"
    core_models[lbl] = ma.__class__.__name__

required = [
    "core.featureflag",
    "core.agencia",
    "core.apisecret",
    "core.cronapikey",
    "common.pais",
    "common.ciudad",
    "common.aerolinea",
    "common.moneda",
]
for r in required:
    status = "OK" if r in core_models else "MISSING"
    print(f"  {r}: {status} -> {core_models.get(r, 'N/A')}")

print()
print("=== URL RESOLUTION ===")
for u in [
    "admin:core_featureflag_changelist",
    "admin:core_agencia_changelist",
    "admin:common_pais_changelist",
    "admin:common_ciudad_changelist",
]:
    try:
        url = reverse(u)
        print(f"  {u}: OK -> {url}")
    except Exception as e:
        print(f"  {u}: ERROR -> {e}")

print()
print("=== KEY IMPORTS ===")
import importlib

for mod_name in ["core.admin_registrations", "core.admin.api_secret_admin", "core.admin_saas"]:
    try:
        importlib.import_module(mod_name)
        print(f"  {mod_name}: OK")
    except Exception as e:
        print(f"  {mod_name}: ERROR -> {e}")
