# 📜 Reglas de Estandarización de Parseo - TravelHub

Este documento define los estándares **MANDATORIOS** para el sistema de parseo de boletos de TravelHub. El objetivo es asegurar una extracción de datos precisa, robusta y libre de errores financieros, garantizando que el SaaS, el Admin y el Frontend funcionen "como un reloj suizo".

---

## 1. Arquitectura Centralizada

Todo ingreso de boletos debe pasar por **un único punto de entrada**:

*   **Orquestador:** `core.services.ticket_parser_service.TicketParserService`
*   **Lógica de Extracción:** `core.ticket_parser.extract_data_from_text`
*   **Modelos de Salida:** `core.models.boletos.BoletoImportado` -> `core.models.ventas.Venta`

### Flujos de Datos
1.  **SaaS (Email Bot/Celery):** `Email` -> `Texto/HTML` -> `TicketParserService` -> `BoletoImportado` -> `Venta`
2.  **Django Admin:** `Upload Archivo` -> `Signal post_save` -> `TicketParserService` -> `Venta`
3.  **Frontend (React/API):** `Endpoint /api/boletos/upload/` -> `TicketParserService` -> `JSON Response`

---

## 2. Los 10 Mandamientos del Parseo

1.  **Priorizar Estructura sobre Regex:** Si un parser dedicado (`SABRE`, `KIU`) retorna un objeto estructurado (ej: diccionario de tarifas), **USARLO**. No re-procesar con regex plano.
2.  **Limpieza de Montos es Sagrada:**
    *   **NUNCA** confiar en `Decimal(str)` directamente.
    *   **SIEMPRE** limpiar currency codes (`USD`, `EUR`, `VES`) y espacios.
    *   **SIEMPRE** normalizar separadores decimales (coma -> punto) *antes* de convertir.
    *   **FALLBACK:** Si falla, usar `Decimal("0.00")`, nunca crashear.
3.  **Fechas Flexibles:** Los formatos cambian (`02JAN25`, `02/01/2025`, `2-ENE-25`). Usar `dateutil.parser` o diccionarios de meses multilingües.
4.  **Detección de GDS:**
    *   **KIU:** Busca `TICKET ELECTRONICO` + Códigos de aerolínea (e.g. `V0`, `QL`).
    *   **SABRE:** Busca `SABRE`, `Hahn Air`, o patrones de PNR (`[A-Z0-9]{6}`).
    *   **AMADEUS:** Busca `AMADEUS`, `CHECKMYTRIP`, o códigos numéricos específicos.
5.  **Multilinea es la Norma:** Los nombres de pasajeros y rutas a menudo se cortan en saltos de línea (`\n`). Usar `re.DOTALL` con cuidado o limpiar saltos de línea antes de regex simples.
6.  **Templates Dinámicos:** No forzar un solo template HTML.
    *   **KIU:** Usar `ticket_template_kiu_bolivares.html` si detecta `VES`/`Bs` o impuestos nacionales.
    *   **SABRE:** Usar `ticket_template_sabre.html`.
7.  **Logging Exhaustivo:** Loggear *siempre* el `Total Extraído` y el `PNR` en los logs de parseo (`BoletoImportado.log_parseo`).
8.  **No Inventar Datos:** Si el `Total` es 0, dejarlo en 0 y marcar `estado_parseo='ERR'` o alerta. No inventar `0.01`.
9.  **Idempotencia:** Procesar el mismo archivo dos veces debe dar el mismo resultado (o actualizar el existente sin duplicar ventas ciegamente).
10. **Validación Visual:** El PDF generado debe ser una representación fiel. Si el parser extrae basura, el PDF mostrará basura. "Garbage in, Garbage out".
11. **EML > PDF (Regla de Oro Copa/Avianca):** Para boletos que llegan por correo, el archivo `.eml` es la fuente de verdad. Los PDF generados por "Imprimir" suelen tener fuentes corruptas (CID). **SIEMPRE PRIORIZAR EML**.

---

## 3. Estándares de Parsers (`core/parsers/`)

Todos los parsers deben heredar de `core.parsers.base_parser.BaseTicketParser`.

### Mapeo de Datos Base (Schema)

El parser debe retornar un diccionario plano o anidado que `TicketParserService` sepa consumir. Las llaves críticas son:

| Llave Principal | Llaves Alternativas (Legacy) | Tipo | Descripción |
| :--- | :--- | :--- | :--- |
| `total_amount` | `total`, `TOTAL_IMPORTE` | `Decimal/Str` | Monto final a cobrar. Critico. |
| `pnr` | `reservation_code`, `CODIGO_DE_RESERVACION` | `Str(6)` | Localizador del GDS. |
| `ticket_number` | `boleto`, `NUMERO_DE_BOLETO` | `Str` | 13 dígitos (ej: `128-1234567890`). |
| `passenger_name` | `pasajero`, `NOMBRE_PASAJERO` | `Str` | "APELLIDO/NOMBRE". Limpiar `FOID`, `MR`, `MRS`. |
| `issue_date` | `fecha_emision`, `FECHA_DE_EMISION` | `Date/Str` | Fecha de compra. |
| `flights` | `flight_segments`, `vuelos` | `List[Dict]` | Lista de segmentos de vuelo. |

### Reglas Específicas por GDS

#### 🦅 KIU (Avior, Conviasa, Laser, Turpial)
*   **Reto:** Texto plano muy variable, a menudo pegado sin espacios.
*   **Estrategia:** Regex secuencial sobre el texto completo.
*   **Impuestos:** Detectar desglose (`YQ`, `IT`, `E0`). Si hay `VES`/`Bolivares`, activar flag `usar_template_bolivares`.
*   **Vuelos:** Los vuelos pueden aparecer en bloques repetidos. Iterar con `re.finditer`.

#### ⚡ SABRE (Copa, AA, Iberia, etc.)
*   **Reto:** Archivos PDF complejos, estructuras anidadas.
*   **Estrategia Híbrida (Nuevo Estándar):**
    1.  **AI/LLM (Ideal):** Si hay presupuesto/api, pasar a Gemini.
    2.  **Regex Estructurada (Actual):** Buscar bloques delimitados (`ITINERARIO`, `RECIBO`).
    3.  **Segmentos:** Parsear línea por línea buscando patrones de vuelo (`AV 123`, `CM 456`).
    4.  **Validación:** Chequear que `total_amount` > 0.
    5.  **Nombre Pasajero:** Extraer de cabecera "PASAJERO: XXXXX".

79. 
80. #### ✈️ COPA AIRLINES (Copa Connect / Accelya / SPRK)
81. *   **Fuente Crítica:** EL ARCHIVO .EML ES OBLIGATORIO. El PDF transformado suele ser ilegible (basura `(cid:22)`).
82. *   **Headers:** `TicketParserService` **DEBE** preservar los headers del correo (`Subject`, `From`, `Received`). La detección depende de encontrar `ACCELYA.COM` o `FARELOGIX` en los headers.
83. *   **Orden de Detección:** `COPA_SPRK` tiene prioridad sobre `SABRE`. Sabre es un "catch-all" peligroso.
84. *   **Lógica:** Parsear el HTML crudo (`WebReceiptParser` fallará si no hay estructura). Usar `copa_parser.py` que aplica Regex sobre el `decoded_payload`.
85. 
86. ---

## 4. Guía de Mantenimiento y Debugging

### Síntoma: "El Venta se crea con monto 0.00"
*   **Causa Probable:** El parser extrajo el string sucio (ej: `USD 738.71`) y `Decimal()` falló silenciosamente o retorno 0.
*   **Solución:** Verificar `TicketParserService._guardar_venta_acumulativa` y asegurar que se usen las utilidades de limpieza (`clean_money_string`, etc).

### Síntoma: "El PDF sale en blanco"
*   **Causa Probable:** El contexto pasado a `generate_ticket` tiene llaves incorrectas (ej: `fecha` en vez de `fecha_emision`).
*   **Solución:** Revisar `core/ticket_parser.py` -> `generate_ticket` y cotejar con el template HTML.

### Síntoma: "No detecta los vuelos de Avior"
*   **Causa Probable:** Avior cambió el formato (ej: agregó una columna nueva o saltos de línea).
*   **Solución:** Capturar el texto crudo (`raw_text`) y probar regex en regex101.com. Actualizar `core/parsers/kiu_parser.py`.

---

### 6. [Nuevo] Proceso de Generación de PDF y Persistencia

#### 6.1 Ciclo de Vida del PDF
1.  **Parseo**: Extracción de datos crudos (`extract_data_from_text`).
2.  **Inyección Manual (CRÍTICO):** Antes de generar el PDF o validar, el servicio **consulta la base de datos** (`BoletoImportado`).
    *   Si existen `nombre_pasajero_procesado` o `foid_pasajero` manuales (ingresados por usuario), **se inyectan forzosamente** en el diccionario de datos.
    *   *Razón:* Evitar que un re-scaneo del PDF (que suele tener datos faltantes) sobrescriba la corrección manual del usuario con `None`.
3.  **Generación**: `core.ticket_parser.generate_ticket(datos_inyectados)`.
    *   Selecciona plantilla (`ticket_template_sabre.html` vs `kiu` vs `bolivares`) basado en `cod_aerolinea` y `moneda`.
    *   Renderiza HTML con Django Templates.
    *   Convierte a PDF con `WeasyPrint`.
4.  **Guardado**: Se guarda en `BoletoImportado.archivo_pdf_generado`.

#### 6.2 Mejoras Específicas por Parser

**⚡ SABRE (Refactorizado):**
*   **Itinerarios Complejos:** Ahora divide el bloque de texto en segmentos usando `re.split` inteligente para capturar múltiples vuelos (`AV 123`, `CM 456`) que antes se perdían.
*   **Estrategia Híbrida:** Prioriza detección de patrones HTML/Estructurados. Si falla, cae a Regex línea por línea.
*   **Limpieza:** Elimina asteriscos (`*`) y caracteres de control (`\r`) que ensuciaban los Nombres y PNRs.

**🦅 KIU (Optimizado):**
*   **Prioridad HTML:** Si el input es `.eml` o HTML, usa `WebReceiptParser` (BeautifulSoup) para extracción exacta de tablas.
*   **Fallback Texto:** Si es PDF de imagen/texto, usa `KIUParser` con regex secuencial mejorada.
*   **Modo Bolívares:** Detecta automáticamente `VES`, `Bs`, `Bs.S` o `IMPUESTO` local para usar `ticket_template_kiu_bolivares.html`, ajustando el formato de moneda.

#### 6.3 Manejo de Errores Visuales
*   **Render_Field Fix:** Se corrigió un error donde `{% render_field %}` se mostraba como texto plano en `venta_edit_glass.html`. Solución: **Aplanar etiquetas multilinea** y asegurar carga de `widget_tweaks` en `INSTALLED_APPS`.
*   **Cache Busting:** Si los templates se pegan, renombrar archivo (v2) y actualizar vista.

## 5. Checklist para Nuevas Integraciones

Para agregar un nuevo GDS (ej: Amadeus, Travelport):

1.  [ ] Crear `core/parsers/amadeus_parser.py`.
2.  [ ] Heredar de `BaseTicketParser`.
3.  [ ] Implementar `can_parse` (buscar palabras clave únicas).
4.  [ ] Implementar `parse` retornando dict estandarizado.
5.  [ ] Registrar en `core/ticket_parser.py` dentro de la lista de parsers.
6.  [ ] Crear `core/templates/core/tickets/ticket_template_amadeus.html`.
7.  [ ] Subir boleto de prueba y verificar extracción de `Total`.
