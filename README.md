# TravelHub - CRM/ERP/CMS para Agencia de Viajes

TravelHub es una aplicación web integral diseñada para agencias de viajes, combinando funcionalidades de CRM (Customer Relationship Management), ERP (Enterprise Resource Planning) y CMS (Content Management System).

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

## Detalles Técnicos

* **Backend:** Django 5.x, Django REST Framework.
* **Base de Datos:** SQLite (desarrollo), preparada para PostgreSQL (producción).
* **Frontend (inicial):** Django Templates. PWA básica.
* **Parseo de Boletos:** PyMuPDF, expresiones regulares.
* **Configuración:** Español, Zona Horaria América/Caracas.

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

5.  **Realizar migraciones de la base de datos:**
    ```bash
    python manage.py makemigrations core
    python manage.py migrate
    ```

6.  **Crear un superusuario (administrador):**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Cargar datos iniciales (fixtures):**
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

