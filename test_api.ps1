
$baseUrl = "http://localhost:8085"
$apiKey = "TravelHubSecretKey2026"
$headers = @{
    "apikey" = $apiKey
    "Content-Type" = "application/json"
}

Write-Host "=== 1. Listar todas las instancias ===" -ForegroundColor Cyan
$instances = Invoke-RestMethod -Uri "$baseUrl/instance/fetchInstances" -Method GET -Headers $headers -ErrorAction SilentlyContinue
$instances | ConvertTo-Json -Depth 5

Write-Host "`n=== 2. Crear instancia TH_2 fresh ===" -ForegroundColor Cyan
$body = @{
    instanceName = "TH_2"
    qrcode = $true
} | ConvertTo-Json
try {
    $result = Invoke-RestMethod -Uri "$baseUrl/instance/create" -Method POST -Headers $headers -Body $body
    $result | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    $_.ErrorDetails.Message
}

Write-Host "`n=== 3. Esperar 3s y obtener QR ===" -ForegroundColor Cyan
Start-Sleep -Seconds 3
try {
    $qr = Invoke-RestMethod -Uri "$baseUrl/instance/connect/TH_2" -Method GET -Headers $headers
    $qr | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Error QR: $_" -ForegroundColor Red
    $_.ErrorDetails.Message
}
