# TravelHub SaaS Platform 🚀

**Sistema de Gestión Integral (ERP/SaaS) para Agencias de Viajes con Inteligencia Artificial.**

TravelHub es una plataforma B2B multi-tenant diseñada para automatizar la operación completa de agencias de viajes. Combina Django con Google Gemini para resolver la fricción operativa, financiera y de marketing.

---

## 🏛️ Arquitectura y Estado Actual (Julio 2026)

### 1. Multi-tenant SaaS & Onboarding
- **Aislamiento de Datos:** `AgenciaMixin` + `AgenciaManager` + `ThreadLocalContextMiddleware`. Cada agencia opera en su propio contexto.
- **Onboarding Autónomo:** Registro self-service con Stripe. Planes: Basic, Pro y Enterprise, con Trial gratuito de 30 días.
- **Aprovisionamiento:** Webhook de Stripe activa creación de agencia, admin y límites de uso.

### 2. Automatización & IA
- **Ticket Parser Pro:** Extracción multi-GDS (Sabre, Amadeus, KIU, Copa, Wingo, TK Connect) con motor híbrido Regex + Gemini.
- **AI Copywriter:** Generación de captions para redes sociales.
- **AI Agent:** Asistente conversacional con function calling integrado al ERP.

### 3. Centro de Control (God Mode)
- Dashboard de superadmin con métricas globales, MRR, churn, uso de IA, y logs de actividad.
- Impersonación controlada con auditoría criptográfica y timeout.

### 4. Sistema de Vouchers
- Generación de vouchers PDF por tipo de servicio (hotel, traslado, actividad, auto, seguro) vía Gotenberg.
- 5 variaciones de diseño por agencia.

---

## 📚 Documentación

| Documento | Descripción |
|-----------|-------------|
| [Índice Maestro](docs/INDEX.md) | Mapa central de documentación |
| [Reporte de Arquitectura](docs/reporte_arquitectura_2026.md) | Arquitectura técnica detallada |
| [Manual del Usuario](docs/manual_del_usuario.md) | Guía para usuarios finales |
| [Reglas de Parseo](docs/parsing_rules.md) | Estándares de extracción GDS |
| [Multi-tenancy](docs/multi_tenancy.md) | Aislamiento de datos |
| [Modelo de Negocio](docs/business_model.md) | Planes y precios |
| [Chequeo de Tipos](docs/mypy.md) | Ejecutar mypy localmente |
| [Despliegue](docs/deployment/deployment.md) | Guía WSL2 + Docker + Cloudflare Tunnel |

---

## 🔍 Chequeo de Tipos con mypy

Para ejecutar el verificador de tipos en tu entorno local:

```bash
pip install -r requirements/dev.txt
mypy .
```

Esto usará la configuración definida en `mypy.ini` y el plugin `django-stubs`.

> **Nota:** `mypy.ini` tiene `strict = False` durante la fase de adopción
> gradual del checkeo de tipos. Ver `docs/mypy.md` para el detalle de los
> error codes temporalmentedesactivados y el plan de activación.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| **Backend** | Django 5.2.14, Python 3.13, Django REST Framework |
| **Frontend** | TailwindCSS, HTMX, Alpine.js (SSR) |
| **Base de Datos** | PostgreSQL 16 + Redis 7 |
| **IA** | Google Gemini (genai SDK v1.x) |
| **Async** | Celery 5.5 + Redis broker |
| **PDF** | Gotenberg (HTML → PDF headless) |
| **Billing** | Stripe (suscripciones SaaS) |
| **Comunicaciones** | Evolution API (WhatsApp), Resend (email), Telegram |
| **Infraestructura** | Docker Compose, WSL2, Cloudflare Tunnel |
| **CI/CD** | GitHub Actions: ruff, pytest (77%+ cobertura), bandit, pip-audit |

---

## 🔒 Seguridad

- **CSP:** Content-Security-Policy con nonces rotativos por request
- **Headers:** HSTS, X-Frame-Options: DENY, X-Content-Type-Options, Referrer-Policy
- **Campos Encriptados:** `EncryptedCharField`/`EncryptedTextField` con Fernet (ENCRYPTION_KEY dedicada)
- **Rate Limiting:** Throttling por vista + límites por plan SaaS
- **Fuerza Bruta:** django-axes (5 intentos máx, 1h bloqueo)
- **Auditoría:** AuditLog con encadenamiento criptográfico SHA-256
- **Multi-tenancy:** PostgreSQL Row-Level Security + ORM filtering

---

## 📋 Mejoras Implementadas (Fases 0-6)

### Fase 0: Emergencia de Seguridad
- [x] Agregado `@login_required` a vistas de upload/dissociate
- [x] Verificación HMAC en webhooks de Binance
- [x] Bloqueo de magic links para usuarios inactivos
- [x] Eliminación de tokens hardcodeados
- [x] Script de rotación de credenciales

### Fase 1: Seguridad y Estabilidad
- [x] Corrección de cadena de hash de auditoría
- [x] Cambio de CASCADE a SET_NULL en `AuditLog.venta`
- [x] Índices en 7 campos frecuentemente filtrados
- [x] Timeout y retry en 11 tareas Celery
- [x] Rate limiting en solicitud de magic links
- [x] Validación de MIME type en uploads

### Fase 2: Integridad de Datos
- [x] Fix TOCTOU race en `Venta.localizador` y `Factura.numero_factura`
- [x] Métodos `clean()` en modelos críticos
- [x] `.quantize(Decimal('0.01'))` en todos los cálculos financieros
- [x] Señales de auditoría para `PagoVenta`, `FeeVenta`, `Cliente`, `Proveedor`

### Fase 3: Performance y Seguridad Web
- [x] Optimización N+1 queries con `select_related`/`prefetch_related`
- [x] Idempotencia en tareas Celery críticas
- [x] Sanitización XSS con `bleach` y template filter
- [x] Protección SSRF en proxy de Evolution API

### Fase 4: Deuda Técnica
- [x] Centralización de `get_user_active_agency()` (patrón repetido 39+ veces)
- [x] Cleanup de imports no usados
- [x] Documentación API con `drf-spectacular`
- [x] Estructura mejorada de `settings.py`

### Fase 5: Testing
- [x] Tests unitarios para validaciones de modelos
- [x] Tests de integración para APIs REST
- [x] Tests de seguridad (XSS, SSRF, sanitización)
- [x] Pipeline CI/CD con GitHub Actions

### Fase 6: Documentación y Despliegue
- [x] Documentación técnica actualizada
- [x] Guía de despliegue para producción
- [x] Docker Compose para desarrollo
- [x] Scripts de migración de datos

---

## ⚠️ Reglas del Repo

- **Cero Secretos:** Nunca commitear `.env`, credenciales JSON, o `db.sqlite3`
- **Historial Limpio:** Purga de claves en commits históricos
- **Linting:** `ruff check . && ruff format .` antes de commit
