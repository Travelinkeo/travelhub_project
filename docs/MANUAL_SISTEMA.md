# 📘 MANUAL MAESTRO DEL SISTEMA — TravelHub SaaS B2B
Este documento explica la arquitectura, el funcionamiento de negocio y la guía de desarrollo del sistema de forma que sea comprensible tanto para directores de negocio y fundadores como para ingenieros de software.

---

## 🏢 1. La Arquitectura SaaS y Multi-Tenancy (Explicación para Todos)

### Explicación Sencilla (No Programadores)
Imagina que **TravelHub** es un gran edificio de apartamentos. En lugar de construir un edificio para cada familia (lo cual sería carísimo), construimos un solo edificio grande y le damos a cada familia su propio apartamento con su llave. 
* El edificio entero es el **Servidor y la Base de Datos**.
* Cada apartamento es una **Agencia de Viajes** (*Tenant*).
* Los residentes de un apartamento (vendedores, contadores) solo pueden ver y modificar las cosas que están dentro de su apartamento. Es físicamente imposible que un residente del Apartamento A abra el clóset del Apartamento B. Esto se llama **Aislamiento Multi-Tenant**.

### Explicación Técnica (Programadores)
El aislamiento multi-tenant se logra en tres capas de seguridad defensiva:
1. **Middleware de Enrutamiento (`MultiTenantDomainMiddleware`)**: Identifica la agencia actual leyendo el host de la petición HTTP (ej. `agencia1.travelhub.cc` o un dominio personalizado como `viajesworld.com`).
2. **Contexto Seguro (`ThreadLocalContextMiddleware`)**: Almacena la agencia identificada en una variable de contexto asíncrona segura (`contextvars`). A diferencia de las variables globales comunes, `contextvars` garantiza que los datos de la agencia no se grucen entre peticiones web concurrentes en servidores multihilo como Gunicorn.
3. **Row-Level Security (RLS) en la Base de Datos**: A nivel de PostgreSQL, cada tabla crítica de negocio tiene políticas de seguridad que filtran las filas de forma automática según la agencia activa en la conexión SQL (`SET LOCAL app.current_agencia_id`). Si el backend intenta consultar datos sin filtrar, PostgreSQL rechaza la petición si el ID de agencia no coincide.

---

## 🧠 2. El Parser Híbrido de Boletos (IA + Regex)

### Explicación Sencilla (No Programadores)
Cuando una agencia de viajes recibe un recibo de boleto emitido por sistemas globales (GDS como Sabre o Amadeus), este viene en formatos de texto muy enredados, correos o PDFs difíciles de leer. Tradicionalmente, un empleado tiene que copiar y pegar cada campo a mano (nombre del pasajero, ruta, costo, impuestos, etc.).
**TravelHub** hace esto automáticamente:
1. **Lector Rápido (Regex)**: Primero, el sistema tiene plantillas predefinidas para leer el texto en milisegundos.
2. **Asistente Inteligente (Gemini AI)**: Si el boleto tiene un formato nuevo o alterado que el lector rápido no comprende, el sistema le envía el texto a la Inteligencia Artificial de Google (Gemini) de forma estructurada para que actúe como un humano ultra-veloz descifrando el contenido.
3. **Caché Inteligente**: Para ahorrar dinero en llamadas de Inteligencia Artificial, si el sistema detecta que el texto de un boleto ya fue leído anteriormente, recupera el resultado de su memoria interna (*Redis*) al instante y a costo cero.

### Explicación Técnica (Programadores)
El flujo en `TicketParserService` opera bajo el patrón de **Fast-First con Fallback Resiliente**:
1. **Ingestión**: El archivo (PDF, TXT, EML) es procesado y extraído a texto plano en UTF-8.
2. **Detección Local**: Se ejecuta `extract_data_from_text` que corre analizadores de expresiones regulares estructurados por GDS. Si se cumple con el contrato de calidad mínimo (PNR válido, nombre de pasajero, y al menos un segmento de vuelo estructurado con hora y fecha), se omite la llamada a la API de IA para optimizar latencia y costos.
3. **Fallback a LLM (Gemini Pro/Flash)**: Si el motor local no califica los datos como confiables, se invoca `UniversalAIParser` utilizando esquemas de salida estructurada (*Structured Outputs* de Gemini con Pydantic) para garantizar que la respuesta del modelo mapee exactamente al esquema del ERP.
4. **Ingestión Atómica de Grupos (Multi-Pax)**: Si el boleto contiene más de un pasajero en la misma reserva (grupo familiar), el servicio realiza un *Split Atómico* usando la tabla `BoletoImportadoTransito`. Divide el boleto en registros individuales por pasajero, vinculándolos a una venta maestra en una transacción de base de datos segura para evitar escrituras parciales.

---

## 🚦 3. Los Candados de Concurrencia (Advisory Locks)

### Explicación Sencilla (No Programadores)
Imagínate una panadería muy concurrida donde los clientes toman un número de un dispensador de papel para ser atendidos. Si dos clientes meten la mano al mismo tiempo y el dispensador no está bien diseñado, ambos podrían llevarse el boleto número 5. En facturación contable y fiscal esto es un desastre: no puede haber dos facturas con el mismo número legal.
**TravelHub** tiene un "semáforo digital" que garantiza que, si dos transacciones ocurren en el mismo microsegundo, una de ellas espere una fracción de segundo a que la otra tome su número correlativo y se retire, garantizando que los números correlativos de facturas y asientos contables sean únicos y perfectamente ordenados.

### Explicación Técnica (Programadores)
Para resolver condiciones de carrera sin bloquear tablas enteras de la base de datos (lo cual congelaría el sistema en picos de tráfico), se utiliza **Advisory Locks Transaccionales de PostgreSQL (`pg_advisory_xact_lock`)**:
1. Se calcula un hash SHA-256 único basado en el prefijo correlativo diario (ej: `F-20260615` o `AS-20260615`).
2. Se adquiere un bloqueo numérico exclusivo para ese prefijo en la base de datos mediante SQL.
3. El proceso lee el conteo de registros actuales y asigna el siguiente número correlativo (`count + 1`) de forma segura.
4. Al finalizar la transacción de base de datos, el bloqueo se libera automáticamente. Esto permite que otros hilos operen en paralelo sobre diferentes días o diferentes agencias sin interferencia.

---

## 🕵️‍♂️ 4. Reconciliación Contable en Segundo Plano

### Explicación Sencilla (No Programadores)
Cuando compras un boleto de avión, ocurren varias cosas tras bambalinas: se crea la venta en el sistema, se emite una factura fiscal para el cliente, se registra el pago y se genera el asiento en la contabilidad. ¿Qué pasa si el sistema de contabilidad o el servidor de internet se cae a la mitad de este proceso? La venta queda registrada pero la contabilidad se "descuadra" sin que nadie se dé cuenta.
**TravelHub** tiene un **Auditor Digital** que corre automáticamente en segundo plano todas las noches. Revisa factura por factura y pago por pago buscando discrepancias: si encuentra alguna factura o pago sin su respectivo asiento contable, el auditor los repara y cuadra la contabilidad automáticamente de forma silenciosa.

### Explicación Técnica (Programadores)
El servicio `ContabilidadReconciliationService.audit_and_reconcile()` busca:
1. Facturas en estado emitido, pagado o parcial que no cuenten con una relación `asiento_contable_factura` ni un asiento contable con `referencia_documento = factura.numero_factura`.
2. Pagos de venta (`PagoVenta`) confirmados que no tengan un asiento contable referenciado como `PAGO-<id>`.
3. Para cada discrepancia encontrada, se invoca de forma segura y atómica el creador contable correspondiente, asociándolo a la transacción original. Esta tarea se ejecuta de forma asíncrona a través de Celery Beat a la 1:00 AM todos los días.

---

## ⚙️ 5. Guía de Inicio Rápido para Desarrolladores

### Requisitos Previos
* Docker y Docker Compose instalados.
* Git.

### Setup del Entorno de Desarrollo

1. **Clonar el proyecto y acceder al directorio**:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd travelhub_project
   ```

2. **Crear archivo de variables de entorno**:
   Copia el archivo de ejemplo a un archivo `.env` en la raíz del proyecto y edita las claves correspondientes (Stripe, Gemini, base de datos):
   ```bash
   cp .env.example .env
   ```

3. **Iniciar los servicios locales con Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```
   Esto levantará el servidor web Django (`travelhub_web`), la base de datos PostgreSQL (`travelhub_db`), el broker Redis (`travelhub_broker`), los workers de Celery, Traefik como proxy inverso y Gotenberg para la generación de PDFs.

4. **Aplicar migraciones de base de datos**:
   ```bash
   docker exec -it travelhub_web python manage.py migrate
   ```

5. **Cargar catálogos iniciales (países, ciudades, aerolíneas, monedas)**:
   ```bash
   docker exec -it travelhub_web python manage.py load_catalogs --upsert
   ```

6. **Crear un superusuario para acceder al panel de administración**:
   ```bash
   docker exec -it travelhub_web python manage.py createsuperuser
   ```

7. **Ejecutar la suite de pruebas unitarias**:
   ```bash
   docker exec -it travelhub_web pytest --reuse-db
   ```
