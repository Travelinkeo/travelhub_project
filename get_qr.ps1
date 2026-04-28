
$baseUrl = "http://localhost:8085"
$apiKey = "TravelHubSecretKey2026"
$headers = @{
    "apikey" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "=== Estado actual de TH_1 ===" -ForegroundColor Cyan
$state = Invoke-RestMethod -Uri "$baseUrl/instance/connectionState/TH_1" -Method GET -Headers $headers -ErrorAction SilentlyContinue
$state | ConvertTo-Json -Depth 3

Write-Host "`n=== Conectar TH_1 (pedir QR) ===" -ForegroundColor Cyan
try {
    $qr = Invoke-RestMethod -Uri "$baseUrl/instance/connect/TH_1" -Method GET -Headers $headers
    Write-Host "Respuesta connect:" -ForegroundColor Green
    $qr | ConvertTo-Json -Depth 5
    
    # Verificar si hay base64 del QR
    if ($qr.base64) {
        Write-Host "`n¡QR BASE64 ENCONTRADO! Longitud: $($qr.base64.Length)" -ForegroundColor Green
        # Guardar el QR como imagen
        $b64 = $qr.base64 -replace "^data:image/png;base64,", ""
        [System.IO.File]::WriteAllBytes("C:\Users\ARMANDO\travelhub_project\qr_test.png", [Convert]::FromBase64String($b64))
        Write-Host "QR guardado en qr_test.png" -ForegroundColor Green
    } else {
        Write-Host "No hay QR base64 en la respuesta. Count: $($qr.count)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host "`n=== Logs recientes de Evolution API (filtrando spam) ===" -ForegroundColor Cyan
docker logs travelhub_project-evolution_api-1 --tail 200 2>&1 | 
    Where-Object { $_ -notmatch "Browser:|Baileys version|Group Ignore" } |
    Select-Object -Last 30
