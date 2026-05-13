# TravelHub - Plan de Acción CTO

## Contexto Actual
- **Prioridad:** Estabilizar el producto
- **Presupuesto:** $0 (usando Resend, sin SendGrid, usando Gemini)
- **Equipo:** 1 persona (autodidacta) + IA
- **Entorno:** Cloudflare Tunnel + WSL2
- **Estado WhatsApp:** Evolution API conectada y funcional (sesión activa)
- **Errores principales:** Cuota de Gemini + Fallos en parseo de boletos

---

## FASE 1: ESTABILIZACIÓN CRÍTICA (Esta semana)

**Objetivo:** Que no explote en producción y tengamos visibilidad de qué falla.

| # | Acción | Detalles | Tiempo Estimado |
|---|--------|----------|-----------------|
| 1.1 | **Activar Sentry** | Configurar Sentry.io (free tier) en `travelhub/settings.py` para capturar errores en producción | 30 min |
| 1.2 | **Mejorar logging de errores** | Añadir logging estructurado en puntos críticos: parseo de emails, llamadas a Gemini, tareas de Celery | 2 horas |
| 1.3 | **Health check básico** | Crear endpoint `/health/` que verifique DB, Redis, Evolution API | 1 hora |
| 1.4 | **Revisar logs actuales** | Analizar `docker logs` para identificar patrones de error específicos | 1 hora |

**Entregables Fase 1:**
- Alertas de error activadas en Sentry/email
- Mapa de errores conocidos documentado
- Sistema de health check funcionando

---

## FASE 2: SEGURIDAD & RENDIMIENTO (Próximas 2 semanas)

**Objetivo:** Proteger datos de clientes y asegurar rendimiento estable.

| # | Acción | Detalles | Tiempo Estimado |
|---|--------|----------|-----------------|
| 2.1 | **Script de verificación de multi-tenancy** | Crear script que verifique que Agencia A no pueda acceder a datos de Agencia B | 4 horas |
| 2.2 | **Optimizar consultas lentas** | Usar Django Debug Toolbar para identificar y optimizar top 5 queries problemáticas | 1 semana |
| 2.3 | **Implementar retry para Gemini** | Añadir backoff exponencial y reintentos en llamadas a Gemini API | 3 horas |
| 2.4 | **Cachear resultados de parsing** | Cachear resultados de Gemini para emails idénticos o similares | 2 horas |

**Entregables Fase 2:**
- Reporte de auditoría de aislamiento de datos
- Mejora medible en tiempo de respuesta de páginas críticas
- Reducción en errores de cuota de Gemini

---

## FASE 3: OPERACIONES & AUTOMATIZACIÓN (Mes 1-2)

**Objetivo:** Reducir carga manual y preparar el sistema para crecer.

| # | Acción | Detalles | Tiempo Estimado |
|---|--------|----------|-----------------|
| 3.1 | **Dashboard de salud del sistema** | Página básica mostrando: colas de Celery, uso de DB, estado de servicios externos | 1 semana |
| 3.2 | **Optimizar frecuencia de IMAP** | Ajustar tareas de Celery para procesar emails en batches inteligentes | 2 horas |
| 3.3 | **Plantillas de onboarding** | Crear checklist/documento para agilizar setup de nuevas agencias | 4 horas |

**Entregables Fase 3:**
- Visibilidad operativa en tiempo real
- Tiempo de setup de nueva agencia reducido
- Menos intervenciones manuales requeridas

---

## FASE 4: TESTS & CONFIANZA (Mes 2-3)

**Objetivo:** Poder hacer cambios con confianza y dormir tranquilo.

| # | Acción | Detalles | Tiempo Estimado |
|---|--------|----------|-----------------|
| 4.1 | **Tests de flujo crítico** | Probar flujo completo: email entrante -> parseo -> creación de venta -> generación de PDF | 1 semana |
| 4.2 | **Tests de multi-tenancy** | Verificar aislamiento entre agencias en operaciones críticas | 1 semana |
| 4.3 | **Documentación técnica** | README actualizado con arquitectura, setup, y procedimientos comunes | 2 semanas |

**Entregables Fase 4:**
- Suite de tests cubriendo flujos principales
- Documentación que reduce dependencia de conocimiento tribal
- Mayor confianza al hacer cambios

---

## RECURSOS GRATUITOS PARA ESTE PLAN

| Necesidad | Solución Gratuita |
|----------|------------------|
| Monitoreo de errores | Sentry.io (Free: 5k errors/mes) |
| Logging estructurado | Python logging estándar + formato JSON |
| Email transaccional | Resend (ya configurado) |
| WhatsApp Business | Evolution API (auto-alojado) |
| Base de datos | PostgreSQL (en Docker/local) |
| Caché | Redis (en Docker/local) |
| CDN/SSL | Cloudflare (ya en uso) |
| Testing | pytest (ya incluido en dev de Django) |

---

## PRÓXIMOS PASOS INMEDIATOS (Hoy)

1. **Activar Sentry:**
   ```python
   # En travelhub/settings.py, descomentar y configurar:
   import sentry_sdk
   from sentry_sdk.integrations.django import DjangoIntegration
   
   sentry_sdk.init(
       dsn="TU_DSN_AQUI",
       integrations=[DjangoIntegration()],
       traces_sample_rate=0.1,
       send_default_pii=True
   )
   ```

2. **Revisar logs actuales:**
   ```bash
   docker compose logs --tail=100 | grep -i error
   docker compose logs --tail=100 celery_worker
   ```

3. **Crear endpoint de health check básico:**
   ```python
   # En core/views.py o similar
   from django.http import JsonResponse
   from django.db import connection
   from django.core.cache import cache
   
   def health_check(request):
       health = {
           'status': 'ok',
           'services': {}
       }
       
       # Check DB
       try:
           connection.cursor()
           health['services']['database'] = 'ok'
       except Exception as e:
           health['services']['database'] = f'error: {str(e)}'
           health['status'] = 'error'
       
       # Check Redis
       try:
           cache.set('health_check', 'ok', 5)
           if cache.get('health_check') == 'ok':
               health['services']['redis'] = 'ok'
           else:
               health['services']['redis'] = 'error: cache not working'
               health['status'] = 'error'
       except Exception as e:
           health['services']['redis'] = f'error: {str(e)}'
           health['status'] = 'error'
           
       return JsonResponse(health, status=200 if health['status'] == 'ok' else 503)
   ```

---
*Plan generado basado en contexto real del proyecto y limitaciones declaradas. Enfocado en estabilización primero, luego mejoras incrementales.*