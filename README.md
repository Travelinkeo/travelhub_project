# TravelHub SaaS Platform 🚀

**Sistema de Gestión Integral (ERP/SaaS) para Agencias de Viajes con Inteligencia Artificial.**

TravelHub es una plataforma B2B multi-tenant diseñada para automatizar la operación completa de agencias de viajes. Combina la potencia de Django con modelos de lenguaje avanzados (Gemini/Vertex AI) para resolver la fricción operativa, financiera y de marketing.

---

## 🏛️ Arquitectura y Estado Actual (Abril 2026)

El proyecto ha pasado por una fase de estabilización crítica, consolidando los siguientes pilares:

### 1. Multi-tenant SaaS & Onboarding
*   **Aislamiento de Datos:** Implementado vía `AgenciaMixin` y `ThreadLocalContextMiddleware`. Cada agencia opera en su propio contexto de datos.
*   **Onboarding Autónomo:** Registro self-service integrado con **Stripe**. Soporta planes *Basic*, *Pro* y *Enterprise*, además de un flujo de *Trial* gratuito.
*   **Aprovisionamiento Automático:** El sistema crea la agencia, el administrador y configura límites de uso (cuotas de ventas/usuarios) al detectar el pago mediante Webhooks.

### 2. Automatización & IA (The Invisible Agent)
*   **Ticket Parser Pro:** Extracción de datos de boletos (Sabre, KIU) usando un motor híbrido de Regex + Google Document AI / Gemini.
*   **Marketing Hub IA:** 
    *   **AI Copywriter:** Generación de captions virales con distintos tonos de voz.
    *   **Post Maker:** Generación de imágenes fotorrealistas (Imagen 3 - Vertex AI) para promociones de hoteles.
    *   **Magic Newsletter:** Generador de campañas de email en HTML.

### 3. Centro de Control (God Mode)
*   Dashboard exclusivo para el dueño de la plataforma con métricas globales: MRR estimado, crecimiento de agencias, salud del sistema y logs de actividad de IA a través de todos los tenants.

---

## 📚 Documentación para Colaboradores (Humano/IA)

Si eres una IA (Claude, ChatGPT, etc.) colaborando en este proyecto, lee estos archivos primero:

1.  [🏛️ Arquitectura del Sistema](docs/ARCHITECTURE.md): Detalla el stack, el middleware multi-tenant y el flujo de autenticación.
2.  [🏢 Arquitectura Multi-tenant](docs/MULTI_TENANCY.md): Explicación técnica del aislamiento de datos por agencia.
3.  [💰 Modelo de Negocio SaaS](docs/BUSINESS_MODEL.md): Planes, precios y límites de suscripción.
4.  [📖 Diccionario de Datos](docs/DATA_DICTIONARY.md): Estructura de modelos y reglas de negocio.
5.  [🤖 Guía de IA & Automatización](docs/AI_GUIDE.md): Cómo interactuar con los servicios de Gemini y el Parser.

---

## 🛠️ Stack Tecnológico
*   **Backend:** Django 5.x, Python 3.12.
*   **Frontend:** TailwindCSS, Alpine.js, HTMX (Arquitectura "Low-code" frontend).
*   **Base de Datos:** PostgreSQL (Multi-tenant).
*   **IA:** Google Gemini Pro, Vertex AI (Imagen 3), Document AI.
*   **Infraestructura:** Docker, Celery (Async tasks), Redis, Stripe (Billing).

---

## ⚠️ Reglas de Seguridad para el Repo
*   **Cero Secretos:** Nunca hagas commit de archivos `.env`, llaves JSON de GCP o `db.sqlite3`.
*   **Git Saneado:** Se ha realizado una purga de historial para asegurar que no haya claves expuestas en commits antiguos.
