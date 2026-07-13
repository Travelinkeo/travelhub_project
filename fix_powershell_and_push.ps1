# ==========================================================
# TRAVELHUB - Fix PowerShell + Git Push All Changes
# ==========================================================
# Ejecutar COMO ADMINISTRADOR. Si falla PowerShell,
# abrir cmd.exe como Admin y correr:
#   powershell -ExecutionPolicy Bypass .\fix_powershell_and_push.ps1
# ==========================================================

Write-Host "===== PASO 1: Reparar .NET Framework (ServicePointManager) =====" -ForegroundColor Cyan

# Intentar 1: DISM
try {
    Write-Host "[1/4] Intentando DISM enable NetFx4-AdvSrvs..." -ForegroundColor Yellow
    dism /online /enable-feature /featurename:NetFx4-AdvSrvs /all /quiet /norestart
    Write-Host "  OK: DISM ejecutado" -ForegroundColor Green
} catch {
    Write-Host "  DISM fallo (esperado si ya instalado): $_" -ForegroundColor DarkYellow
}

# Intentar 2: sfc
try {
    Write-Host "[2/4] Intentando sfc /scannow..." -ForegroundColor Yellow
    sfc /scannow
    Write-Host "  OK: SFC ejecutado" -ForegroundColor Green
} catch {
    Write-Host "  SFC fallo: $_" -ForegroundColor DarkYellow
}

# Intentar 3: Forzar registro de .NET
try {
    Write-Host "[3/4] Ejecutando ngen..." -ForegroundColor Yellow
    & "$env:windir\Microsoft.NET\Framework64\v4.0.30319\ngen.exe" executeQueuedItems
} catch {
    Write-Host "  ngen skip: $_" -ForegroundColor DarkYellow
}

Write-Host "[4/4] Probando PowerShell nuevamente..." -ForegroundColor Yellow
try {
    $test = [System.Net.ServicePointManager]::SecurityProtocol
    Write-Host "  OK: ServicePointManager funcional!" -ForegroundColor Green
} catch {
    Write-Host "  AUN ROTO. Reinicia Windows y vuelve a ejecutar este script." -ForegroundColor Red
    Write-Host "  Si persiste, ejecuta en CMD como Admin:" -ForegroundColor Yellow
    Write-Host '    reg add "HKLM\SOFTWARE\Microsoft\.NETFramework\v4.0.30319" /v SchUseStrongCrypto /t REG_DWORD /d 1 /f' -ForegroundColor Gray
    Write-Host '    reg add "HKLM\SOFTWARE\Wow6432Node\Microsoft\.NETFramework\v4.0.30319" /v SchUseStrongCrypto /t REG_DWORD /d 1 /f' -ForegroundColor Gray
    exit 1
}

# ==========================================================
Write-Host "`n===== PASO 2: Git Add + Commit + Push =====" -ForegroundColor Cyan
Set-Location "C:\Users\ARMANDO\travelhub_project"

git add -A
if ($LASTEXITCODE -ne 0) { Write-Host "git add FALLO" -ForegroundColor Red; exit 1 }

$commitMsg = @"
feat: reestructura documentacion y mejora integracion WhatsApp/Telegram

Documentacion:
- Archivos obsoletos movidos a docs/_archive/
- Nuevos documentos: despliegue.md, seguridad.md, desarrollo.md
- INDEX.md reestructurado

WhatsApp (Evolution API):
- Nuevos tipos de mensaje: botones, listas, reacciones, ubicacion, contacto, sticker
- Webhook Evolution para mensajes entrantes y actualizacion de estado
- Seguimiento delivery/read en MensajeWhatsApp
- Mensajes programados (modelo + tarea Celery cada 60s)
- Settings faltantes: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, TWILIO_WHATSAPP_NUMBER

Telegram:
- Settings faltantes: CHANNEL_ID, STORAGE_CHANNEL_ID, FINANZAS_CHAT_ID
- Notificaciones al cliente (confirmacion venta, recordatorio pago, alerta vuelo, alerta migratoria)
- 3 comandos self-service: /misreservas, /mivuelo, /mivoucher
- Modo webhook para el bot (--webhook URL)
- Campo telegram_chat_id en modelo Cliente
- Tareas Celery para notificaciones a clientes
"@

git commit -m $commitMsg
if ($LASTEXITCODE -ne 0) { Write-Host "git commit FALLO" -ForegroundColor Red; exit 1 }

Write-Host "`n===== PASO 3: Push a hardening/operational-risks =====" -ForegroundColor Cyan
git push origin hardening/operational-risks
if ($LASTEXITCODE -ne 0) { Write-Host "git push FALLO" -ForegroundColor Red; exit 1 }

# ==========================================================
Write-Host "`n===== PASO 4: Deploy al contenedor =====" -ForegroundColor Cyan

$files = @(
    @("travelhub\settings\base.py", "/app/travelhub/settings/base.py"),
    @("apps\crm\models.py", "/app/apps/crm/models.py"),
    @("apps\crm\admin.py", "/app/apps/crm/admin.py"),
    @("apps\crm\migrations\0031_whatsapp_enhancements.py", "/app/apps/crm/migrations/0031_whatsapp_enhancements.py"),
    @("apps\crm\migrations\0032_cliente_telegram_chat_id.py", "/app/apps/crm/migrations/0032_cliente_telegram_chat_id.py"),
    @("apps\crm\views\webhook_views.py", "/app/apps/crm/views/webhook_views.py"),
    @("apps\crm\urls.py", "/app/apps/crm/urls.py"),
    @("apps\communications\services\evolution_api_service.py", "/app/apps/communications/services/evolution_api_service.py"),
    @("apps\communications\services\telegram_unified.py", "/app/apps/communications/services/telegram_unified.py"),
    @("apps\common\tasks.py", "/app/apps/common/tasks.py"),
    @("core\management\commands\run_telegram_bot.py", "/app/core/management/commands/run_telegram_bot.py"),
    @("travelhub\celery_beat_schedule.py", "/app/travelhub/celery_beat_schedule.py")
)

foreach ($f in $files) {
    $local = "C:\Users\ARMANDO\travelhub_project\$($f[0])"
    $remote = $f[1]
    Write-Host "Copiando $($f[0])... " -NoNewline
    docker cp "$local" "travelhub_web:$remote" 2>$null
    if ($?) { Write-Host "OK" -ForegroundColor Green } else { Write-Host "FAIL" -ForegroundColor Red }
}

Write-Host "`nAplicando migraciones..." -ForegroundColor Yellow
docker exec travelhub_web python manage.py migrate crm 0030 --fake --noinput
docker exec travelhub_web python manage.py migrate crm 0031 --noinput
docker exec travelhub_web python manage.py migrate crm 0032 --noinput

Write-Host "`nReiniciando contenedor..." -ForegroundColor Yellow
docker restart travelhub_web

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  TODO COMPLETADO!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
pause
