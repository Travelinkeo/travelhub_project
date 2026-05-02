# TravelHub SaaS Platform 🚀

**Sistema de Gestión Integral (ERP/SaaS) para Agencias de Viajes con Inteligencia Artificial.**

TravelHub es una plataforma B2B multi-tenant diseñada para automatizar la operación completa de agencias de viajes. Combina la potencia de Django con modelos de lenguaje avanzados (Gemini/Vertex AI) para resolver la fricción operativa, financiera y de marketing.

---

## 🏛️ Arquitectura y Estado Actual (Mayo 2026)

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

Si eres un desarrollador o una IA (Claude, ChatGPT, Gemini) colaborando en este proyecto, **tu punto de partida obligatorio** es:

0.  🚩 **[ÍNDICE MAESTRO](docs/INDEX.md)**: El mapa central con acceso a todos los documentos actualizados.

Para consultas específicas:
1.  [🏛️ Reporte de Arquitectura 2026](docs/REPORTE_ARQUITECTURA_2026.md): Documento maestro con diagramas de flujo y arquitectura técnica detallada.
2.  [📖 Libro del Usuario (Frontend)](docs/MANUAL_DEL_USUARIO.md): Guía paso a paso **sin tecnicismos** para usuarios finales y agentes de viajes.
3.  [📜 Reglas de Parseo (GDS)](docs/PARSING_RULES.md): Estándares de extracción y estandarización para Sabre, KIU y Amadeus.
4.  [🏢 Arquitectura Multi-tenant](docs/MULTI_TENANCY.md): Explicación técnica del aislamiento de datos por agencia.
5.  [💰 Modelo de Negocio SaaS](docs/BUSINESS_MODEL.md): Planes, precios y límites de suscripción.

---

## 🛠️ Stack Tecnológico
*   **Backend:** Django 6.x, Python 3.12+.
*   **Frontend:** TailwindCSS, HTMX, Alpine.js (Arquitectura moderna "Low-code" frontend).
*   **Base de Datos:** PostgreSQL (Multi-tenant) + Redis.
*   **IA:** Google Gemini Pro, Vertex AI (Imagen 3), Document AI.
*   **Infraestructura:** Coolify (Deployment), Docker, Celery (Async tasks), Stripe (Billing).

---

## ⚠️ Reglas de Seguridad para el Repo
*   **Cero Secretos:** Nunca hagas commit de archivos `.env`, llaves JSON de GCP o `db.sqlite3`.
*   **Git Saneado:** Se ha realizado una purga de historial para asegurar que no haya claves expuestas en commits antiguos.
