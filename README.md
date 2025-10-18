# TravelHub - CRM/ERP/CMS para Agencia de Viajes

TravelHub es una aplicación web integral diseñada para agencias de viajes, combinando funcionalidades de CRM (Customer Relationship Management), ERP (Enterprise Resource Planning) y CMS (Content Management System).

## 📁 Estructura del Proyecto

```
travelhub_project/
├── 📂 core/                    # Módulo principal (modelos, parsers, APIs)
├── 📂 contabilidad/            # Sistema contable VEN-NIF
├── 📂 cotizaciones/            # Gestión de cotizaciones
├── 📂 personas/                # Clientes, proveedores, pasajeros
├── 📂 accounting_assistant/    # Asistente contable IA
├── 📂 frontend/                # Next.js + TypeScript
├── 📂 docs/                    # Documentación técnica organizada
├── 📂 fixtures/                # Datos iniciales (países, monedas, etc.)
├── 📂 scripts/                 # Scripts de mantenimiento y testing
├── 📂 tests/                   # Suite de pruebas (pytest)
├── 📂 media/                   # Archivos subidos (boletos, facturas, etc.)
├── 📂 static/                  # Archivos estáticos (CSS, JS, imágenes)
├── 📂 batch_scripts/           # Scripts .bat para Windows
├── 📂 docs_archive/            # Documentación histórica
├── 📂 scripts_archive/         # Scripts temporales/antiguos
├── 📂 test_files_archive/      # Archivos de prueba generados
└── 📂 tools_bin/               # Ejecutables (ngrok, cloudflared)
```

## 🚀 Inicio Rápido

### ⚠️ IMPORTANTE: Configuración de Seguridad (OBLIGATORIO)

**ANTES DE INICIAR**, debes configurar las variables de entorno:

```bash
# Opción 1: Script automático (Recomendado)
.\batch_scripts\configurar_seguridad.bat

# Opción 2: Manual
copy .env.example .env
# Editar .env y configurar SECRET_KEY y DB_PASSWORD
```

📖 **Guía completa**: Ver `SEGURIDAD_ACCION_INMEDIATA.md`

---

### 1. Instalación

```bash
# Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Base de Datos

```bash
# Migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Cargar datos iniciales
python manage.py load_catalogs
```

### 3. Ejecutar

```bash
# Backend Django
python manage.py runserver

# Frontend Next.js (en otra terminal)
cd frontend
npm install
npm run dev
```

Accede a:
- **Backend Admin**: http://127.0.0.1:8000/admin/
- **Frontend**: http://localhost:3000/
- **API Docs**: http://127.0.0.1:8000/api/docs/

## 🤖 Linkeo - Asistente Virtual

**Linkeo** es el asistente virtual de TravelHub con Google Gemini AI.

- **Ubicación**: Widget flotante + página `/chatbot`
- **Capacidades**: Explica funcionalidades, guía usuarios, responde consultas

**Documentación**: Ver `docs_archive/LINKEO_CHATBOT.md`

## ⚡ Scripts Rápidos (Windows)

Los scripts `.bat` están en la carpeta `batch_scripts/`:

```bash
# Iniciar backend + frontend
.\batch_scripts\start_completo.bat

# Exponer con ngrok
.\batch_scripts\iniciar_con_ngrok.bat

# Sincronizar tasa BCV
.\batch_scripts\sincronizar_bcv.bat

# Enviar recordatorios de pago
.\batch_scripts\enviar_recordatorios.bat

# Cierre mensual contable
.\batch_scripts\cierre_mensual.bat
```

## 📚 Documentación Principal

### Guías de Usuario
- **Flujo de Venta**: `docs_archive/INICIO_RAPIDO.md`
- **Facturación Venezuela**: `docs_archive/CONTABILIDAD_VENEZUELA_VEN_NIF.md`
- **Notificaciones**: `docs_archive/NOTIFICACIONES.md`

### Guías Técnicas
- **APIs REST**: `docs/api/FRONTEND_API_ENDPOINTS.md`
- **Parsers de Boletos**: `docs_archive/PARSERS_AEROLINEAS.md`
- **Auditoría**: `docs_archive/AUDIT.md`
- **Seguridad**: `docs/deployment/SECURITY.md`

### Deployment
- **Ngrok**: `docs/deployment/INSTRUCCIONES_NGROK.md`
- **Red Local**: `docs_archive/COMPARTIR_EN_RED_LOCAL.md`
- **Redis**: `docs_archive/REDIS_SETUP.md`

## 🔧 Características Principales

### CRM
✅ Gestión de Clientes con historial completo  
✅ Gestión de Proveedores (consolidadores, mayoristas)  
✅ Catálogo de Productos/Servicios  
✅ Sistema de Fidelidad (puntos por compras)  

### ERP
✅ Ventas, Facturas y Asientos Contables  
✅ Liquidaciones a Proveedores  
✅ Importación automática de Boletos (KIU, SABRE, AMADEUS)  
✅ Generación de Vouchers  

### Contabilidad VEN-NIF
✅ Dualidad Monetaria (USD/BSD)  
✅ Integración con BCV (tasa automática)  
✅ Provisión INATUR (1% mensual)  
✅ Reportes contables completos  

### Integraciones
✅ Parser Multi-GDS (KIU, SABRE, AMADEUS, Wingo, Copa)  
✅ OCR de Pasaportes (Google Cloud Vision)  
✅ Notificaciones Email + WhatsApp (Twilio)  
✅ Chatbot IA (Google Gemini)  

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov --cov-report=term-missing

# Tests específicos
pytest tests/test_sabre_parser_enhanced.py -v
```

**Cobertura actual**: 71%+ (objetivo: 85%)

## 🔐 Seguridad

- ✅ Autenticación JWT + Token Legacy
- ✅ CORS configurado
- ✅ CSP Headers
- ✅ Rate Limiting por endpoint
- ✅ Auditoría completa de operaciones
- ✅ Encriptación HTTPS en producción

## 📊 CI/CD

Pipeline automático en GitHub Actions:
- Lint con `ruff`
- Tests con `pytest`
- Auditoría de dependencias con `pip-audit`
- Cobertura de código

Ver: `.github/workflows/ci.yml`

## 🛠️ Tecnologías

**Backend**:
- Django 5.x
- Django REST Framework
- PostgreSQL / SQLite
- Redis (cache opcional)

**Frontend**:
- Next.js 14
- TypeScript
- Tailwind CSS
- React Query

**Integraciones**:
- Google Gemini AI
- Google Cloud Vision (OCR)
- Twilio (WhatsApp)
- BCV API (tasas)

## 📞 Soporte

Para más información, consulta la documentación en:
- `docs/` - Documentación técnica actualizada
- `docs_archive/` - Documentación histórica y guías completas

## 📝 Licencia

Proyecto privado - TravelHub © 2025
