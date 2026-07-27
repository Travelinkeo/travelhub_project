$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$artDir = "C:\Users\ARMANDO\.gemini\antigravity\brain\b61c38ba-47ea-41c8-82d1-fd3f1c9fa1de"

$pages = @(
    @{ Name = "real_landing.png"; Url = "http://localhost:8000/" },
    @{ Name = "real_dashboard.png"; Url = "http://localhost:8000/bookings/dashboard/modern/" },
    @{ Name = "real_gds_analyzer.png"; Url = "http://localhost:8000/system/intelligence/gds-analyzer/" },
    @{ Name = "real_brain_assistant.png"; Url = "http://localhost:8000/accounting/asistente/" },
    @{ Name = "real_wiki_gds.png"; Url = "http://localhost:8000/system/wiki/gds/" },
    @{ Name = "real_configuracion.png"; Url = "http://localhost:8000/system/setup/perfil/" }
)

foreach ($p in $pages) {
    $outFile = Join-Path $artDir $p.Name
    Write-Host "Capturing $($p.Name) from $($p.Url)..."
    $tmpFile = Join-Path $env:TEMP $p.Name
    Start-Process -FilePath $chrome -ArgumentList "--headless=new", "--window-size=1920,1080", "--screenshot=$tmpFile", $p.Url -Wait
    if (Test-Path $tmpFile) {
        Copy-Item -Path $tmpFile -Destination $outFile -Force
        Remove-Item -Path $tmpFile -Force
        Write-Host "Successfully saved $outFile"
    } else {
        Write-Host "Failed to capture $($p.Name)"
    }
}
