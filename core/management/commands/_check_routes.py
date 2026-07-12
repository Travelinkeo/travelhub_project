import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
os.environ.setdefault("DJANGO_ENV", "production")

import django

django.setup()

from django.urls import reverse  # noqa: E402  # requiere django.setup() previo

tests = [
    ("home", "/"),
    ("public_pricing", "/pricing/"),
    ("pwa_manifest", "/manifest.json"),
    ("service_worker", "/service-worker.js"),
    ("offline", "/offline/"),
    ("status_api", "/status/"),
    ("docs_index", "/docs/"),
    ("health_metrics", "/health/metrics/"),
    ("push_subscribe", "/api/push/subscribe/"),
    ("sso_login", "/sso/login/1/"),
]

for name, expected in tests:
    try:
        kwargs = {"provider_id": 1} if "sso" in name else {}
        rev = reverse(name, kwargs=kwargs)
        ok = "OK" if rev == expected else f"WRONG got={rev}"
        print(f"{ok} {name:20s} -> {rev}")
    except Exception as e:
        print(f"NO {name:20s} -> {type(e).__name__}: {e}")
print("DONE.")
