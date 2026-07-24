"""
Provider Chain para TravelHub AI — abstracción de múltiples proveedores
con failover automático, circuit breaker y trazabilidad de métricas.

Jerarquía de fallback:
  1. Gemini (estructurado + texto) — principal
  2. OpenAI (estructurado + texto) — fallback primario
  3. DeepSeek (solo texto) — emergencia

Cada proveedor implementa AbstractBaseProvider.
Usar FallbackRouter para invocar la cadena completa.
"""
