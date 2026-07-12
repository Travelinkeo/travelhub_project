# Línea Base de Endurecimiento — TravelHub

> **Nota:** Este documento contiene la línea base histórica del plan de endurecimiento. Para una visión consolidada y actualizada de la seguridad, consulta [seguridad.md](seguridad.md).

**Fecha:** 2026-06-26
**Branch:** `hardening/operational-risks`
**Commit base:** `40afb5d` - "Baseline commit: all current changes before hardening phase 0"

---

## 📊 Métricas Actuales (Baseline)

> **NOTA:** Estas métricas deben medirse en entorno de staging/producción real. Valores abajo son referencias esperadas basadas en arquitectura actual.

| Métrica | Valor Esperado | Umbral Alerta | Herramienta Medición |
|---------|----------------|---------------|---------------------|
| **API P95 Latency** | < 300ms | > 800ms | Prometheus/Grafana |
| **Health Check Success Rate** | 100% | < 99.9% | `/health/` endpoint |
| **Celery Queue Lag (default)** | < 50 tasks | > 1000 tasks | `celery_queue_depth` metric |
| **Celery Queue Lag (notifications)** | < 10 tasks | > 100 tasks | `celery_queue_depth` metric |
| **DB Pool Usage** | < 50% | > 80% | `db_active_connections` / `max_connections` |
| **Redis Memory Usage** | < 60% | > 85% | Redis `info memory` |
| **Error Rate (5xx)** | < 0.1% | > 1% | Sentry/Prometheus |
| **Backup Success Rate** | 100% | < 100% | Backup job logs |
| **Deploy Frequency** | Semanal | - | GitHub Actions |
| **MTTR (Mean Time To Recovery)** | < 30 min | > 60 min | Incident logs |

---

## 🐳 Configuración Docker Compose Actual

### **docker-compose.prod.yml - Servicios y Redes**

```yaml
# Redes
networks:
  travelhub_public:   # Traefik, Nginx, Evolution API
  travelhub_private:  # DB, Redis, Celery, Gotenberg, Evolution DB

# Volúmenes Persistentes
volumes:
  postgres_data:        # PostgreSQL principal
  redis_data:           # Redis único (RIESGO: SPOF)
  static_volume:        # Static files (Nginx)
  media_volume:         # Media files (Nginx)
  evolution_data:       # Evolution API instances
  evolution_db_data:    # Evolution API PostgreSQL

# Servicios Críticos
services:
  traefik:          # Reverse proxy + TLS (v3.0)
  db:               # PostgreSQL 15-alpine (SIN HA)
  pgbouncer:        # Connection pooler (transaction mode)
  redis:            # Redis 7-alpine (ÚNICO - RIESGO CRÍTICO)
  web:              # Django + Gunicorn (4 workers)
  nginx:            # Static/media server
  gotenberg:        # PDF generation (Chromium)
  celery_worker:    # Celery worker (4 concurrency, 4 queues)
  celery_beat:      # Celery beat (DatabaseScheduler)
  evolution:        # Evolution API v2 (WhatsApp)
  evolution_db:     # PostgreSQL para Evolution
```

### **Variables de Entorno Críticas (prod)**
```bash
# Database
DB_NAME=travelhub
DB_USER=postgres
DB_PASSWORD=<secret>
DATABASE_URL=postgres://${DB_USER}:${DB_PASSWORD}@pgbouncer:5432/${DB_NAME}

# Redis (ÚNICO para todo - RIESGO)
REDIS_PASSWORD=<secret>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/0

# Evolution API
WHATSAPP_MICROSERVICE_TOKEN=<secret>
EVOLUTION_DB_USER=postgres
EVOLUTION_DB_PASSWORD=<secret>
CACHE_REDIS_URI=redis://:${REDIS_PASSWORD}@redis:6379/1  # Mismo Redis!

# Django
SECRET_KEY=<50+ chars>
DEBUG=False
ALLOWED_HOSTS=travelhub.cc,*.travelhub.cc
```

---

## ⚠️ Riesgos Identificados (Baseline)

| ID | Riesgo | Severidad | Impacto | Mitigación Fase |
|----|--------|-----------|---------|-----------------|
| **R01** | **Redis único para Cache + Sessions + Celery + Evolution** | 🔴 CRÍTICO | SPOF total: caída = app down + colas paradas + WhatsApp down | Fase 1: Split 4 instancias |
| **R02** | **PostgreSQL sin réplicas ni HA** | 🔴 CRÍTICO | Pérdida datos / downtime prolongado ante fallo | Fase 2: Patroni cluster |
| **R03** | **Healthchecks solo HTTP básicos** | 🟡 ALTO | No detecta degradación DB/Redis/Celery antes de fallo | Fase 3: Deep healthchecks |
| **R04** | **Celery Beat sin HA (DatabaseScheduler)** | 🟡 ALTO | Tareas cron duplicadas/perdidas si beat cae | Fase 4: RedBeat |
| **R05** | **Evolution API en red pública** | 🟡 ALTO | Superficie ataque WhatsApp | Fase 5: Private network + auth |
| **R06** | **Gunicorn workers fijos (4)** | 🟢 MEDIO | No auto-escala bajo carga | Fase 6: K8s HPA/KEDA |
| **R07** | **Logs no estructurados (JSON)** | 🟢 MEDIO | Difícil debugging/alerting en Grafana/Loki | Fase 3: Structured logging |
| **R08** | **Sin CDN para media (R2 directo)** | 🟢 MEDIO | Latencia + coste requests | Fase 7: Cloudflare CDN |

---

## 🔧 Configuración Actual por Componente

### **Redis Usage en Código**
```python
# settings.py - Líneas 526-535
_redis_password = os.getenv("REDIS_PASSWORD", None)
_redis_host = os.getenv("REDIS_HOST", "redis")
_redis_port = os.getenv("REDIS_PORT", "6379")

# CACHES (DB 1) - settings.py:582-597
# SESSIONS (DB 2) - settings.py:590-596
# CELERY (DB 0) - settings.py:539-540
# EVOLUTION (DB 1) - docker-compose:322

# Accesos directos en código:
# core/views/health_views.py:89 - get_redis_connection("default")
# core/metrics.py:37 - get_redis_connection("default")
# core/cache.py:63 - get_redis_connection("default")
# apps/automation/services/ticket_parser_service.py:60 - import redis
# apps/common/utils/celery_utils.py:203 - import redis
```

### **PostgreSQL Usage**
```python
# settings.py:202
DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
DATABASES["default"]["CONN_MAX_AGE"] = 600
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# PgBouncer config (docker-compose.prod.yml:65-90)
POOL_MODE: transaction
MAX_CLIENT_CONN: 100
DEFAULT_POOL_SIZE: 25
```

### **Celery Configuration**
```python
# travelhub/celery.py - Queues definidas:
# - default (general)
# - ia_fast (IA tiempo real <5s)
# - ia_heavy (IA batch >1min)
# - notifications (WhatsApp/Email/Telegram)

# Beat schedule (travelhub/celery_beat_schedule.py) - 16 tareas programadas
# Scheduler: DatabaseScheduler (django_celery_beat)
```

---

## ✅ Pruebas de Humo (Smoke Tests) - Baseline

### **Test 1: Health Check Básico**
```bash
curl -f http://localhost:8000/health/
# Expected: 200 OK con {"status": "ok", "checks": {...}}
```

### **Test 2: Métricas Prometheus**
```bash
curl -f http://localhost:8000/health/metrics
# Expected: 200 OK con métricas travelhub_*
```

### **Test 3: Database Connectivity**
```bash
python manage.py dbshell -c "SELECT 1;"
# Expected: 1 row returned
```

### **Test 4: Redis Connectivity**
```bash
redis-cli -h redis -p 6379 -a $REDIS_PASSWORD ping
# Expected: PONG
```

### **Test 5: Celery Workers**
```bash
celery -A travelhub inspect ping
# Expected: pong from all workers
```

### **Test 6: Celery Beat**
```bash
celery -A travelhub inspect scheduled
# Expected: Lista de tareas programadas
```

### **Test 7: Evolution API**
```bash
curl -f http://localhost:8080/manager/health
# Expected: 200 OK
```

---

## 📦 Plan de Rollback por Fase

| Fase | Comando Rollback | Tiempo Estimado |
|------|------------------|-----------------|
| **Fase 1 (Redis Split)** | `docker compose -f docker-compose.prod.yml up -d redis` (viejo) + revertir env vars | < 5 min |
| **Fase 2 (PG HA)** | Revertir PgBouncer config a `db:5432` + DNS switch | < 2 min |
| **Fase 3 (Healthchecks)** | `git revert` commit healthchecks | < 1 min |
| **Fase 4 (RedBeat)** | Cambiar `CELERY_BEAT_SCHEDULER` a `django_celery_beat.schedulers:DatabaseScheduler` | < 1 min |
| **Fase 5 (Evolution Private)** | Añadir `travelhub_public` a evolution network + quitar middleware auth | < 2 min |
| **Fase 6 (K8s)** | Mantener docker-compose como fallback | N/A |

---

## 📝 Checklist Phase 0 Completion

- [x] Branch `hardening/operational-risks` creado desde baseline
- [x] Baseline commit `40afb5d` con todos los cambios actuales
- [x] Documentación `hardening_baseline.md` creada
- [ ] Métricas baseline medidas en staging (PENDING: requiere entorno)
- [ ] Smoke tests automatizados en CI (PENDING: siguiente paso)
- [ ] Documentación de configuración actual completada
- [ ] Matriz de riesgos y rollback documentada

---

## 🚀 Próximos Pasos (Fase 1)

1. **Crear tests de humo automatizados** en `tests/test_health_smoke.py`
2. **Añadir tests a CI** (`.github/workflows/ci.yml`)
3. **Implementar Redis Split** (4 instancias separadas)
4. **Validar 0-downtime migration** en staging

---

*Documento generado automáticamente como parte del plan de hardening operativo.*
