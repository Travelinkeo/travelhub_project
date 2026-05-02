# Reporte de Optimización del Parser SABRE

## Objetivo
Mejorar la robustez del parser de boletos SABRE para eliminar la necesidad de ajustes manuales constantes y reducir el tiempo de procesamiento de boletos problemáticos.

## Mejoras Implementadas

### 1. Integración con Base de Datos de Aerolíneas (IATA & Placas)
Se ha enriquecido el catálogo de aerolíneas del sistema (`core.Aerolinea`) importando datos de:
- **Tabla Mundial de Aerolíneas (PDF):** +130 aerolíneas con códigos IATA y Numéricos.
- **Lista KIU (Texto):** 20 aerolíneas regionales y venezolanas con sus códigos de placa (ej. Rutaca 765).

### 2. Normalización Inteligente de Aerolíneas
Se actualizó la lógica de `normalize_airline_name` en `core/airline_utils.py` y `sabre_parser.py` para usar 4 niveles de prioridad:

*   **PRIORIDAD SUPERIOR (Nueva):** Búsqueda por **Prefijo de Boleto (Placa)**.
    *   Si el boleto es `045-1234567890`, el sistema busca la aerolínea con código numérico `045` en la BD.
    *   Esto elimina la ambigüedad de nombres comerciales vs legales (ej. "LAN AIRLINES S.A." -> Detectado automáticamente como "LATAM Airlines" por el código 045).
*   **PRIORIDAD 0:** Mapeo de Nombres Legales Conocidos (ej. "AEROVIAS DEL CONTINENTE" -> "AVIANCA").
*   **PRIORIDAD 1:** Código IATA del Vuelo (ej. "AV123" -> Busca "AV" en BD).
*   **PRIORIDAD 2:** Código IATA en el Nombre (ej. "5R-RUTACA" -> Busca "5R" en BD).

### 3. Propagación de Aerolínea del Encabezado
Si los segmentos de vuelo no indican claramente la aerolínea (común en boletos viejos o códigos compartidos), el parser ahora **propaga** la aerolínea detectada en el encabezado del boleto a todos los segmentos vacíos.

## Resultados de la Prueba de Regresión
Se ejecutó un lote de prueba con **37 boletos reales** (incluyendo casos previamente fallidos de Avianca, Copa, LAN, y aerolíneas asiáticas).

*   **Tasa de Éxito:** 36/37 Boletos Parseados y PDFs Generados.
    *   *Único fallo:* Boleto de SATA (PDF corrupto a nivel de capa de texto, requiere OCR/Re-emisión).
*   **Caso LAN (LATAM):** Parseado correctamente como "LATAM Airlines" gracias a la nueva lógica.
*   **Caso Avianca/Taca:** Parseados correctamente unificando bajo "Avianca".
*   **Caso Air France/KLM/China Eastern:** Parseados correctamente usando códigos IATA/Placas.

## Conclusión
El sistema ahora es capaz de identificar aerolíneas incluso si el nombre en el texto es desconocido, siempre que el número de boleto o el código de vuelo sean válidos y existan en la base de datos. Esto reduce drásticamente los errores de "Aerolínea no identificada".
