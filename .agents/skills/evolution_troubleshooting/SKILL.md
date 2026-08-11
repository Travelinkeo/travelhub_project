---
name: evolution-troubleshooting
description: Troubleshooting and recovery guide for Evolution API v2.2.3 and WhatsApp integration in TravelHub, including Baileys Web client version synchronization, ffmpeg installer patches, and Docker container recovery.
---

# Evolution API / WhatsApp QR Troubleshooting & Maintenance Skill

Use this skill whenever the user reports issues with the WhatsApp QR code not loading (e.g., stuck on placeholder, 404 Not Found, WebSocket connection errors, or connection failure loops in Baileys).

---

## 1. Quick Diagnostics & Health Checks

### A. Query Django WhatsApp Health Endpoint
Run from host terminal or container:
```bash
curl -s http://localhost:8000/system/whatsapp/health/<slug>/
```
- **ok**: QR is cached in Redis or ready to fetch from Evolution.
- **degraded**: Evolution container is running, but QR cache is empty (will auto-refresh in ~60s via Celery Beat).
- **down**: Evolution API container is stopped or DB credentials failed.
- **not_configured**: Instance missing in Evolution API. Create it using `EvolutionService.create_instance()`.

### B. Inspect Evolution API Logs
Check live Baileys socket handshake and connection state:
```bash
docker logs travelhub_evolution --tail 30
```
Look for:
- `msg: "connected to WA"` -> Baileys socket initialized.
- `msg: "connection errored"` -> Old/unsupported Baileys WhatsApp client version.

---

## 2. Mandatory Repairs & Common Issues

### Issue 1: WhatsApp Invalidation (`Connection Failure` / `connection errored`)
WhatsApp periodically invalidates outdated Web client versions. When invalidated, Baileys logs `Error: Connection Failure` continuously.

**Solution:**
1. Discover the latest WhatsApp Web client version using Node inside the container:
   ```bash
   docker exec travelhub_evolution node -e "const { fetchLatestBaileysVersion } = require('baileys'); fetchLatestBaileysVersion().then(v => console.log('LATEST:', v.version.join('.')));"
   ```
2. Update `CONFIG_SESSION_PHONE_VERSION` in both `docker-compose.yml` and `/evolution/.env` inside the container:
   - File 1: [docker-compose.yml](file:///C:/Users/ARMANDO/travelhub_project/docker-compose.yml) (`CONFIG_SESSION_PHONE_VERSION=2.3000.1043857760`)
   - File 2: Update `/evolution/.env` inside `travelhub_evolution` container using node/sed.
3. Restart the container:
   ```bash
   docker restart travelhub_evolution
   ```

### Issue 2: `@ffmpeg-installer` Missing Architecture Error
When `travelhub_evolution` starts up, `@ffmpeg-installer/ffmpeg` may throw an error if the platform architecture tag does not match Alpine/Linux.

**Solution:**
Inject dummy native ffmpeg patch:
```bash
docker exec travelhub_evolution sh -c "cat << 'EOF' > /evolution/node_modules/@ffmpeg-installer/ffmpeg/index.js
'use strict';
module.exports = { path: '/usr/bin/ffmpeg', version: '4.x' };
EOF"
docker restart travelhub_evolution
```

### Issue 3: Database Authentication Error (`P1000: Authentication failed against database server`)
If `/evolution/.env` inside the container resets its `DATABASE_CONNECTION_URI` to default placeholder credentials (`user:pass`), Prisma migrations will fail.

**Solution:**
Verify credentials in `travelhub_evolution_db` environment:
```bash
docker exec travelhub_evolution_db env
```
If needed, reset the Postgres role password:
```bash
docker exec travelhub_evolution_db psql -U evolution -d evolution_v2 -c "ALTER USER evolution WITH PASSWORD 'a1_N8Vvfo-yE0LYJpO6QwNcLCPEsQ8C9N4-uIpC-t3w';"
```
And update `DATABASE_CONNECTION_URI` in `/evolution/.env` to match.

---

## 3. Force Cache Refresh & Verification

Once Evolution logs show `connected to WA` without errors:
1. Verify base64 QR generation via HTTP endpoint:
   ```bash
   docker exec travelhub_evolution node -e "const http=require('http'); http.get('http://localhost:8080/instance/connect/travelinkeo', {headers:{apiKey: process.env.AUTHENTICATION_API_KEY}}, r=>{let d=''; r.on('data',c=>d+=c); r.on('end',()=>{const j=JSON.parse(d); console.log('base64 len:', j.base64?j.base64.length:'NONE');});});"
   ```
2. Trigger Django QR cache task:
   ```bash
   docker exec travelhub_web python manage.py shell -c "from apps.common.tasks import fetch_evolution_qr_task; print('Cached length:', len(fetch_evolution_qr_task('travelinkeo')))"
   ```
3. Confirm Redis key presence:
   ```bash
   docker exec travelhub_web python manage.py shell -c "from django.core.cache import cache; print('In Cache:', bool(cache.get('evo_qr:travelinkeo')))"
   ```

---

## 4. Architectural Rules & Best Practices
- **Do not recreate container without volume persistence**: `evolution_data` and `evolution_db_data` keep instance tokens.
- **WebSocket Fallback in Django**: Always catch `WebSocketBadStatusException` in `apps/common/tasks/evolution.py` so HTTP fallback generates the QR seamlessly.
