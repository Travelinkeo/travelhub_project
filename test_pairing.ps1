
$headers = @{
    "apikey" = "TravelHubSecretKey2026"
    "Content-Type" = "application/json"
}

Write-Host "=== Test: GET /instance/connect/TH_1?number=584140001234 ===" -ForegroundColor Cyan
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8085/instance/connect/TH_1?number=584140001234" -Method GET -Headers $headers -TimeoutSec 15
    Write-Host "Resultado:" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Error HTTP: $($_.ErrorDetails.Message)" -ForegroundColor Red
    Write-Host "Exception: $($_.Exception.Message)" -ForegroundColor Red
}
