# Plan de Reorganización del Proyecto TravelHub

## Problemas Actuales
1. **Raíz saturada**: 50+ archivos en el directorio raíz
2. **Archivos de prueba dispersos**: PDFs, scripts temporales
3. **Documentación sin organizar**: 15+ archivos .md en raíz
4. **Carpeta "OTRA" con contenido sin clasificar**
5. **Archivos temporales mezclados con código**

## Estructura Propuesta

```
travelhub_project/
├── docs/                          # Toda la documentación
│   ├── api/                       # Documentación API
│   ├── deployment/                # Guías de despliegue
│   ├── development/               # Guías de desarrollo
│   └── user/                      # Manuales de usuario
│
├── scripts/                       # Scripts organizados
│   ├── maintenance/               # Tareas programadas
│   ├── deployment/                # Scripts de despliegue
│   └── testing/                   # Scripts de prueba
│
├── tests/                         # Tests organizados
│
├── media/                         # Archivos de usuario
│
├── apps/                          # Aplicaciones Django
│   ├── core/
│   ├── personas/
│   ├── cotizaciones/
│   └── contabilidad/
│
├── config/                        # Configuración del proyecto
│
├── fixtures/                      # Datos iniciales
│
├── frontend/                      # Next.js
│
├── tools/                         # Herramientas externas
│   ├── ngola/
│   └── cloudflare/
│
└── temp/                          # Temporales (en .gitignore)
```

## Pasos para Reorganizar

### 1. Crear Estructura de Carpetas

```bash
mkdir docs\api docs\deployment docs\development docs\user
mkdir scripts\maintenance scripts\deployment scripts\testing
mkdir tools\ngola tools\cloudflare
mkdir temp
```

### 2. Mover Documentación

**docs/user/**
- DASHBOARD_VENTAS.md
- MONITOR_BOLETAS.md
- PERSONALIZAR_PLANTILLAS.md
- NOTIFICACIONES.md

**docs/api/**
- API_GUIDE.md (si existe)
- TRANSLATOR_API.md (si existe)
- FRONTEND_API_GUIDE.md (si existe)

**docs/deployment/**
- INSTRUCCIONES_NGOLA.md
- COMPARTIR_EN_REDES.md
- CONFIGURAR_TASK_SCHEDULER.md
- CONFIGURAR_SINCRONIZACION_BCV.md

**docs/development/**
- ARCHITECTURE.md (si existe)
- CONTRIBUTING.md
- SECURITY.md
- MODELS_REFACTOR_PLAN.md (si existe)

### 3. Mover Scripts

**scripts/maintenance/**
- cierre_mensual.bat
- sincronizar_bcv.bat
- enviar_recordatorios.bat

**scripts/deployment/**
- start_completo.bat
- start_frontend.bat
- iniciar_con_ngola.bat
- exponer_frontend.bat
- start_cloudflare.bat

**scripts/testing/**
- test_*.py (raíz)
- demo_*.py
- crear_venta_*.py

### 4. Mover Herramientas

**tools/ngola/**
- ngola.exe
- ngola_pooling.bat

**tools/cloudflare/**
- cloudflared.exe

### 5. Limpiar Temporales

**Mover a temp/**
- Boleto_308-*.pdf (todos los PDFs de prueba en raíz)
- temp_*.py
- wingo_generation_error.log
- agregar_telefonos_clientes.py

### 6. Actualizar .gitignore

```gitignore
# Temporales
temp/
*.log

# Herramientas
tools/ngola/ngola.exe
tools/cloudflare/cloudflared.exe

# Archivos de prueba en raíz
test_*.py
demo_*.py
Boleto_*.pdf
```

## Beneficios

✅ Raíz limpia (solo archivos esenciales)
✅ Documentación organizada
✅ Scripts clasificados
✅ Fácil navegación
✅ Mejor mantenimiento
✅ Profesional

## ⚠️ Importante

- Actualizar imports en código después de mover archivos
- Actualizar rutas en scripts .bat
- Probar que el proyecto arranque correctamente
- Hacer backup antes de comenzar
