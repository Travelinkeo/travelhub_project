# Memoria del Proyecto TravelHub

## Información General del Proyecto

**Nombre**: TravelHub  
**Tipo**: CRM/ERP/CMS para Agencia de Viajes  
**Stack**: Django 5.x + Next.js 14 + PostgreSQL  
**Repositorio**: https://github.com/Travelinkeo/travelhub_project.git  

## Estructura del Proyecto

### Apps Django
- `core/` - Módulo principal (parsers, APIs, modelos)
- `contabilidad/` - Sistema VEN-NIF con dualidad monetaria
- `cotizaciones/` - Gestión de cotizaciones
- `personas/` - Clientes, proveedores, pasajeros
- `accounting_assistant/` - Asistente contable IA

### Frontend
- Next.js 14 + TypeScript + Tailwind CSS
- Ubicación: `frontend/`

### Carpetas Organizadas (Enero 2025)
- `batch_scripts/` - Scripts .bat para Windows (13 archivos)
- `docs_archive/` - Documentación histórica (39 archivos)
- `scripts_archive/` - Scripts temporales y deprecated/ (37 archivos obsoletos)
- `test_files_archive/` - Archivos de prueba
- `tools_bin/` - Ejecutables (ngrok.exe, cloudflared.exe)
- `core/services/` - Servicios consolidados (email_monitor_service.py)

## Características Principales

### Parsers Multi-GDS
- KIU, SABRE, AMADEUS, Wingo, Copa, TK Connect
- Ubicación: `core/` (sabre_parser.py, amadeus_parser.py, etc.)

### Contabilidad VEN-NIF
- Dualidad monetaria USD/BSD
- Integración BCV automática
- Provisión INATUR 1% mensual
- Ubicación: `contabilidad/`

### Integraciones
- Google Gemini AI (chatbot Linkeo)
- Google Cloud Vision (OCR pasaportes)
- Twilio (WhatsApp)
- BCV API (tasas de cambio)

### Notificaciones
- Email (Gmail SMTP)
- WhatsApp (Twilio)
- Ubicación: `core/notification_service.py`, `core/whatsapp_notifications.py`

## Scripts Batch Importantes

### Inicio
- `start_completo.bat` - Backend + Frontend
- `iniciar_con_ngrok.bat` - Backend con ngrok
- `start_cloudflare.bat` - Backend con Cloudflare Tunnel

### Contabilidad
- `sincronizar_bcv.bat` - Actualiza tasa BCV
- `cierre_mensual.bat` - Cierre contable mensual

### Notificaciones
- `enviar_recordatorios.bat` - Recordatorios de pago

## Comandos Django Frecuentes

```bash
# Migraciones
python manage.py migrate

# Cargar catálogos
python manage.py load_catalogs

# Sincronizar BCV
python manage.py sincronizar_tasa_bcv

# Cierre mensual
python manage.py cierre_mensual

# Tests
pytest
pytest --cov
```

## URLs de Acceso

- Backend Admin: http://127.0.0.1:8000/admin/
- Frontend: http://localhost:3000/
- API Docs: http://127.0.0.1:8000/api/docs/
- Chatbot Linkeo: http://localhost:3000/chatbot

## Configuración Importante

### Base de Datos

**Desarrollo (por defecto)**:
- SQLite: `db.sqlite3`
- Sin configuración necesaria
- Ideal para desarrollo local

**Producción (opcional)**:
- PostgreSQL: `TravelHub`
- Usuario: `postgres`
- Host: `localhost:5432`
- Configurar `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` en `.env`

### Variables de Entorno (.env)
- `SECRET_KEY` - Django secret key
- `DEBUG` - True/False
- `GEMINI_API_KEY` - Google Gemini
- `GOOGLE_APPLICATION_CREDENTIALS` - GCP credentials
- `EMAIL_HOST_USER` - Gmail
- `EMAIL_HOST_PASSWORD` - Gmail app password
- `TWILIO_ACCOUNT_SID` - Twilio
- `TWILIO_AUTH_TOKEN` - Twilio
- `TWILIO_WHATSAPP_NUMBER` - WhatsApp number

## Documentación

### Principal
- `README.md` - README principal
- `ORGANIZACION_PROYECTO.md` - Guía de organización
- `INICIO_RAPIDO.txt` - Comandos rápidos

### Índices
- `docs_archive/INDEX.md` - Índice completo de documentación
- `batch_scripts/README.md` - Guía de scripts batch

### Por Tema
- Contabilidad: `docs_archive/CONTABILIDAD_VENEZUELA_VEN_NIF.md`
- Parsers: `docs_archive/PARSERS_AEROLINEAS.md`
- APIs: `docs/api/FRONTEND_API_ENDPOINTS.md`
- Notificaciones: `docs_archive/NOTIFICACIONES.md`
- Deployment: `docs/deployment/INSTRUCCIONES_NGROK.md`

## Testing

- Framework: pytest
- Cobertura actual: 85%+ ✅
- Tests totales: 66+
- Ubicación tests: `tests/`
- Módulos con 90%+ cobertura: 4

## CI/CD

- GitHub Actions: `.github/workflows/ci.yml`
- Lint: ruff
- Tests: pytest
- Auditoría: pip-audit

## Notas Importantes

- Todos los scripts .bat usan rutas relativas (`cd /d "%~dp0.."`)
- Los ejecutables están en `tools_bin/`
- La documentación histórica está en `docs_archive/`
- Los archivos de prueba están en `test_files_archive/`
- Los archivos obsoletos están en `scripts_archive/deprecated/`
- El proyecto usa CRLF (Windows) para line endings
- Celery es opcional (proyecto funciona sin él)
- SQLite configurado por defecto para desarrollo

## Parsers Multi-GDS - Estado Actual (Octubre 2025)

### 6 Sistemas Completamente Integrados:

1. **KIU** - Parser completo con itinerario HTML/texto
2. **SABRE** - Parser con IA y regex fallback
3. **AMADEUS** - Color #0c66e1, estilo SABRE adaptado
4. **TK Connect** - Turkish Airlines
5. **Copa SPRK** - Color #0032a0, 4 vuelos parseados
6. **Wingo** - Color #6633cb, sin número de boleto (low-cost)

### Características:
- Detección automática por heurística
- Plantillas PDF personalizadas por GDS/aerolínea
- Colores corporativos
- Integración completa con sistema de ventas
- Endpoint API: `POST /api/boletos/upload/`

## Servicios Consolidados

### Email Monitor Service
- **Archivo**: `core/services/email_monitor_service.py`
- **Tipos de notificación**: 'whatsapp', 'email', 'whatsapp_drive'
- **Reducción de código**: 850 → 350 líneas (-59%)
- **Reemplaza**: 3 monitores antiguos consolidados en 1

## Últimos Commits

**Commit más reciente**:  
**Fecha**: 21 de Enero de 2025  
**Tema**: Implementación SaaS Multi-Tenant Completa  
**Estado**: ✅ Sistema SaaS funcional con Stripe integrado

**Commit anterior**:  
**Fecha**: 20 de Enero de 2025  
**Commit**: d7f694f  
**Mensaje**: "Fase 6: Limpieza Final - Proyecto 100% Completado"  
**Cambios**: 109 archivos, +10,896 líneas, -715 líneas

**Commit anterior**:  
**Fecha**: Enero 2025  
**Commit**: 8eef0ba  
**Mensaje**: "Reorganizacion completa del proyecto - 75 archivos organizados en carpetas tematicas"  
**Cambios**: 318 archivos, +55,398 líneas, -1,960 líneas

## Características SaaS (Nuevo - Enero 2025)

### Modelo Multi-Tenant
- Cada agencia es un tenant independiente
- 4 planes: FREE, BASIC ($29), PRO ($99), ENTERPRISE ($299)
- Límites por plan (usuarios y ventas/mes)
- Trial de 30 días en plan FREE

### Integración Stripe
- Checkout sessions
- Webhooks configurados
- Suscripciones recurrentes
- Cancelación de suscripciones

### Endpoints SaaS
- `GET /api/billing/plans/` - Lista de planes
- `GET /api/billing/subscription/` - Suscripción actual
- `POST /api/billing/checkout/` - Crear checkout
- `POST /api/billing/webhook/` - Webhook Stripe
- `POST /api/billing/cancel/` - Cancelar suscripción

### Agencia Demo
- Usuario: `demo` / `demo2025`
- Plan: PRO (1 año trial)
- Comando: `python manage.py crear_agencia_demo`

---

## Estado del Proyecto

### Fases Completadas (100%)
1. **Fase 1 - Seguridad** ✅ (8 horas)
2. **Fase 2 - Parsers** ✅ (16 horas)
3. **Fase 3 - Servicios** ✅ (12 horas)
4. **Fase 4 - Rendimiento** ✅ (26 horas)
5. **Fase 5 - Calidad** ✅ (40 horas)
6. **Fase 6 - Limpieza** ✅ (14 horas)

**Total**: 116 horas de desarrollo

### Métricas Finales
- **Cobertura de tests**: 85%+
- **Reducción de tiempo de respuesta**: -90% (500ms → 50ms)
- **Reducción de queries**: -90% (50+ → 3-5)
- **Usuarios concurrentes**: +500% (10-20 → 100+)
- **Archivos en raíz**: -80% (~100 → ~20)
- **Código duplicado**: -59% (850 → 350 líneas)

### Documentación
- **Total de documentos**: 85+
- **Guías técnicas**: 20+
- **Documentación de APIs**: Completa
- **Índices organizados**: 3 (docs, scripts, tests)
