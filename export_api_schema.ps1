# Script para generar la especificación de OpenAPI estáticamente
# Esto permite que los desarrolladores de frontend y otros consumidores
# tengan acceso a las definiciones sin necesidad de levantar el servidor.

Write-Host "Generando esquema OpenAPI (schema.yml) desde Django..." -ForegroundColor Cyan

python manage.py spectacular --file schema.yml

if ($LASTEXITCODE -eq 0) {
    Write-Host "Esquema generado con éxito en schema.yml" -ForegroundColor Green
    Write-Host "Puedes usar este archivo con generadores de código como orval, swagger-codegen o Postman." -ForegroundColor Yellow
} else {
    Write-Host "Error al generar el esquema OpenAPI" -ForegroundColor Red
}
