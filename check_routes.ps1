
# Script to find all Evolution API route endpoints
$content = docker exec travelhub_project-evolution_api-1 cat /evolution/dist/api/integrations/channel/whatsapp/baileys.router.js
$content | Select-String -Pattern '(get|post|put|delete|patch)\s*\(' | ForEach-Object { $_.Line.Substring(0, [Math]::Min(120, $_.Line.Length)) }
