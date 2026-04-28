# Script para probar el checkout de Stripe

Write-Host "=== Test de Stripe Checkout ===" -ForegroundColor Green

# 1. Obtener token JWT
Write-Host "`n1. Obteniendo token JWT..." -ForegroundColor Yellow
$loginBody = @{
    username = "demo"
    password = "demo2025"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/jwt/obtain/" -Method Post -Body $loginBody -ContentType "application/json"
$accessToken = $loginResponse.access

Write-Host "Token obtenido: $($accessToken.Substring(0,50))..." -ForegroundColor Green

# 2. Ver suscripción actual
Write-Host "`n2. Consultando suscripción actual..." -ForegroundColor Yellow
$headers = @{
    "Authorization" = "Bearer $accessToken"
}

try {
    $subscription = Invoke-RestMethod -Uri "http://localhost:8000/api/billing/subscription/" -Method Get -Headers $headers
    Write-Host "Plan actual: $($subscription.plan.name)" -ForegroundColor Green
    Write-Host "Ventas usadas: $($subscription.usage.ventas.usado) / $($subscription.usage.ventas.limite)" -ForegroundColor Green
} catch {
    Write-Host "Error consultando suscripción: $_" -ForegroundColor Red
}

# 3. Crear checkout session para plan PRO
Write-Host "`n3. Creando checkout session para plan PRO..." -ForegroundColor Yellow
$checkoutBody = @{
    plan = "PRO"
} | ConvertTo-Json

try {
    $checkout = Invoke-RestMethod -Uri "http://localhost:8000/api/billing/checkout/" -Method Post -Body $checkoutBody -ContentType "application/json" -Headers $headers
    Write-Host "Checkout URL creada exitosamente!" -ForegroundColor Green
    Write-Host "URL: $($checkout.checkout_url)" -ForegroundColor Cyan
    Write-Host "`nAbre esta URL en tu navegador para completar el pago de prueba" -ForegroundColor Yellow
    Write-Host "Tarjeta de prueba: 4242 4242 4242 4242" -ForegroundColor Yellow
    
    # Abrir automáticamente en el navegador
    Start-Process $checkout.checkout_url
} catch {
    Write-Host "Error creando checkout: $_" -ForegroundColor Red
    Write-Host $_.Exception.Response.StatusCode -ForegroundColor Red
}

Write-Host "`n=== Fin del test ===" -ForegroundColor Green
