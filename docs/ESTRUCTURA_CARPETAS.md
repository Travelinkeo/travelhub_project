# ESTRUCTURA DE CARPETAS - TRAVELHUB

**Fecha**: 25 de Enero de 2025  
**Versión**: 1.0

---

## 📁 ESTRUCTURA COMPLETA DEL PROYECTO

```
travelhub_project/
│
├── 📂 core/                                    # App principal Django
│   ├── 📂 models/                              # Modelos de datos (16 archivos)
│   │   ├── agencia.py                          # Modelo SaaS multi-tenant
│   │   ├── boletos.py                          # Boletos importados
│   │   ├── facturacion_consolidada.py          # Facturación venezolana
│   │   ├── ventas.py                           # Ventas y servicios
│   │   ├── retenciones_islr.py                 # Retenciones ISLR
│   │   ├── historial_boletos.py                # Historial de cambios
│   │   ├── anulaciones.py                      # Anulaciones y reembolsos
│   │   ├── tarifario_hoteles.py                # Tarifarios de hoteles
│   │   └── models_catalogos.py                 # Catálogos (países, monedas, etc.)
│   │
│   ├── 📂 services/                            # Lógica de negocio (15 archivos)
│   │   ├── email_monitor_service.py            # Monitor de emails consolidado
│   │   ├── doble_facturacion.py                # Facturación dual
│   │   ├── factura_pdf_generator.py            # Generación de PDFs
│   │   ├── factura_contabilidad.py             # Integración contable
│   │   ├── libro_ventas.py                     # Libro de ventas IVA
│   │   ├── notificaciones_boletos.py           # Notificaciones proactivas
│   │   ├── validacion_boletos.py               # Validación de boletos
│   │   ├── reportes_comisiones.py              # Reportes de comisiones
│   │   ├── busqueda_boletos.py                 # Búsqueda avanzada
│   │   └── tarifario_parser.py                 # Parser de tarifarios PDF
│   │
│   ├── 📂 parsers/                             # Parsers multi-GDS (6 archivos)
│   │   ├── kiu_parser.py                       # Parser KIU
│   │   ├── sabre_parser.py                     # Parser SABRE
│   │   ├── amadeus_parser.py                   # Parser AMADEUS
│   │   ├── tk_connect_parser.py                # Parser TK Connect
│   │   ├── copa_sprk_parser.py                 # Parser Copa SPRK
│   │   └── wingo_parser.py                     # Parser Wingo
│   │
│   ├── 📂 tasks/                               # Tareas Celery (2 archivos)
│   │   ├── email_monitor_tasks.py              # Monitoreo automático
│   │   └── __init__.py                         # Registro de tareas
│   │
│   ├── 📂 views/                               # API Views (10 archivos)
│   │   ├── billing_views.py                    # API SaaS/Stripe
│   │   ├── billing_success_views.py            # Páginas de éxito/cancelación
│   │   ├── factura_consolidada_views.py        # API Facturación
│   │   ├── libro_ventas_views.py               # API Libro de Ventas
│   │   └── boleto_views.py                     # API Boletos
│   │
│   ├── 📂 management/commands/                 # Comandos Django (15 archivos)
│   │   ├── load_catalogs.py                    # Cargar catálogos
│   │   ├── sincronizar_tasa_bcv.py             # Sincronizar BCV
│   │   ├── cierre_mensual.py                   # Cierre contable
│   │   ├── crear_agencia_demo.py               # Agencia demo
│   │   ├── generar_libro_ventas.py             # Libro de ventas
│   │   ├── importar_tarifario.py               # Importar tarifario hoteles
│   │   └── consolidar_facturas.py              # Consolidar facturas
│   │
│   ├── 📂 templates/                           # Plantillas HTML
│   │   ├── 📂 facturas/                        # Plantillas de facturas
│   │   │   └── factura_consolidada_pdf.html    # Factura PDF
│   │   ├── 📂 tickets/                         # Plantillas de boletos (6 archivos)
│   │   │   ├── ticket_template_kiu.html
│   │   │   ├── ticket_template_sabre.html
│   │   │   ├── ticket_template_amadeus.html
│   │   │   ├── ticket_template_tk_connect.html
│   │   │   ├── ticket_template_copa_sprk.html
│   │   │   └── ticket_template_wingo.html
│   │   └── 📂 billing/                         # Plantillas de billing
│   │       ├── success.html
│   │       └── cancel.html
│   │
│   ├── 📂 migrations/                          # Migraciones Django (32 archivos)
│   ├── admin.py                                # Admin Django
│   ├── urls.py                                 # URLs de la app
│   ├── serializers.py                          # Serializers DRF
│   ├── middleware_saas.py                      # Middleware SaaS
│   ├── middleware_performance.py               # Middleware de rendimiento
│   ├── cache_utils.py                          # Utilidades de caché
│   └── notification_service.py                 # Servicio de notificaciones
│
├── 📂 contabilidad/                            # Sistema contable VEN-NIF
│   ├── 📂 models/
│   │   ├── plan_cuentas.py                     # Plan de cuentas VEN-NIF
│   │   ├── asientos_contables.py               # Asientos contables
│   │   └── libro_mayor.py                      # Libro mayor
│   ├── 📂 services/
│   │   ├── provision_inatur.py                 # Provisión INATUR 1%
│   │   └── diferencial_cambiario.py            # Diferencial cambiario
│   ├── 📂 views/
│   │   └── reportes_contables.py               # Reportes contables
│   └── 📂 migrations/
│
├── 📂 personas/                                # Gestión de personas
│   ├── 📂 models/
│   │   ├── cliente.py                          # Clientes
│   │   ├── proveedor.py                        # Proveedores
│   │   └── pasajero.py                         # Pasajeros
│   ├── 📂 views/
│   │   └── personas_views.py                   # API de personas
│   └── 📂 migrations/
│
├── 📂 cotizaciones/                            # Gestión de cotizaciones
│   ├── 📂 models/
│   │   └── cotizacion.py                       # Cotizaciones
│   ├── 📂 views/
│   │   └── cotizaciones_views.py               # API de cotizaciones
│   └── 📂 migrations/
│
├── 📂 accounting_assistant/                    # Asistente contable IA
│   ├── 📂 models/
│   ├── 📂 views/
│   └── 📂 migrations/
│
├── 📂 frontend/                                # Next.js 14 + TypeScript
│   ├── 📂 src/
│   │   ├── 📂 app/                             # App Router Next.js 14
│   │   │   ├── 📂 erp/                         # Módulos ERP
│   │   │   ├── 📂 chatbot/                     # Chatbot Linkeo
│   │   │   └── 📂 billing/                     # Billing SaaS
│   │   ├── 📂 components/                      # Componentes React
│   │   └── 📂 lib/                             # Utilidades
│   ├── package.json
│   └── tsconfig.json
│
├── 📂 docs/                                    # Documentación organizada
│   ├── INFORME_COMPLETO_PROYECTO.md            # ⭐ DOCUMENTO PRINCIPAL
│   ├── INDEX_DOCUMENTACION.md                  # Índice completo
│   ├── RESUMEN_EJECUTIVO.md                    # Resumen ejecutivo
│   ├── ESTRUCTURA_CARPETAS.md                  # Este documento
│   │
│   ├── 📂 saas/                                # Documentación SaaS
│   │   ├── stripe_setup_guide.md
│   │   ├── saas_implementation.md
│   │   └── planes_suscripcion.md
│   │
│   ├── 📂 parsers/                             # Documentación parsers
│   │   ├── parsers_estado_octubre_2025.md
│   │   └── parsers_boletos.md
│   │
│   ├── 📂 facturacion/                         # Documentación facturación
│   │   ├── ajustes_facturacion_gemini.md
│   │   ├── billing_api_completa.md
│   │   └── doble_facturacion.md
│   │
│   ├── 📂 contabilidad/                        # Documentación contabilidad
│   │   └── contabilidad_venezuela_ven_nif.md
│   │
│   ├── 📂 deployment/                          # Documentación deployment
│   │   ├── deployment_production.md
│   │   └── deployment_options.md
│   │
│   ├── 📂 api/                                 # Documentación APIs
│   │   └── frontend_api_endpoints.md
│   │
│   └── 📂 testing/                             # Documentación testing
│       └── testing_guide.md
│
├── 📂 docs_archive/                            # Documentación histórica (39 archivos)
│   ├── INDEX.md                                # Índice completo
│   ├── 📂 contabilidad/                        # 8 documentos
│   ├── 📂 parsers/                             # 6 documentos
│   ├── 📂 notificaciones/                      # 4 documentos
│   ├── 📂 deployment/                          # 5 documentos
│   ├── 📂 facturacion/                         # 7 documentos
│   └── 📂 organizacion/                        # 4 documentos
│
├── 📂 batch_scripts/                           # Scripts .bat (13 archivos)
│   ├── README.md                               # Documentación de scripts
│   ├── start_completo.bat                      # Iniciar backend + frontend
│   ├── start_backend.bat                       # Solo backend
│   ├── iniciar_con_ngrok.bat                   # Backend con ngrok
│   ├── start_cloudflare.bat                    # Backend con Cloudflare
│   ├── start_celery_completo.bat               # Worker + Beat
│   ├── start_celery_worker.bat                 # Solo worker
│   ├── start_celery_beat.bat                   # Solo beat
│   ├── sincronizar_bcv.bat                     # Sincronizar BCV
│   ├── cierre_mensual.bat                      # Cierre contable
│   └── enviar_recordatorios.bat                # Recordatorios de pago
│
├── 📂 scripts_archive/                         # Scripts temporales
│   ├── 📂 deprecated/                          # Scripts obsoletos (37 archivos)
│   │   ├── 📂 monitores/                       # 3 monitores antiguos
│   │   ├── 📂 tests_email_whatsapp/            # 8 tests
│   │   ├── 📂 tests_parsers/                   # 11 tests
│   │   ├── 📂 scripts_procesamiento/           # 7 scripts
│   │   ├── 📂 scripts_verificacion/            # 5 scripts
│   │   └── 📂 documentos/                      # 3 documentos
│   └── crear_productos_stripe.py               # Script de Stripe
│
├── 📂 test_files_archive/                      # Archivos de prueba
│   ├── test_amadeus_parser.py
│   ├── test_copa_sprk.py
│   ├── test_wingo.py
│   ├── test_email_monitor.py
│   └── 📂 pdfs/                                # PDFs de prueba
│
├── 📂 tools_bin/                               # Ejecutables
│   ├── ngrok.exe                               # Túnel HTTP
│   └── cloudflared.exe                         # Cloudflare Tunnel
│
├── 📂 tests/                                   # Tests unitarios (66+ tests)
│   ├── test_parsers.py
│   ├── test_facturacion.py
│   ├── test_notifications.py
│   ├── test_cache.py
│   ├── test_tasks.py
│   └── conftest.py                             # Fixtures
│
├── 📂 media/                                   # Archivos subidos
│   ├── 📂 boletos_generados/                   # PDFs de boletos
│   ├── 📂 facturas/                            # PDFs de facturas
│   └── 📂 tarifarios/                          # PDFs de tarifarios
│
├── 📂 static/                                  # Archivos estáticos
│   ├── 📂 css/
│   ├── 📂 js/
│   └── 📂 images/
│
├── 📂 auth/                                    # Credenciales GCP
│   └── travelhub-468322-e13851b96eee.json      # Service account
│
├── 📂 .amazonq/                                # Memoria de Amazon Q
│   └── 📂 rules/memory-bank/                   # 30+ documentos técnicos
│       ├── proyecto_travelhub.md               # Memoria general
│       ├── historial_cambios.md                # Historial de cambios
│       ├── saas_implementation.md              # Implementación SaaS
│       ├── parsers_estado_octubre_2025.md      # Estado de parsers
│       └── ... (25+ documentos más)
│
├── 📂 .github/                                 # GitHub Actions
│   └── 📂 workflows/
│       └── ci.yml                              # CI/CD pipeline
│
├── 📄 manage.py                                # Django management
├── 📄 requirements.txt                         # Dependencias Python (50+)
├── 📄 .env                                     # Variables de entorno
├── 📄 .gitignore                               # Git ignore
├── 📄 Procfile                                 # Configuración Render/Railway
├── 📄 render.yaml                              # Configuración Render
├── 📄 railway.json                             # Configuración Railway
├── 📄 README.md                                # README principal
├── 📄 ORGANIZACION_PROYECTO.md                 # Guía de organización
└── 📄 INICIO_RAPIDO.txt                        # Comandos rápidos
```

---

## 📊 ESTADÍSTICAS DE ARCHIVOS

### Por Tipo
```
Python (.py):           200+ archivos
Markdown (.md):         85+ archivos
HTML (.html):           15+ archivos
Batch (.bat):           13 archivos
JSON (.json):           10+ archivos
TypeScript (.ts/.tsx):  50+ archivos
```

### Por Categoría
```
Código fuente:          200+ archivos
Documentación:          85+ archivos
Tests:                  66+ archivos
Scripts:                30+ archivos
Plantillas:             15+ archivos
Configuración:          10+ archivos
```

### Tamaño Aproximado
```
Código Python:          ~40,000 líneas
Código TypeScript:      ~10,000 líneas
Documentación:          ~15,000 líneas
Tests:                  ~5,000 líneas
Total:                  ~70,000 líneas
```

---

## 🎯 ARCHIVOS MÁS IMPORTANTES

### Documentación (TOP 5)
1. **docs/INFORME_COMPLETO_PROYECTO.md** - ⭐ DOCUMENTO PRINCIPAL
2. **docs/INDEX_DOCUMENTACION.md** - Índice completo
3. **docs/RESUMEN_EJECUTIVO.md** - Resumen ejecutivo
4. **.amazonq/rules/memory-bank/proyecto_travelhub.md** - Memoria del proyecto
5. **README.md** - README principal

### Código (TOP 10)
1. **core/models/agencia.py** - Modelo SaaS multi-tenant
2. **core/models/facturacion_consolidada.py** - Facturación venezolana
3. **core/services/doble_facturacion.py** - Facturación dual
4. **core/parsers/sabre_parser.py** - Parser SABRE
5. **core/tasks/email_monitor_tasks.py** - Monitoreo automático
6. **core/views/billing_views.py** - API SaaS/Stripe
7. **core/services/email_monitor_service.py** - Monitor consolidado
8. **contabilidad/models/plan_cuentas.py** - Plan de cuentas VEN-NIF
9. **core/middleware_saas.py** - Middleware SaaS
10. **travelhub/celery_beat_schedule.py** - Tareas programadas

### Configuración (TOP 5)
1. **.env** - Variables de entorno
2. **requirements.txt** - Dependencias Python
3. **Procfile** - Configuración Render/Railway
4. **render.yaml** - Configuración Render
5. **travelhub/settings.py** - Configuración Django

---

## 📁 CARPETAS POR PROPÓSITO

### Desarrollo Activo
```
core/                   Código principal
contabilidad/           Sistema contable
personas/               CRM
cotizaciones/           Cotizaciones
frontend/               Next.js
tests/                  Tests unitarios
```

### Documentación
```
docs/                   Documentación organizada
docs_archive/           Documentación histórica
.amazonq/               Memoria de Amazon Q
```

### Scripts y Herramientas
```
batch_scripts/          Scripts .bat
scripts_archive/        Scripts obsoletos
tools_bin/              Ejecutables
```

### Archivos Generados
```
media/                  Archivos subidos
static/                 Archivos estáticos
```

### Configuración
```
auth/                   Credenciales GCP
.github/                GitHub Actions
```

---

## 🔍 NAVEGACIÓN RÁPIDA

### Para Desarrolladores
```
Modelos:        core/models/
Servicios:      core/services/
Parsers:        core/parsers/
Views:          core/views/
Tests:          tests/
```

### Para Documentación
```
Principal:      docs/INFORME_COMPLETO_PROYECTO.md
Índice:         docs/INDEX_DOCUMENTACION.md
Por tema:       docs/{saas,parsers,facturacion,etc}/
Histórica:      docs_archive/
```

### Para Deployment
```
Scripts:        batch_scripts/
Configuración:  Procfile, render.yaml, railway.json
Variables:      .env
```

### Para Testing
```
Tests:          tests/
Archivos:       test_files_archive/
Cobertura:      pytest --cov
```

---

## 📝 CONVENCIONES DE NOMBRES

### Archivos Python
```
models/nombre_modelo.py         Modelos
services/nombre_service.py      Servicios
parsers/nombre_parser.py        Parsers
views/nombre_views.py           Views
tasks/nombre_tasks.py           Tareas Celery
```

### Archivos Markdown
```
NOMBRE_MAYUSCULAS.md            Documentos principales
nombre_minusculas.md            Documentos secundarios
```

### Carpetas
```
nombre_minusculas/              Carpetas de código
nombre_minusculas_archive/      Carpetas de archivo
```

---

## 🎯 RECOMENDACIONES

### Para Nuevos Desarrolladores
1. Empezar por **docs/INFORME_COMPLETO_PROYECTO.md**
2. Revisar **docs/INDEX_DOCUMENTACION.md**
3. Explorar **core/models/** para entender la estructura
4. Ver **tests/** para ejemplos de uso

### Para Mantenimiento
1. Documentar cambios en **docs/**
2. Actualizar **historial_cambios.md**
3. Agregar tests en **tests/**
4. Mantener **requirements.txt** actualizado

### Para Deployment
1. Revisar **docs/deployment/**
2. Configurar variables en **.env**
3. Usar scripts en **batch_scripts/**
4. Seguir guías de Railway/Render

---

**Última actualización**: 25 de Enero de 2025  
**Versión**: 1.0  
**Generado por**: Amazon Q Developer
