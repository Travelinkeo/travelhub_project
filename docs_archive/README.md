# TravelHub - CRM/ERP/CMS para Agencia de Viajes

TravelHub es una aplicación web integral diseñada para agencias de viajes, combinando funcionalidades de CRM (Customer Relationship Management), ERP (Enterprise Resource Planning) y CMS (Content Management System).

## 🤖 Linkeo - Asistente Virtual Inteligente

**Linkeo** es el asistente virtual de TravelHub, entrenado con conocimiento completo del sistema.

- **Ubicación**: Widget flotante en todas las páginas + página dedicada `/chatbot`
- **Tecnología**: Google Gemini AI con sistema de fallback
- **Conocimiento**: TODO el sistema TravelHub (módulos, flujos, comandos, integraciones)
- **Capacidades**: Explica funcionalidades, guía usuarios, responde consultas, conecta con agentes

**Documentación completa**: Ver [LINKEO_CHATBOT.md](LINKEO_CHATBOT.md)

**APIs disponibles**:
- `POST /api/chatbot/message/` - Enviar mensajes
- `GET /api/chatbot/quick-replies/` - Respuestas rápidas
- `GET /api/chatbot/status/` - Estado del bot

## Características Principales

**CRM:**
* Gestión de Clientes: Información detallada, historial, cálculo de cliente frecuente.
* Gestión de Proveedores: Niveles (consolidador, mayorista, otros).
* Catálogo de Productos/Servicios: Boletos aéreos, hoteles, paquetes, etc., vinculados a proveedores.
* Generación y envío de Cotizaciones.

**ERP:**
* Modelos de Venta, Factura y Asiento Contable.
* Registro automático de ingresos y egresos (conceptual).
* API REST para CRUD de ventas, facturas y asientos contables.
* Importación y parseo de Boletos (PDF/TXT/EML) de KIU, SABRE, AMADEUS.

## Manual de Usuario: Flujo de Venta y Contabilidad

Esta guía describe el proceso completo desde la importación de un boleto hasta la generación de documentos contables.

### Paso 1: Importación y Creación de la Venta

1.  **Subir un Boleto:** En el panel de administración, ve a "Boletos Importados" y haz clic en "Añadir Boleto Importado". Selecciona un archivo de boleto (`.pdf`, `.eml`, `.txt`) y guárdalo.
2.  **Proceso Automático:** Al guardar, el sistema automáticamente:
    *   Parsea el boleto y extrae toda la información relevante.
    *   Crea o actualiza una **Venta** agrupando todos los boletos que compartan el mismo **Localizador**.
    *   La `Venta` se crea **sin un Cliente asignado**, lista para ser procesada.

### Paso 2: Enriquecimiento de la Venta (Costos y Ganancias)

1.  **Ir a la Venta:** Ve a la sección "Ventas / Reservas". Busca la venta creada en el paso anterior (puedes usar el localizador para encontrarla).
2.  **Añadir Detalles Financieros:** Haz clic en la venta para ver su detalle. En la sección inferior **"Items de Venta/Reserva"**, verás los boletos como items individuales. Aquí puedes rellenar los campos financieros:
    *   **Proveedor del Servicio:** Asigna el proveedor que emitió el boleto.
    *   **Costo Neto Proveedor:** El costo base del servicio.
    *   **Fee Emisión Proveedor:** El fee que cobra el proveedor por la emisión.
    *   **Comisión Agencia (Monto):** La comisión que ganas del proveedor.
    *   **Fee Interno Agencia:** Tu fee de servicio propio.
3.  **Guardar los Cambios:** Una vez rellenados los datos, guarda la `Venta`.

### Paso 3: Facturación al Cliente

1.  **Seleccionar la Venta:** En la lista de "Ventas / Reservas", marca la casilla de la venta que acabas de editar.
2.  **Ejecutar Acción de Facturar:** En el menú desplegable de "Acciones" (en la parte superior), selecciona **"Asignar Cliente y Generar Factura"** y haz clic en "Ir".
3.  **Asignar Cliente:** En la página intermedia, selecciona el `Cliente` al que le vas a facturar y haz clic en "Confirmar y Facturar".
4.  **Resultado:**
    *   La `Venta` ahora tendrá el cliente asignado.
    *   Se creará una nueva `Factura` en la sección "Facturas de Clientes".
    *   Esta `Factura` tendrá un **PDF adjunto**, generado automáticamente con el formato de tu modelo.

### Paso 4: Liquidación al Proveedor (Cuentas por Pagar)

1.  **Seleccionar la Venta:** Vuelve a la lista de "Ventas / Reservas" y selecciona la misma venta (que ahora ya tiene cliente y factura).
2.  **Ejecutar Acción de Liquidar:** En el menú de "Acciones", selecciona **"Generar Liquidación a Proveedor(es)"** y haz clic en "Ir".
3.  **Resultado:**
    *   El sistema calculará automáticamente cuánto se le debe a cada proveedor involucrado en la venta, usando la fórmula: `(Costo Neto + Fee Proveedor) - Comisión Agencia`.
    *   Se creará un nuevo registro en la sección **"Liquidaciones a Proveedores"** (que ahora es visible en el menú principal del admin).
    *   Este registro representa una **cuenta por pagar** al proveedor.

Este flujo de trabajo te permite mantener un control detallado de cada etapa del proceso de venta.

---

## Detalles Técnicos

* **Backend:** Django 5.x, Django REST Framework.
* **Base de Datos:** SQLite (desarrollo), preparada para PostgreSQL (producción).
* **Frontend (inicial):** Django Templates. PWA básica.
* **Parseo de Boletos:** PyMuPDF, expresiones regulares.
* **Configuración:** Español, Zona Horaria América/Caracas.

## Integración Continua (CI) y Calidad de Código

Se incluye un pipeline de GitHub Actions (`.github/workflows/ci.yml`) que se ejecuta en pushes y pull requests contra `main` y `master`.

Etapas principales:
1. Lint & Tests (matriz Python 3.12 / 3.13)
    * `ruff check .` (estilo, errores comunes, seguridad básica, orden de imports)
    * `ruff format --check .` (verifica formateo consistente)
    * `pytest --cov --cov-report=xml --cov-fail-under=71 -q` (baseline actual 71%)
    * Publicación de `coverage.xml` como artifact.
2. Auditoría de dependencias
    * `pip-audit` genera `pip-audit.json` (artifact) y marca el job si encuentra vulnerabilidades.

Archivos de configuración relevantes:
* `requirements-dev.txt`: dependencias de desarrollo (ruff, black, isort, pytest-cov, coverage, pip-audit).
* `.ruff.toml`: reglas de lint/format (line-length=100, select de errores y seguridad básica).
* `.coveragerc`: fuentes medidas (excluye migraciones, tests, `manage.py`).

### Ejecución Local Rápida

```bash
pip install -r requirements-dev.txt
ruff check .
ruff format .  # Para aplicar formateo automático (opcional)
pytest --cov -q
```

Para ver líneas faltantes:
```bash
pytest --cov --cov-report=term-missing
```

Si necesitas exigir un umbral distinto localmente:
```bash
pytest --cov --cov-fail-under=80 -q
```

### Auditoría de Dependencias Local
```bash
pip install pip-audit
pip-audit
```

### Filosofía
* El umbral de cobertura actual (71%) refleja el primer incremento sobre el estado de partida (70%) sin bloquear PRs.
* Plan: incrementos pequeños (1–2 puntos) por iteración: próximo objetivo 73% y luego 75%; después avanzar a 80–85% priorizando módulos críticos.
* Objetivo estratégico: >85% en lógica de dominio (`core/models.py`, parsers y utilidades de auditoría).
* `ruff` reemplaza a múltiples herramientas (flake8, isort, pyupgrade, algunas reglas de seguridad) simplificando mantenimiento.

### Próximos Mejores Pasos (Opcional)
* Añadir `pip-audit` en modo SARIF para integración con la pestaña de seguridad de GitHub.
* Incorporar `bandit` para análisis estático adicional de seguridad.
* Generar badge de cobertura con un paso que procese `coverage.xml` (o usar Codecov).
* Cache selectivo de la carpeta `.pytest_cache` para acelerar builds.


## Instalación

1.  **Clonar el repositorio (si aplica) o crear la estructura de carpetas.**

2.  **Crear y activar un entorno virtual:**
    ```bash
    python -m venv venv
    ```
    * Windows: `.\venv\Scripts\activate`
    * Unix/Linux/macOS: `source venv/bin/activate`

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar variables de entorno:**
    Copia `.env.example` a `.env` y edita los valores.
    ```bash
    cp .env.example .env
    ```

5.  **Levantar Postgres (opcional recomendado) con docker-compose:**
    ```bash
    docker-compose up -d db
    ```
    Ajusta variables en `.env` (ver `.env.example`). Si no defines `POSTGRES_HOST` el sistema usará SQLite como fallback.

6.  **Realizar migraciones de la base de datos:**
    ```bash
    python manage.py migprate
    ```

7.  **Crear un superusuario (administrador):**
    ```bash
    python manage.py createsuperuser
    ```

8.  **Cargar datos iniciales (fixtures):**
    ```bash
    python manage.py loaddata paises.json
    python manage.py loaddata monedas.json
    python manage.py loaddata clientes.json
    python manage.py loaddata proveedores.json
    python manage.py loaddata productos_servicios.json
    ```

### Nueva Opción Recomendada: Comando Unificado de Catálogos

En lugar de múltiples `loaddata`, se puede usar el comando idempotente `load_catalogs` que además soporta actualización (`--upsert`), pre‑validación (`--dry-run`) y ahora incluye ciudades.

Ejemplos:
```bash
python manage.py load_catalogs --only paises monedas --upsert
python manage.py load_catalogs --only ciudades --dry-run
python manage.py load_catalogs  # carga todos los catálogos soportados cuyos archivos existan
```

Archivos esperados por defecto (ubicados en `fixtures/`):
```
 p a i s e s . j s o n
 monedas.json
 ciudades.json
 proveedores.json
 clientes.json
 productos_servicios.json
```

Formato `ciudades.json` (lista de objetos):
```json
[
    {"nombre": "Caracas", "pais_codigo_iso_2": "VE", "region_estado": "Distrito Capital"},
    {"nombre": "Medellín", "pais_codigo_iso_2": "CO", "region_estado": "Antioquia"}
]
```
Claves soportadas para identificar país:
* `pais_codigo_iso_2` (preferido)
* `pais_codigo_iso_3` (alternativo)

Regla de unicidad aplicada (según el modelo `Ciudad`): `(nombre, pais, region_estado)`.

Si un país referenciado no existe se detiene con error (para visibilidad) salvo en modo `--dry-run`, donde la fila se marca como omitida.

Campos opcionales ignorados simplemente no se actualizan salvo que se utilice `--upsert`.

Para CSV: proveer encabezados equivalentes (`nombre,pais_codigo_iso_2,region_estado`).

## Autenticación (Legacy Token vs JWT)

Actualmente coexisten dos mecanismos mientras se completa la migración:

1. Legacy Token (endpoint `/api/auth/login/`) devuelve `{"token": "..."}`.
2. JWT (endpoints SimpleJWT):
    * Obtener par: `POST /api/auth/jwt/obtain/ {"username": "u", "password": "p"}` → `{access, refresh}`
    * Refresh: `POST /api/auth/jwt/refresh/ {"refresh": "..."}` → nuevo `access` (y opcional nuevo `refresh`).
    * Verificar: `POST /api/auth/jwt/verify/ {"token": "..."}`.
    * Logout (blacklist refresh): `POST /api/auth/jwt/logout/ {"refresh": "..."}`.

El frontend (`frontend/src/lib/api.ts`) ya soporta ambos (`login` y `loginJwt`). Nuevo desarrollo debe preferir JWT.

Rotación configurada (`ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`). Ajusta lifetimes mediante variables:
```
JWT_ACCESS_MINUTES=15
JWT_REFRESH_DAYS=7
```

## Uso

1.  **Iniciar el servidor de desarrollo:**
    * Windows: Ejecuta `iniciar.bat` o `python manage.py runserver`
    * Unix/Linux/macOS: Ejecuta `sh start.sh` o `python manage.py runserver`

2.  Abre tu navegador y ve a `http://127.0.0.1:8000/`.
3.  Para acceder al panel de administración de Django, ve a `http://127.0.0.1:8000/admin/`.

## Parser de Boletos (KIU & Sabre)

El sistema unifica el parseo de boletos en `core/ticket_parser.py` mediante detección heurística del GDS.

### Detección de GDS
Orden de prioridad:
1. Sabre: se detecta por patrones como `ITINERARY DETAILS`, `PREPARED FOR` + `RESERVATION CODE` o encabezados de e‑ticket de Sabre.
2. KIU: requiere alguno de `KIUSYS.COM`, `E-TICKET ITINERARY RECEIPT`, `BOOKING REF`, patrón `C1/XXXXXX` o combinación `ISSUE DATE/FECHA DE EMIS` + `PASSENGER ITINERARY RECEIPT`.
Si ningún patrón coincide se devuelve `{"error": "GDS no reconocido"}`.

### Campos Normalizados (Sabre)
El parser Sabre genera un diccionario principal con claves:
* `SOURCE_SYSTEM`: `SABRE`
* `preparado_para`: Nombre bruto formateado (ej: `PEREZ/JOSE`)
* `documento_identidad`: Código extraído entre corchetes tras el nombre; si no existe se devuelve `-`
* `codigo_reservacion`, `numero_boleto`, `fecha_emision`, `fecha_emision_iso`
* `aerolinea_emisora`, `agente_emisor`, `numero_iata`, `numero_cliente`
* `fare`, `fare_currency`, `fare_amount`
* `total`, `total_currency`, `total_amount`
* `vuelos`: Lista de segmentos.

Cada elemento de `vuelos` contiene (cuando se puede extraer):
* `fecha_salida`, `fecha_llegada` en formato `DD-MM-YYYY`
* `fecha_salida_iso`, `fecha_llegada_iso` en formato ISO `YYYY-MM-DD`
* `numero_vuelo`, `aerolinea`
* `origen` y `destino`: dict `{ciudad, pais}`
* `hora_salida`, `hora_llegada`, `terminal_salida`, `terminal_llegada`
* `cabina`, `equipaje`, `codigo_reservacion_local`
* `co2_valor`, `co2_unidad` (si se encuentra una línea de emisiones tipo `397.86 kg CO2`)
* Se formatean a `DD-MM-YYYY` y adicionalmente se generan variantes ISO.
* Si un segmento carece de `fecha_llegada`, se infiere: misma fecha salvo que `hora_llegada < hora_salida`, en cuyo caso se suma 1 día.

### Normalización Monetaria
La función `_parse_currency_amount` separa moneda (tres letras) y monto para campos `fare` y `total`, poblando `*_currency` y `*_amount`.

### Plantillas PDF
`core/pdf_generator.py` transforma la salida Sabre al contexto requerido por `core/templates/core/tickets/ticket_template_sabre.html`.
* Se garantiza siempre un valor (`-`) para `pasajero.documento_identidad`.
* Campos no presentes en el correo quedan en blanco o `-` según corresponda.

### Pruebas Automatizadas
Se añadió `pytest` y el archivo `tests/test_sabre_parser_enhanced.py` que valida:
* Extracción de documento de identidad.
* Conteo de segmentos (>1 para boletos multi-tramo).
* Formato de fechas y presencia de variantes ISO.
* Normalización de CO2.

Para ejecutar las pruebas:
```bash
python -m pytest -q tests/test_sabre_parser_enhanced.py
```

### Extensión Futura
* Añadir parsers para Amadeus y Travelport (placeholders ya definidos).
* Consolidar un esquema pydantic para validación estricta.
* Manejo de timezone y duración de vuelo calculada.
* Captura de equipaje detallada (peso/piezas) y estatus del segmento.

## Contrato de Normalización (`normalized`)

Cada parseo de boleto (KIU, SABRE y futuros) inyecta un bloque `normalized` en el dict resultante mediante `normalize_common_fields`. Este bloque provee una interfaz estable para consumo por API, generación de PDF, analítica y futuras integraciones sin depender de claves específicas de cada GDS.

### Campos Base
| Clave | Tipo | Descripción |
|-------|------|-------------|
| source_system | str | GDS de origen (`KIU`, `SABRE`, etc.). |
| ticket_number | str/None | Número de boleto si se detecta (con guiones o limpio según fuente). |
| reservation_code | str/None | PNR limpio (sin prefijo `C1/` para KIU). |
| reservation_code_full | str/None | PNR completo (ej. `C1/ABC123`). |
| passenger_name_raw | str/None | Nombre crudo `APELLIDOS/NOMBRES`. |
| passenger_name | str/None | Nombre legible (`Nombres Apellidos`). |
| airline_name | str/None | Nombre de la aerolínea emisora (cuando disponible). |
| issuing_agent | str/None | Agente emisor. |
| issuing_date_iso | str/None | Fecha emisión en formato `YYYY-MM-DD`. |
| fare_currency / fare_amount | str / str | Moneda y monto base de la tarifa. |
| total_currency / total_amount | str / str | Moneda y monto total cobrado. |
| taxes_currency / taxes_amount | str / str | Derivado (o reportado) = total - fare, misma moneda. |
| itinerary_text | str/None | Texto crudo del itinerario (cuando no hay estructura completa). |
| segments | list[dict] | Segmentos estructurados (ver abajo). |

### Segmentos (`segments`)
Cada elemento incluye (cuando se puede inferir):
| Clave | Descripción |
|-------|-------------|
| segment_index | Índice 1-based. |
| source_system | GDS de origen del segmento. |
| flight_number | Número de vuelo (sin separar código marketing). |
| marketing_airline | Código de aerolínea (2 letras) inferido del vuelo. |
| origin / destination | Código de ciudad/IATA (KIU heurístico, SABRE desde texto estructurado). |
| departure_date_iso / arrival_date_iso | Fechas ISO. Arrival se infiere (+1 día) si cruza medianoche. |
| departure_time / arrival_time | Horas `HH:MM` si disponibles. |
| cabin | Cabina (SABRE). |
| baggage_allowance | Franquicia equipaje (SABRE). |
| terminal_departure / terminal_arrival | Terminales si se detectan. |
| co2_value / co2_unit | Emisiones de CO2 (si aparecen). |
| duration_minutes | Duración calculada (SABRE) soporta cruce de medianoche. |
| layover_minutes | Minutos de conexión respecto al segmento previo (SABRE multi‑tramo). |

Limitaciones actuales KIU: segmentos sin horas y sin arrival_date por falta de datos explícitos; se provee sólo flight_number, origin, destination y (si es posible) departure_date_iso derivada de la fecha de emisión + token ddMMM.

### Consistencia de Montos
Para entradas con `fare`, `taxes` (reportado o derivado) y `total` en la misma moneda:
* `amount_consistency`: `OK` si ambas condiciones se cumplen (|total - (fare+taxes)| ≤ 0.01 y |taxes - (total - fare)| ≤ 0.01) o `MISMATCH` en caso contrario.
* `amount_difference`: `total - (fare + taxes)` (signado) en formato `±DD.DD`.
* `taxes_amount_expected`: Valor esperado de taxes (= total - fare).
* `taxes_difference`: taxes_reportado - taxes_esperado.
* En mismatch puede añadirse `amount_difference_taxes` (sinónimo de `taxes_difference`).

Se registran `logger.warning` con detalles del boleto cuando hay mismatch para facilitar auditoría.

### Reglas y Fallbacks
1. No se eliminan claves originales del parseo bruto; `normalized` sólo añade.
2. Si faltan fechas de segmento pero hay horas, se usa `issuing_date_iso` como fallback para permitir cálculo de duración y layover.
3. `taxes_amount` sólo se calcula si no viene proporcionado (para poder detectar inconsistencias si la fuente ya lo entregó).
4. Tolerancia monetaria fija: 0.01 (puede parametrizarse en el futuro). 

### Evolución Planeada
| Mejora | Estado |
|--------|--------|
| Mapear origin/destination a códigos IATA normalizados | Pendiente |
| Añadir horas/arrival completas en KIU | Pendiente |
| Parser Amadeus/Travelport alimentando mismo contrato | Pendiente |
| Validación cruzada fare + taxes = total con múltiples monedas (multi‑cambio) | Pendiente |
| Exponer contrato en documentación OpenAPI/DRF | Pendiente |

### Ejemplo de Uso
```python
from core import ticket_parser

raw = ticket_parser._parse_sabre_ticket(sabre_text)
n = raw["normalized"]
if n.get('amount_consistency') == 'MISMATCH':
    # trigger alerta o registrar auditoría
    pass
for seg in n.get('segments', []):
    print(seg['flight_number'], seg['departure_date_iso'], seg['duration_minutes'])
```

Esto permite desacoplar la representación interna de cada GDS de los consumidores aguas arriba (API, PDFs, BI).

## Auditoría (Logs de Eliminación)

Implementación de auditoría con acciones `CREATE`, `UPDATE`, `DELETE` (Venta, ItemVenta) y `STATE` (cambios de estado de Venta).

Endpoint API (solo lectura, autenticado): `/api/audit-logs/` (sin paginación por ahora). Admite filtros por `modelo`, `accion`, rango de fechas (`created_from`, `created_to`) y búsqueda en `object_id`/`descripcion` vía `?search=`.

Evolución planificada: creación (`CREATE`), actualización (`UPDATE` con diffs compactos, `DELETE`, `STATE`)
 con detalles completos en `AUDIT.md`.

Resumen rápido del modelo `AuditLog`:
* `modelo` + `object_id`
* `accion` (`CREATE`, `UPDATE` con diff reducido, `DELETE`, `STATE`)
* `venta` (FK opcional; actualmente `CASCADE`)
* `descripcion` y campos prev/nuevos (se usan para `STATE`)
* Diffs en `metadata_extra.diff` para `UPDATE` (lista blanca de campos de texto)
* `metadata_extra` extensible (ej: `venta_id`, `diff`)

Ver documentación ampliada: `AUDIT.md`.

## Esquema de Colores por GDS (PDF Tickets)

Para diferenciar visualmente el origen del boleto, cada GDS usa una paleta primaria específica en su plantilla PDF:

| GDS        | Color Primario | Color Secundario / Acento | Notas |
|------------|----------------|---------------------------|-------|
| SABRE      | Rojo #D92B2B   | Degradado hacia #B32020   | Ya implementado en `ticket_template_sabre.html`. |
| KIU        | Azul #0D1E40   | Azul medio #2173A6        | Plantilla revertida a esquema azul original. |
| AMADEUS    | Turquesa #008B8B | Turquesa claro #00A8A8  | Pendiente creación de plantilla. |
| TRAVELPORT | Negro #111827  | Gris #374151 / Borde #E5E7EB | Pendiente creación de plantilla. |

### Convenciones de Estilo
* Mantener misma estructura semántica entre plantillas (`ticket-header`, `ticket-body`, `ticket-footer`).
* Tipografías: `Poppins` para títulos, `Open Sans` para cuerpo; monospace para itinerario.
* Evitar sombras pesadas (WeasyPrint + consistencia visual). Solo usar si es claramente distintivo.
* No mezclar degradados entre GDS salvo que se defina expresamente (actualmente solo Sabre).

### Próximos Pasos Propuestos
1. Crear `ticket_template_amadeus.html` con paleta turquesa.
2. Crear `ticket_template_travelport.html` con paleta negro/gris.
3. Extraer variables de color en cada plantilla a un bloque `:root` documentado.
4. (Opcional) Centralizar estilos comunes en un fragmento reutilizable e inyectarlo desde el generador para reducir duplicación.
5. Añadir pruebas de snapshot visual (hash de HTML) para evitar regresiones de color.

### Ejemplo de Bloque CSS Base (Referencia)
```css
:root {
    --tk-primary: <#COLOR_PRIMARIO>;
    --tk-accent: <#COLOR_ACENTO>;
    --tk-text-dark: #2c3e50;
    --tk-text-light: #495057;
    --tk-background-light: #f8f9fa;
    --tk-border-light: #e9ecef;
}
```

## Normalización de CODIGO_IDENTIFICACION (FOID / D.IDENTIDAD)

En KIU el FOID es obligatorio para cerrar la reserva y emitir el boleto. Para garantizar consistencia se centralizó la lógica en `core/identification_utils.py` con la función `normalize_codigo_identificacion` y se reutiliza tanto en el parser interno como en el externo.

Reglas aplicadas:
1. Se localiza la línea que inicia con alguno de los prefijos válidos: `FOID`, `FOID/D.IDENTIDAD`, `/D.IDENTIDAD`, `D.IDENTIDAD`.
2. Se toma únicamente el contenido hasta el fin de esa línea (no se arrastran líneas siguientes).
3. Se eliminan repetidamente prefijos redundantes al inicio (p.ej. `/D.IDENTIDAD: FOID:`) para quedarse solo con la parte derecha.
4. Si aparece la palabra `RIF` a la derecha se corta todo desde allí para evitar contaminar el identificador con información fiscal.
5. Se extrae el primer token alfanumérico de longitud >= 3 (fallback a cualquier token alfanumérico si no existe uno de esa longitud).
6. Si excepcionalmente no se encuentra línea válida (escenario no esperado en KIU), se devuelve `"No encontrado"`.

Ejemplos:
| Entrada Línea FOID                               | Resultado |
|--------------------------------------------------|-----------|
| `FOID/D.IDENTIDAD: IDEPPE151144`                 | `IDEPPE151144` |
| `D.IDENTIDAD: ABC12345`                          | `ABC12345` |
| `FOID: XYZ999`                                   | `XYZ999` |
| `/D.IDENTIDAD: FOID: DUPLICATE777`               | `DUPLICATE777` |

Pruebas automatizadas en `tests/test_codigo_identificacion_normalization.py` validan estos casos para ambos parsers (interno y externo).

Motivación: Evitar divergencias entre parsers y prevenir regresiones si se extiende la lógica de parseo en el futuro.

## Reglas de Estados de Venta y Fidelidad

La entidad `Venta` maneja estados financieros y operativos. Para evitar que la lógica automática sobrescriba decisiones operativas, se separan dos grupos:

Estados financieros base (auto-gestionados por pagos):
* `PEN` (Pendiente de Pago)
* `PAR` (Pagada Parcialmente)
* `PAG` (Pagada Totalmente)

Estados operativos / avanzados (solo cambian manualmente o por procesos de negocio externos):
* `CNF` (Confirmada) – proveedores y servicios asegurados.
* `VIA` (En Proceso/Viaje) – el viaje / servicio ha iniciado.
* `COM` (Completada) – todos los servicios han finalizado satisfactoriamente.
* `CAN` (Cancelada)

### Reglas de Transición Automática
1. Cada vez que se inserta / actualiza un `PagoVenta` confirmado o un `FeeVenta`, se recalculan los totales y saldo mediante señales (`post_save`).
2. Si el estado actual está en el conjunto financiero base y el saldo cambia:
     * `saldo_pendiente == total_venta` -> permanece `PEN`.
     * `0 < saldo_pendiente < total_venta` -> `PAR`.
     * `saldo_pendiente <= 0` -> `PAG`.
3. Si la venta está en un estado operativo (`CNF`, `VIA`, `COM`, `CAN`), los pagos no la devuelven a un estado financiero; solo se actualizan los montos.

### Asignación de Puntos de Fidelidad
* Se otorga 1 punto por cada 10 unidades monetarias de `total_venta` (división entera/truncada) y solo si el resultado es > 0.
* Ventas con total < 10 no generan puntos y la bandera permanece en `False`.
* Los puntos se disparan cuando:
    * La venta pasa a `COM` o `PAG`, **o**
    * El `saldo_pendiente` llega a 0 aunque el estado operativo sea distinto (ej. `CNF`, `VIA`).
* La bandera `puntos_fidelidad_asignados` se marca únicamente cuando efectivamente se acreditan puntos (>0); evita falsos positivos.
* Idempotencia garantizada: pagos posteriores (incluyendo sobrepagos o montos 0) y recálculos no vuelven a sumar.
* La lógica vive en un método interno (`Venta._evaluar_otorgar_puntos`) invocado desde `save()`, `recalcular_finanzas()` y señales de pagos.

### Escenarios Cubiertos por Tests
* Pago parcial -> transición a `PAR`.
* Pago total directo -> `PAG` y puntos asignados.
* Pagos incrementales -> puntos solo al final (sin duplicar).
* Estado `COM` manual antes de pagos -> puntos inmediatos; luego pago no duplica.
* Estado `CNF` + pago total -> puntos al completar el pago, preservando estado.
* Estado `VIA` (operativo) + pagos parciales y totales -> estado no se sobrescribe; puntos al saldo cero.
* Venta con total < 10 -> no otorga puntos, flag permanece `False`.
* Idempotencia: sobrepago o pagos adicionales tras otorgar puntos no incrementan el saldo de puntos.

### Extensiones Futuras Sugeridas
* Motor de workflow configurable (reglas declarativas).
* Historial de cambios de estado (`VentaEstadoHistorial`).
* Políticas de puntos por tipo de producto / margen.
* Hooks para notificaciones (email / webhooks) al llegar a `PAG` o `COM`.

## Sistema de Contabilidad Integrada (VEN-NIF)

TravelHub incluye un módulo completo de contabilidad que cumple con el marco normativo venezolano (VEN-NIF) para agencias de viajes.

### Características Principales

**Dualidad Monetaria**: Maneja simultáneamente USD (moneda funcional) y BSD (moneda de presentación legal).

**Integración Automática**: Genera asientos contables automáticamente desde facturas y pagos.

**Diferencial Cambiario**: Calcula y registra ganancias/pérdidas por fluctuaciones de tasa BCV.

**Contribución INATUR**: Provisiona automáticamente el 1% sobre ingresos brutos mensuales.

### Comandos Disponibles

```bash
# Actualizar tasa BCV
python manage.py actualizar_tasa_bcv --tasa 45.50

# Provisionar INATUR mensual
python manage.py provisionar_inatur --mes 1 --anio 2025

# Cargar plan de cuentas inicial
python manage.py loaddata plan_cuentas_venezuela.json
```

### Flujo Automático

1. Usuario crea **Factura Venezuela** → Sistema genera asiento contable
2. Usuario registra **Pago** → Sistema calcula diferencial cambiario y genera asiento
3. Fin de mes → Ejecutar comando INATUR para provisión

**Documentación completa**: Ver [CONTABILIDAD_VENEZUELA_VEN_NIF.md](CONTABILIDAD_VENEZUELA_VEN_NIF.md)

---

## Componentes de Venta y Metadata Ampliada

Se introdujo el modelo `VentaParseMetadata` para snapshots de parseo de boletos (KIU / SABRE) con campos de consistencia monetaria (`amount_consistency`, `amount_difference`, `taxes_amount_expected`, `taxes_difference`) y estructura de segmentos (`segments_json`). Las propiedades dinámicas en `Venta` exponen el snapshot más reciente sin duplicar columnas.

### Nuevos Modelos de Componentes (Multi‑Producto)

Ampliación de la plataforma para manejar más tipos de producto dentro de una misma `Venta`:

| Modelo | Propósito | Notas |
|--------|----------|-------|
| `AlquilerAutoReserva` | Reservas de autos | Ciudades de retiro/devolución, categoría, compañía, seguro. |
| `EventoServicio` | Tickets / eventos puntuales | Fecha/hora, ubicación, asiento / zona. |
| `CircuitoTuristico` | Itinerario multi‑día | Agrupa días (`CircuitoDia`), descripción general. |
| `CircuitoDia` | Día individual del circuito | Ciudad, actividades/resumen, unicidad (circuito, día_numero). |
| `PaqueteAereo` | Paquete combinado (vuelos + hotel, etc.) | Campo JSON flexible `resumen_componentes`. |
| `ServicioAdicionalDetalle` | Servicios complementarios | Tipos enumerados (Seguro, SIM, Lounge, etc.). |

Todos referencian `Venta` mediante `ForeignKey` y se exponen en el `VentaSerializer` como listas read‑only:
`alquileres_autos`, `eventos_servicios`, `circuitos_turisticos`, `paquetes_aereos`, `servicios_adicionales`.

### Endpoints API

Prefijo `/api/` (router DRF):

```
alquileres-autos/
eventos-servicios/
circuitos-turisticos/
circuitos-dias/
paquetes-aereos/
servicios-adicionales/
```

### Ejemplo Creación (JSON)

```json
POST /api/alquileres-autos/
{
    "venta": 123,
    "categoria_auto": "SUV",
    "compania_rentadora": "Hertz"
}
```

### Pruebas

Archivo `tests/test_new_components_api.py` cubre:
1. Creación de cada modelo vía API (201 esperado).
2. Asociación correcta a `Venta`.
3. Presencia de las colecciones en el detalle de `Venta`.

### Próximos Pasos Recomendados

1. Validaciones específicas (fechas coherentes retiro/devolución, cálculo automático `dias_total`).
2. Índices DB (e.g. `tipo_servicio`, `fecha_evento`, combinados para filtros frecuentes).
3. Permisos granulares por tipo de componente.
4. Esquema validado para `PaqueteAereo.resumen_componentes` (pydantic / JSON Schema).
5. KPI/Margen por componente (análisis de rentabilidad). 
6. Reglas de propagación (al eliminar `Venta`, reporte agregado en auditoría previa).

## Notas de migración y refactor

**Septiembre 2025:**
- Se aceptó la migración `0016` generada por Django debido a un cambio en el import path del validador de campos de catálogos tras modularización progresiva (`core/models_catalogos.py`).
- La decisión se tomó para mantener la modularidad y evitar revertir la separación de modelos, ya que el cambio no afecta el schema real sino la referencia interna del validador.
- Se recomienda documentar cualquier migración futura causada por cambios en paths de import o validadores personalizados.
- El middleware de seguridad fue ajustado para generar el nonce CSP antes de la vista y propagarlo a templates, asegurando coincidencia entre header y atributo `nonce` en scripts.

---

### Comando de Importación de Pasajeros

Se ha añadido un comando de gestión para facilitar la carga masiva de pasajeros desde un archivo Excel.

*   **Comando:** `python manage.py importar_pasajeros "C:\ruta\completa\a\tu\archivo.xlsx"`
*   **Ubicación del script:** `personas/management/commands/importar_pasajeros.py`

**Formato del Archivo Excel:**

El comando espera un archivo `.xlsx` con las siguientes columnas obligatorias:
*   `Apellido`
*   `Nombre`
*   `Numero de Documento`

**Funcionamiento:**

*   El comando lee cada fila del archivo.
*   Utiliza el `Numero de Documento` como identificador único.
*   Si un pasajero con ese número de documento ya existe, actualiza su nombre y apellido.
*   Si no existe, crea un nuevo registro de pasajero.
*   Informa en la consola el resultado de cada fila (creado, actualizado, omitido por datos faltantes o error).

---

## APIs REST para Frontend

TravelHub expone **26+ endpoints REST** que replican todas las funcionalidades del admin de Django para consumo del frontend.

**📋 Documentación completa:** Ver [FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md)

### Funcionalidades Implementadas

#### Alta Prioridad ✅
1. **Dashboard de Métricas** - `/api/dashboard/metricas/` y `/api/dashboard/alertas/`
2. **Liquidaciones a Proveedores** - `/api/liquidaciones/` (CRUD + acciones)
3. **Generación de Vouchers** - `/api/ventas/{id}/generar-voucher/`

#### Prioridad Media ✅
4. **Auditoría y Trazabilidad** - `/api/auditoria/venta/{id}/` y `/api/audit-logs/`
5. **Gestión de Pasaportes OCR** - `/api/pasaportes/` (CRUD + verificación + crear cliente)
6. **Gestión de Boletos** - `/api/boletos/sin-venta/`, reintentar parseo, crear venta automática

#### Baja Prioridad ✅
7. **Reportes Contables** - Libro diario, balance, validación, exportación Excel
8. **Comunicaciones con Proveedores** - `/api/comunicaciones/` (inbox, categorías)

**Resumen de implementación:** Ver [RESUMEN_IMPLEMENTACION_FRONTEND_API.md](RESUMEN_IMPLEMENTACION_FRONTEND_API.md)

### Mejoras de Calidad Implementadas ✅

1. **Tests Unitarios** - 15+ tests para endpoints críticos
2. **Documentación Swagger/OpenAPI** - Disponible en `/api/docs/`
3. **Rate Limiting Granular** - Throttling por tipo de operación
4. **Sistema de Caché** - Opcional con Redis para mejor rendimiento

**Detalles completos:** Ver [MEJORAS_IMPLEMENTADAS.md](MEJORAS_IMPLEMENTADAS.md)

---

## Sistema de Notificaciones Multicanal (Email + WhatsApp)

TravelHub incluye un sistema automático de notificaciones multicanal que se activa en eventos clave del ciclo de vida de las ventas.

**📋 Documentación completa:** Ver [NOTIFICACIONES.md](NOTIFICACIONES.md) para configuración detallada de WhatsApp/Twilio.

### Canales Soportados
- 📧 **Email** (Gmail SMTP) - Plantillas HTML profesionales
- 📱 **WhatsApp** (Twilio API) - Mensajes formateados (opcional)

### Emails Automáticos

El sistema envía automáticamente los siguientes tipos de email:

1. **Confirmación de Venta Creada**
   - Se envía cuando se crea una nueva venta con cliente asignado
   - Incluye: localizador, fecha, total y estado

2. **Notificación de Cambio de Estado**
   - Se envía cuando cambia el estado de una venta
   - Muestra el estado anterior y el nuevo estado

3. **Confirmación de Pago Recibido**
   - Se envía automáticamente al registrar un pago confirmado
   - Incluye: monto pagado, método de pago y saldo restante

### Recordatorios de Pago

Para enviar recordatorios de pago a ventas pendientes, usa el comando:

```bash
python manage.py enviar_recordatorios_pago
```

**Opciones:**
- `--dias=N`: Envía recordatorios a ventas sin actualizar en N días (default: 3)
- `--dry-run`: Simula el envío sin enviar emails reales

**Ejemplos:**
```bash
# Enviar recordatorios a ventas sin actualizar en 7 días
python manage.py enviar_recordatorios_pago --dias=7

# Simular envío sin enviar emails
python manage.py enviar_recordatorios_pago --dry-run
```

### Configuración de Email

Por defecto, el sistema usa `console.EmailBackend` (emails se muestran en consola).

Para producción, configura en `settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu_email@gmail.com'
EMAIL_HOST_PASSWORD = 'tu_password'
DEFAULT_FROM_EMAIL = 'TravelHub <noreply@travelhub.com>'
```

### Automatización con Cron

Para enviar recordatorios automáticamente, configura un cron job:

```bash
# Enviar recordatorios diariamente a las 9 AM
0 9 * * * cd /ruta/proyecto && /ruta/venv/bin/python manage.py enviar_recordatorios_pago --dias=3
```

```
```