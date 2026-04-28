# 🏢 Arquitectura del Módulo Financiero e IA (TravelHub v3.0)

Este documento detalla el diseño técnico, el flujo de datos y los mecanismos de resiliencia del motor de **Conciliación Inteligente y Auditoría Forense** de TravelHub.

---

## 🏗️ 1. Visión General del Ecosistema (Stack TALL + AI)

El módulo financiero de TravelHub opera como un **Monolito Majestuoso** que combina la simplicidad de Django con la reactividad de las aplicaciones modernas:

*   **Frontend (HTMX + Alpine.js):** Proporciona una interfaz fluida libre de JSON APIs complejas. HTMX orquesta la telemetría en tiempo real (polling) y las acciones de auditoría de un solo clic.
*   **Backend Core (Django 4.2+):** Actúa como el orquestador de reglas de negocio, persistencia multitenant y seguridad fiscal.
*   **Worker Engine (Celery + Redis):** Gestiona las tareas de larga duración (IA y PDF) para mantener el hilo principal del servidor siempre disponible.
*   **Cerebro Financiero (Gemini Pro + Pydantic):** Transforma datos no estructurados de proveedores (PDF/Excel) en hallazgos contables determinísticos mediante razonamiento de lenguaje natural.

---

## 🚦 2. Mapa de Carriles (Colas de Celery)

Hemos diseñado una arquitectura de colas segmentada para evitar que tareas pesadas bloqueen notificaciones críticas:

| Cola | Prioridad | Ejemplo de Tareas | SLA Esperado |
| :--- | :--- | :--- | :--- |
| `ia_fast` | ⚡ ALTA | Análisis de tickets PNR, validación rápida de esquemas. | < 5 segundos |
| `ia_heavy` | 🧠 MEDIA | Conciliación masiva de reportes BSP/KIU (5k+ registros). | 30s - 3min |
| `notifications` | 📧 MEDIA | Envío de reportes PDF por email, notificaciones WhatsApp/Telegram. | < 10 segundos |
| `default` | 🐢 BAJA | Sincronización de catálogos, cálculos estadísticos históricos. | N/A |

---

## 🔄 3. Flujo de Conciliación Inteligente (El Viaje del Dato)

El proceso de conciliación sigue un ciclo de vida de **4 fases críticas**:

1.  **Ingestión Reactiva (HTMX):** El usuario sube el reporte. HTMX dispara un POST asíncrono y reemplaza el formulario por un monitor de progreso animado que hace polling al `task_id`.
2.  **Cruce Híbrido (IA + Regex):**
    *   Primero, un motor Regex/Pandas intenta el cruce determinístico por número de boleto.
    *   Segundo, Gemini Pro analiza las "zonas grises" (diferencias de impuestos, fees no reportados) y genera un **Razonamiento Auditor** en lenguaje natural.
3.  **Auditoría Forense (Human-in-the-Loop):** El usuario aterriza en el Dashboard de Resultados. Puede ver los KPIs globales y aprobar ajustes contables individuales con un solo clic.
4.  **Cierre Documental (PDF & Email):** Tras la auditoría, el sistema genera un PDF enriquecido en memoria (WeasyPrint) y lo envía automáticamente a la gerencia por email.

---

## 🛡️ 4. Mecanismos de Resiliencia (Hardening)

Para garantizar la estabilidad en un entorno SaaS exigente, implementamos estas "Bolsas de Aire" técnicas:

### 🧺 La Mochila y el Almacenamiento Temporal
Nunca guardamos archivos binarios pesados en la DB principal. Utilizamos `FileSystemStorage` temporal o **Telegram Storage** para evitar el crecimiento excesivo de la base de datos (Regla de la Mochila).

### 🛣️ Asistencia de Carril (`safe_delay`)
Utilizamos un helper `safe_delay` que envuelve las llamadas a `.delay()` de Celery. Si el broker (Redis) está caído, el sistema no lanza un Error 500, sino que registra el fallo en el log y alerta al usuario de forma elegante.

### 🆔 Idempotencia v2.0
Cada acción financiera (Asiento, Factura, Comisión) genera un **Token de Idempotencia** único. Esto evita que un doble clic accidental o un reintento de Celery genere duplicidad en los libros contables.

### 🗑️ Soft Deletes y Auditoría
Todos los movimientos financieros usan `SafeDeleteModel`. Nada se borra físicamente. Esto permite al soporte técnico hacer "Rollbacks Manuales" en caso de errores de auditoría humana.

### 🔒 Blind Indexes
Para búsquedas rápidas de boletos/pasaportes cifrados, utilizamos un índice ciego (hash) que permite buscar sin desencriptar los datos sensibles en la base de datos.

---

> **Nota para Desarrolladores:** El estándar estético del módulo es "Emerald Dark". Si añades una nueva vista, asegúrate de heredar de `base_modern.html` y mantener el uso de variables CSS dinámicas para el branding multi-tenant.
