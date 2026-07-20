---
name: evolution-troubleshooting
description: Troubleshooting and recovery guide for Evolution API v2.2.3 and WhatsApp integration in TravelHub, including QR code issues and Docker container reloading.
---

# Evolution API / WhatsApp QR Troubleshooting Skill

Use this skill whenever the user reports issues with the WhatsApp QR code not loading (e.g. 404 Not Found, spinning indefinitely) or Evolution API connection problems.

## 1. Quick Diagnostics & Health Checks

Before taking action, check the system health:
- Query the Django health-check endpoint (no auth required):
  `curl -s http://localhost:8000/system/whatsapp/health/<slug>/`
  - **ok**: QR is ready in Redis cache or generable from Evolution.
  - **degraded**: Evolution is up but cache is empty (usually regenerates in ~60s via Celery Beat).
  - **down**: Evolution container is down or credentials are bad.
  - **not_configured**: Instance is missing, call `EvolutionService.create_instance()`.

## 2. Emergency Recovery Steps

If the QR doesn't appear or the integration is failing:

### A. Check WhatsApp Protocol Version
Ensure `CONFIG_SESSION_PHONE_VERSION` in the Evolution container is exactly `2.3000.1035194821`:
```bash
docker exec travelhub_evolution cat /evolution/.env | grep CONFIG_SESSION_PHONE_VERSION
```
If incorrect, update it and restart the container (`docker restart travelhub_evolution`). Wait ~60s for startup.

### B. Force QR Cache Refresh
If the container is running properly but the QR doesn't show in the Django UI, force a refresh:
```bash
docker exec travelhub_web python3 /app/trigger_qr.py
```
If it succeeds, it will print "Evolution QR cached via HTTP". If it says "Not Found", the instance may need to be recreated via Evolution API (`/instance/create`).

### C. Verify Django Services
- **Celery Worker**: Check if `travelhub_worker` is crashing or stuck. Run `docker logs travelhub_worker --tail 30` and ensure tasks are processing. A crashed worker means the QR cache never updates.
- **Celery Beat**: Check if `travelhub_beat` is running. It triggers the `fetch_evolution_qr_task` every 60s.
- **URL Configuration**: Check that the QR proxy points to `core:evolution_qr_image` (the PNG view) and NOT `core:evolution_qr_proxy` (the Manager UI).
  ```bash
  docker exec travelhub_web python3 -c "from django.urls import reverse; print(reverse('core:evolution_qr_image', kwargs={'instance_name':'travelinkeo'}))"
  ```

## 3. Important Endpoint Changes (Evolution v2.2.3 vs v1)
- **CORRECT QR Endpoint**: `/instance/connect/<slug>` (Returns `{qrcode: {base64: "..."}}`).
- **DEPRECATED**: `/instance/qrcode/<slug>/` or `/manager/qr/<slug>/` (Will return 404).

## 4. Deploying Python Fixes (Without full docker build)
If you need to edit `.py` or `.html` files in Django (`travelhub_web`) to fix an issue, use the included deployment script to sync changes without a 3-minute rebuild:
```bash
bash docs/troubleshooting/deploy_local_changes.sh
```
This script:
1. Copies changed files via `docker cp`.
2. Clears `__pycache__`.
3. Sends `SIGHUP` to the Gunicorn master process to gracefully reload workers.
*(Note: If you change `models.py` schemas, `urls_system.py`, or `package.json`, you must perform a full rebuild: `docker compose up -d --build web`)*
