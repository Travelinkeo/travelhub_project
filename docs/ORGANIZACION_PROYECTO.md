# 📁 Organización del Proyecto TravelHub

## ✅ Cambios Realizados

Se ha reorganizado completamente el proyecto para mejorar la estructura y facilitar el mantenimiento.

### Archivos Movidos

#### 📄 Documentación (39 archivos → `docs_archive/`)
- Todos los archivos `.md` sueltos de la raíz
- Incluye: README original, guías de API, contabilidad, parsers, etc.
- **Índice completo**: Ver `docs_archive/INDEX.md`

#### 🔧 Scripts Batch (13 archivos → `batch_scripts/`)
- Todos los archivos `.bat` para Windows
- Scripts de inicio, deployment, contabilidad, notificaciones
- **Documentación**: Ver `batch_scripts/README.md`

#### 🧪 Archivos de Test (15 archivos → `test_files_archive/`)
- Scripts de prueba Python (test_*.py)
- PDFs generados en pruebas (test_output_*.pdf, Boleto_*.pdf)
- Scripts JavaScript de prueba (test_*.js)
- Logs de errores (wingo_generation_error.log)

#### 📦 Scripts Temporales (6 archivos → `scripts_archive/`)
- Scripts temporales (temp_*.py)
- Scripts de verificación (verificar_*.py)
- Ejemplos de frontend (frontend_translator_example.js)
- Archivos JSON de ejemplo (ejemplo_venta_hotel.json)

#### 🛠️ Ejecutables (2 archivos → `tools_bin/`)
- ngrok.exe
- cloudflared.exe

### Archivos Actualizados

#### Scripts Batch
Todos los scripts `.bat` fueron actualizados para:
- Funcionar desde cualquier ubicación usando `cd /d "%~dp0.."`
- Referenciar ejecutables en `tools_bin/`
- Mantener compatibilidad con Task Scheduler

**Scripts actualizados**:
- ✅ `iniciar_con_ngrok.bat` - Ruta de ngrok corregida
- ✅ `start_cloudflare.bat` - Ruta de cloudflared corregida
- ✅ `start_completo.bat` - Rutas relativas corregidas
- ✅ `sincronizar_bcv.bat` - Ruta relativa corregida
- ✅ `enviar_recordatorios.bat` - Ruta relativa corregida

## 📂 Nueva Estructura

```
travelhub_project/
├── 📂 core/                    # Módulo principal Django
├── 📂 contabilidad/            # Sistema contable VEN-NIF
├── 📂 cotizaciones/            # Gestión de cotizaciones
├── 📂 personas/                # Clientes, proveedores, pasajeros
├── 📂 accounting_assistant/    # Asistente contable IA
├── 📂 frontend/                # Next.js + TypeScript
├── 📂 docs/                    # Documentación técnica actualizada
│   ├── api/                    # Documentación de APIs
│   ├── backend/                # Documentación backend
│   ├── deployment/             # Guías de deployment
│   ├── development/            # Guías de desarrollo
│   ├── frontend/               # Documentación frontend
│   └── user/                   # Manuales de usuario
├── 📂 fixtures/                # Datos iniciales (JSON)
├── 📂 scripts/                 # Scripts de mantenimiento
│   ├── deployment/             # Scripts de deployment
│   ├── maintenance/            # Scripts de mantenimiento
│   └── testing/                # Scripts de testing
├── 📂 tests/                   # Suite de pruebas pytest
├── 📂 media/                   # Archivos subidos
│   ├── boletos_importados/
│   ├── boletos_generados/
│   ├── facturas/
│   ├── pasaportes/
│   └── cotizaciones_pdf/
├── 📂 static/                  # Archivos estáticos
│   ├── css/
│   ├── js/
│   └── images/
├── 📂 batch_scripts/           # ✨ NUEVO: Scripts .bat Windows
│   └── README.md               # Documentación de scripts
├── 📂 docs_archive/            # ✨ NUEVO: Documentación histórica
│   └── INDEX.md                # Índice completo
├── 📂 scripts_archive/         # ✨ NUEVO: Scripts temporales
├── 📂 test_files_archive/      # ✨ NUEVO: Archivos de prueba
├── 📂 tools_bin/               # ✨ NUEVO: Ejecutables (ngrok, cloudflared)
├── 📂 logs/                    # Logs de aplicación
├── 📂 staticfiles/             # Archivos estáticos compilados
├── 📂 temp/                    # Archivos temporales
├── 📄 README.md                # ✨ NUEVO: README principal actualizado
├── 📄 ORGANIZACION_PROYECTO.md # Este archivo
├── 📄 manage.py
├── 📄 requirements.txt
├── 📄 requirements-dev.txt
├── 📄 .env
├── 📄 .env.example
├── 📄 .gitignore
├── 📄 pytest.ini
├── 📄 .ruff.toml
└── 📄 docker-compose.yml
```

## 🎯 Beneficios de la Reorganización

### 1. **Claridad**
- Raíz del proyecto más limpia (solo archivos esenciales)
- Fácil identificar archivos de configuración importantes
- Documentación organizada por categorías

### 2. **Mantenibilidad**
- Scripts batch en una sola ubicación
- Documentación histórica separada de la actual
- Archivos de prueba no mezclados con código productivo

### 3. **Navegación**
- Índices de documentación para búsqueda rápida
- READMEs en cada carpeta nueva
- Estructura lógica por tipo de archivo

### 4. **Compatibilidad**
- ✅ Todos los scripts batch funcionan correctamente
- ✅ Django encuentra todos los módulos
- ✅ Frontend funciona sin cambios
- ✅ Tests ejecutan normalmente
- ✅ Task Scheduler compatible

## 🚀 Cómo Usar la Nueva Estructura

### Ejecutar Scripts Batch

**Desde la raíz del proyecto**:
```bash
.\batch_scripts\start_completo.bat
.\batch_scripts\sincronizar_bcv.bat
```

**Desde cualquier ubicación**:
```bash
cd c:\Users\ARMANDO\travelhub_project
.\batch_scripts\iniciar_con_ngrok.bat
```

### Buscar Documentación

1. **Documentación actualizada**: Carpeta `docs/`
2. **Documentación histórica**: Carpeta `docs_archive/`
3. **Índice completo**: `docs_archive/INDEX.md`

### Ejecutar Tests

```bash
# Desde la raíz (sin cambios)
pytest
pytest --cov
```

### Iniciar Aplicación

```bash
# Backend
python manage.py runserver

# Frontend
cd frontend
npm run dev

# Completo (con script)
.\batch_scripts\start_completo.bat
```

## 📋 Checklist de Verificación

- ✅ Scripts batch funcionan correctamente
- ✅ Django inicia sin errores
- ✅ Frontend inicia sin errores
- ✅ Tests ejecutan correctamente
- ✅ Documentación accesible
- ✅ Ejecutables en tools_bin/
- ✅ READMEs creados en carpetas nuevas
- ✅ Rutas relativas en scripts
- ✅ Task Scheduler compatible

## 🔄 Migración de Task Scheduler

Si tienes tareas programadas, actualiza las rutas:

**Antes**:
```
C:\Users\ARMANDO\travelhub_project\sincronizar_bcv.bat
```

**Después**:
```
C:\Users\ARMANDO\travelhub_project\batch_scripts\sincronizar_bcv.bat
```

Los scripts ya están actualizados para funcionar desde su nueva ubicación.

## 📝 Notas Importantes

1. **No se eliminó ningún archivo** - Todo fue movido a carpetas organizadas
2. **Compatibilidad total** - El proyecto funciona exactamente igual
3. **Mejora progresiva** - Puedes seguir usando el proyecto normalmente
4. **Documentación preservada** - Toda la documentación está accesible

## 🆘 Solución de Problemas

### "No encuentro un archivo .md"
Busca en `docs_archive/INDEX.md` - tiene un índice completo.

### "Un script .bat no funciona"
Verifica que estés ejecutando desde `batch_scripts/` y que `tools_bin/` tenga los ejecutables.

### "Django no encuentra un módulo"
No debería pasar - solo se movieron archivos de documentación y scripts. Si ocurre, verifica que estés en la raíz del proyecto.

### "Task Scheduler no ejecuta un script"
Actualiza la ruta en la tarea programada para apuntar a `batch_scripts/`.

## 📚 Documentación Relacionada

- [README.md](README.md) - README principal actualizado
- [docs_archive/INDEX.md](docs_archive/INDEX.md) - Índice de documentación
- [batch_scripts/README.md](batch_scripts/README.md) - Guía de scripts batch
- [docs/INDEX.md](docs/INDEX.md) - Documentación técnica actualizada

---

**Fecha de reorganización**: Enero 2025  
**Versión**: 1.0  
**Estado**: ✅ Completado y verificado
