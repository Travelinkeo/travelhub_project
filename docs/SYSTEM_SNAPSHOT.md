# System Snapshot for AI Collaborators 🤖

**Fecha:** 1 de Mayo, 2026
**Estado:** Fase de Estabilización SaaS Completada.

Este documento sirve como "memoria de largo plazo" para que cualquier IA que retome este proyecto pueda entender las decisiones críticas y el estado actual sin alucinaciones.

## 1. Multi-tenancy (Eje Central)
El sistema utiliza una arquitectura **Shared Database, Isolated Rows**.
- **Identificador:** `agencia_id` en casi todos los modelos vía `AgenciaMixin`.
- **Inyección de Contexto:** El `ThreadLocalContextMiddleware` captura la agencia del usuario logueado y la hace disponible globalmente en el hilo de ejecución.
- **Seguridad:** Los QuerySets en el admin y vistas están filtrados automáticamente por `agencia`.

## 2. Flujo de Onboarding & Pagos
- **Entry Point:** `/onboarding/` (`SaaSOnboardingView`).
- **Integración:** Stripe Checkout.
- **Workflow:** 
    1. Usuario elige plan -> Redirige a Stripe.
    2. Stripe Webhook (`checkout.session.completed`) -> `StripeService.handle_webhook()`.
    3. `_provision_new_agency()`: Crea `Agencia`, `User`, `UsuarioAgencia` (Admin) y dispara `NotificationService.enviar_bienvenida_agencia()`.
- **Trial:** El plan `FREE` activa un trial de 30 días sin tarjeta.

## 3. Inteligencia Artificial (Marketing & Automatización)
- **Servicios:** Centralizados en `core/services/marketing_service.py` y `core/services/ai_engine.py`.
- **Vertex AI:** Configurado para **Imagen 3** en `GenerateAIImageView`. Requiere `GCP_PROJECT_ID`.
- **Gemini Pro:** Usado para copywriting y análisis de KPIs en el Dashboard del CEO.
- **Ticket Parser:** Ubicado en `core/services/parsers/`. Utiliza una cadena de responsabilidad: `Normalization -> AI/Regex Extraction -> Persistence`.

## 4. Estructura de Frontend
- **Framework:** Django Templates + TailwindCSS.
- **Interactividad:** HTMX para carga asíncrona de componentes (ej. Consejos de IA) y Alpine.js para lógica de UI (tabs, modales, formularios).
- **Admin:** Basado en el tema **Unfold**, altamente personalizado en `settings.py`.

## 5. Próximos Desafíos Técnicos
- **Impersonation:** Falta completar la lógica segura para que el SuperAdmin entre en sesiones de otras agencias.
- **WhatsApp Automation:** El servicio `whatsapp_service.py` está listo pero requiere vinculación de instancias por cada agencia nueva.
- **Escalabilidad de Parser:** Migrar el parser de Sabre totalmente a LLM (Gemini 1.5 Flash) para mayor precisión.

## ⚠️ NOTA PARA LA IA:
Antes de modificar modelos, verifica siempre `AgenciaMixin`. Si un nuevo modelo requiere aislamiento por agencia, **DEBE** heredar de este mixin. No almacenes secretos en el código, usa el `.env`.
