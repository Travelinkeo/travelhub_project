# 🚦 Semáforo Migratorio (Migration Checker)

El módulo de **Semáforo Migratorio** automatiza la validación de requisitos de ingreso (visas, pasaporte, vacunas) para los pasajeros, utilizando una combinación de reglas locales, caché y validación por IA (Gemini).

## 📋 Características Principales

1.  **Validación Automática:** Se ejecuta al importar boletos que contengan datos de vuelos normalizados.
2.  **Validación Manual:** Desde el Admin de Django (Acciones masivas) o API.
3.  **Consulta Rápida (Telegram):** Comando `/check_visa` para consultas ad-hoc.
4.  **Backend Híbrido:**
    *   **Caché (Redis):** Respuestas instantáneas para rutas comunes.
    *   **Reglas Locales:** Base de datos interna para casos frecuentes (ej: Vzla -> España).
    *   **IA (Gemini):** Respaldo para casos complejos o rutas inusuales.

## 🛠 Arquitectura

### Modelos
*   **`MigrationCheck` (`core`):** Almacena el resultado de cada validación.
*   **`Pasajero` (`personas`):** Se extendió con campos:
    *   `fecha_emision_documento`
    *   `tiene_fiebre_amarilla`
    *   `fecha_vacuna_fiebre_amarilla`

### Servicios
*   **`MigrationCheckerService` (`core.services`):** Orquestador principal. Lógica de pasaporte y caché.
*   **`GeminiMigrationValidator` (`core.services`):** Cliente de IA para generar consultas y parsear respuestas JSON.

## 🚀 Uso

### Telegram Bot
Envía el comando:
`/check_visa [Nacionalidad] [Destino]`
Ejemplo: `/check_visa VEN ESP`

### Django Admin
1.  Ir a **Ventas**.
2.  Seleccionar ventas.
3.  Acción: **🚦 Validar Requisitos Migratorios**.
4.  Los resultados aparecen en la pestaña (Inline) de cada Venta.

### API
*   `POST /api/migration/check/`
*   `GET /api/migration/checks/{pasajero_id}/`

## ⚙️ Configuración

Variables de entorno requeridas:
*   `GEMINI_API_KEY`: Para el validador por IA.
*   `REDIS_URL`: Para el caché (opcional, fallback a memoria).

## 🤖 Automatización
La validación se dispara automáticamente vía **Signals** (`core.signals`) cuando se crea un `BoletoImportado` que contiene información de vuelos en la estructura `normalized`.
