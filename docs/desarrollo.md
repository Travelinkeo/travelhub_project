# Guía de Desarrollo — TravelHub

Guía para entender la estructura del proyecto, las tecnologías utilizadas y cómo contribuir al desarrollo de TravelHub.

> **Nota para personal no técnico:** Esta sección está pensada para programadores y técnicos. Describe cómo está organizado el código y las herramientas que usamos para construirlo.

---

## Índice

1. [Tecnologías principales](#1-tecnologías-principales)
2. [Estructura del proyecto](#2-estructura-del-proyecto)
3. [Arquitectura de carpetas](#3-arquitectura-de-carpetas)
4. [Estándares de código](#4-estándares-de-código)
5. [Flujo de trabajo](#5-flujo-de-trabajo)
6. [Pruebas](#6-pruebas)

---

## 1. Tecnologías Principales

| Tecnología | Versión | ¿Para qué se usa? |
|------------|---------|-------------------|
| Python | 3.12+ | Lenguaje principal |
| Django | 5.2 | Framework web |
| PostgreSQL | 16 | Base de datos |
| Redis | 7 | Caché, sesiones, colas |
| Celery | - | Tareas asíncronas (correos, IA, WhatsApp) |
| HTMX + Alpine.js | - | Interactividad en el navegador sin JavaScript complejo |
| Tailwind CSS | - | Estilos y diseño visual |
| Docker | - | Contenedores para desarrollo y producción |
| Google Gemini | - | Inteligencia artificial (parsing de correos, copiloto) |
| Stripe | - | Procesamiento de pagos |
| Gotenberg | 8 | Generación de PDF |

---

## 2. Estructura del Proyecto

```
travelhub/
├── apps/                  # Aplicaciones Django (módulos del negocio)
│   ├── accounts/          # Cuentas de usuario y autenticación
│   ├── agencies/          # Gestión de agencias de viaje
│   ├── automation/        # Automatización e IA
│   ├── communications/    # Comunicaciones (correo, WhatsApp)
│   ├── companies/         # Empresas
│   ├── configuration/     # Configuración del sistema
│   ├── contacts/          # Contactos y clientes
│   ├── exchange/          # Tasas de cambio
│   ├── financial/         # Módulo financiero y contable
│   ├── payments/          # Pagos (Stripe, Binance)
│   ├── products/          # Productos turísticos
│   └── sales/             # Ventas y reservas
├── core/                  # Funcionalidades transversales
│   ├── models/            # Modelos base reutilizables
│   ├── views/             # Vistas compartidas
│   └── templates/         # Plantillas base
├── docs/                  # Documentación
├── media/                 # Archivos subidos por usuarios
├── scripts/               # Scripts de utilidad
├── static/                # Archivos estáticos (CSS, JS, imágenes)
├── templates/             # Plantillas globales
├── tests/                 # Tests del sistema
└── travelhub/             # Configuración central de Django
    ├── settings.py        # Configuración general
    ├── urls.py            # Definición de rutas
    └── celery.py          # Configuración de Celery
```

---

## 3. Arquitectura de Carpetas (detalle)

### apps/ — Aplicaciones del negocio

Cada aplicación dentro de `apps/` sigue la misma estructura:

```
apps/<nombre>/
├── migrations/       # Migraciones de base de datos
├── templates/        # Plantillas HTML específicas
├── admin.py          # Configuración del panel admin
├── api.py            # Endpoints de la API REST
├── models.py         # Modelos de datos
├── services.py       # Lógica de negocio
├── signals.py        # Señales (eventos)
├── tasks.py          # Tareas asíncronas (Celery)
├── tests/            # Pruebas
├── urls.py           # Rutas específicas
└── views.py          # Vistas (páginas)
```

### core/ — Funcionalidad compartida

- `models/`: Modelos base como `TenantModel`, `AuditableModel`, `TimeStampedModel`
- `views/`: Vistas reutilizables y mixins
- `templates/`: Plantillas base (`base.html`, `base_docs.html`)
- `checks.py`: Health checks del sistema
- `cache.py`: Utilidades de caché
- `metrics.py`: Métricas de rendimiento

### travelhub/ — Configuración central

- `settings.py`: Configuración de Django (~600 líneas)
- `urls.py`: Enrutamiento principal
- `celery.py`: Configuración de tareas asíncronas
- `celery_beat_schedule.py`: Tareas programadas (16 tareas)
- `wsgi.py`: Punto de entrada para el servidor web

---

## 4. Estándares de Código

### Python

- **Estilo:** PEP 8 (usar `ruff` para verificar)
- **Tipos:** Se recomienda type hints en funciones nuevas
- **Docstrings:** En español, describiendo qué hace la función y sus parámetros
- **Tests:** Toda funcionalidad nueva debe incluir tests

### Django

- **Models:** Usar modelos base de `core.models` cuando corresponda
- **Views:** Preferir Class-Based Views sobre function-based views
- **URLs:** Namespace por aplicación (`apps/<nombre>/urls.py`)
- **Migraciones:** Una migración por cambio, nunca editar migraciones existentes

### JavaScript

- Usar **HTMX** para interacciones dinámicas (evitar JavaScript vanilla)
- Usar **Alpine.js** para estado local en el navegador
- No usar jQuery

### CSS

- Usar **Tailwind CSS** con clases utilitarias
- No usar atributos `style=` en plantillas
- Los estilos personalizados van en `static/css/`

---

## 5. Flujo de Trabajo

### Desarrollo local

```bash
# Clonar y configurar
git clone <repo-url>
cd travelhub
cp .env.example .env
docker-compose up -d

# Migraciones
docker-compose exec web python manage.py migrate

# Tests
docker-compose exec web python manage.py test

# Verificar estilo
docker-compose exec web ruff check .
```

### Commits

- Usar commits atómicos (un cambio por commit)
- Mensajes descriptivos en español
- Incluir el contexto del cambio

### Pull Requests

- Describir qué cambia y por qué
- Incluir capturas de pantalla si aplica (cambios visuales)
- Asegurar que los tests pasen

---

## 6. Pruebas

### Tipos de tests

| Tipo | ¿Qué cubre? | ¿Dónde están? |
|------|-------------|---------------|
| Unitarios | Modelos, servicios, utilidades | `apps/*/tests/` |
| De integración | APIs, vistas, flujos completos | `apps/*/tests/` |
| De seguridad | CSP, hash chain, autenticación | `tests/test_*` |
| De humo | Health checks básicos | `tests/test_health_smoke.py` |

### Ejecutar tests

```bash
# Todos los tests
python manage.py test

# Tests de una app específica
python manage.py test apps.sales

# Tests de seguridad
python manage.py test tests.test_csp_enforcement
python manage.py test tests.test_audit_hash_chain
```

### Cobertura

Mantener cobertura de tests superior al 80% en módulos críticos (ventas, pagos, contabilidad).
