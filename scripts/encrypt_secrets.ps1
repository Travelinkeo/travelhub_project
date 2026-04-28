<#
.SYNOPSIS
    Script de cifrado "Protocolo Fantasma" para TravelHub.
    Cifra y descifra archivos .env para que no residan en texto plano.

.DESCRIPTION
    Uso:
    .\encrypt_secrets.ps1 -Action encrypt
    .\encrypt_secrets.ps1 -Action decrypt
#>

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("encrypt", "decrypt")]
    [string]$Action
)

$EnvFile = ".env"
$EncFile = ".env.gpg"

# Verificar si GPG está instalado
if (!(Get-Command gpg -ErrorAction SilentlyContinue)) {
    Write-Error "GPG no está instalado. Instálalo para usar el Protocolo Fantasma."
    exit 1
}

if ($Action -eq "encrypt") {
    if (Test-Path $EnvFile) {
        Write-Host "Cifrando $EnvFile..." -ForegroundColor Cyan
        gpg --symmetric --cipher-algo AES256 --output $EncFile $EnvFile
        Write-Host "¡Éxito! Archivo cifrado creado en $EncFile" -ForegroundColor Green
        Write-Host "ADVERTENCIA: Deberías eliminar el $EnvFile original en producción." -ForegroundColor Yellow
    } else {
        Write-Error "No se encontró el archivo $EnvFile"
    }
} elseif ($Action -eq "decrypt") {
    if (Test-Path $EncFile) {
        Write-Host "Descifrando $EncFile..." -ForegroundColor Cyan
        gpg --decrypt --output $EnvFile $EncFile
        Write-Host "¡Éxito! Archivo descifrado creado en $EnvFile" -ForegroundColor Green
    } else {
        Write-Error "No se encontró el archivo cifrado $EncFile"
    }
}
