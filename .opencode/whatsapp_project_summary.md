# WhatsApp QR Code Fix — Project Summary

## Objective
- Fix the WhatsApp QR code display — Baileys inside Evolution API v2.2.3 enters an infinite reconnection loop because WhatsApp servers actively reject the connection with `CB:failure` reason **405**, preventing QR generation

## Important Details
- The `CB:failure` reason is **405** (not a standard Baileys `DisconnectReason` enum value), with server locations `lla`, `vll`, `atn`, `cco`, `frc` — confirms server-side protocol rejection, not transient
- Baileys **connects** WebSocket and completes Noise handshake (`"connected to WA"`), then sends registration node → WhatsApp replies `CB:failure 405` → Baileys closes connection with `"Connection Failure"` at `socket.js:524`
- Evolution `ChannelStartupService` auto-reconnects every ~3s → infinite loop
- Two Baileys copies exist in the container:
  - `/evolution/node_modules/baileys/` — original `6.7.12` (now replaced with **6.17.16** CJS)
  - `/evolution/node_modules/@whiskeysockets/baileys/` — still **6.7.12** CJS (for backward compat)
- WhatsApp protocol version in registration logs: `[2,3000,1015901307]` — differs from both the bundled file (`1019707846` in 6.17.16) and the GitHub latest (`1035194821`); source of `1015901307` unaccounted for
- `LOG_LEVEL=DEBUG` and `LOG_BAILEYS=debug` remain set
- Container restart policy: `unless-stopped` — filesystem persists across restarts

## Work State
### Completed
- Confirmed CB:FAILURE reason code is **405** (via monkey-patch `console.error` at `socket.js:522`)
- Cleaned 25 stale Evolution instance directories
- Upgraded Baileys inside container: `6.7.12 → 6.17.16 (CJS)` — reverting from the broken `7.0.0-rc13` (ESM) that caused `ERR_REQUIRE_ESM`
- **Resolved the `ERR_REQUIRE_ESM` crash** — `node dist/main.js` now loads baileys 6.17.16 CJS successfully and runs without immediate failure
- Deleted stale instance `freshqr1` from Evolution API
- All previous Django-side fixes remain applied (removed `delete_instance` calls, relaxed HX-poll to 30s)

### Active
- App is starting up (currently in DB migration phase of container restart cycle)
- Once running, will test if the WhatsApp connection receives a QR code or still gets `CB:failure 405`

### Blocked
- Baileys infinite reconnection loop persists after all upgrades — WhatsApp is actively rejecting connections at the application layer, not a network/transport issue
- Cannot verify fix efficacy because container was in crash loop (22 restarts total, 21 from ESM error)
- No public documentation mapping WhatsApp Web `CB:failure` reason 405 to a specific cause

## Next Move
1. Wait for container startup to finish, then observe Baileys connection behavior
2. If 405 persists, determine if the version `1015901307` comes from Evolution API's `CONFIG_SESSION_PHONE` ENV or another override — try forcing the latest GitHub version (`1035194821`)
3. Check if the container's outbound IP is flagged as a datacenter range that WhatsApp blocks for new registrations (try a residential IP or proxy)
4. As last resort, replace Evolution API with a standalone Node.js script using `@whiskeysockets/baileys@latest` outside the container (on a different network)

## Relevant Files
- `/evolution/node_modules/baileys/lib/Socket/socket.js:522-525`: CB:failure handler — reason `405` confirmed
- `/evolution/node_modules/baileys/lib/Utils/validate-connection.js`: `buildHash` = `md5(config.version.join('.'))`, `appVersion` from `config.version`
- `/evolution/node_modules/baileys/lib/Defaults/baileys-version.json`: bundled version `[2,3000,1019707846]` (6.17.16 CJS)
- `/evolution/node_modules/@whiskeysockets/baileys/lib/Defaults/baileys-version.json`: bundled version `[2,3000,1015901307]` (6.7.12)
- GitHub raw: `https://raw.githubusercontent.com/WhiskeySockets/Baileys/master/src/Defaults/baileys-version.json` → returns `[2,3000,1035194821]`
- `docker-compose.yml`: evolution service with `LOG_LEVEL=DEBUG`, `LOG_BAILEYS=debug`, `QRCODE_LIMIT=30`
- `apps/communications/services/whatsapp_unified.py`: `start_session()` refactored (removed delete on close)
- `core/views/agencia_views.py`: `WhatsAppStatusView.get()` refactored
- `core/views/evolution_qr_view.py`: `evolution_qr_proxy()` refactored
- `core/templates/dashboard/partials/whatsapp_qr_new.html`: polling interval relaxed to 30s
