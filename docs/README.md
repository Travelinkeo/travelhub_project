# 📚 Documentación TravelHub

## 🎯 Acceso Rápido

- **🚀 [Inicio Rápido](guides/INICIO_RAPIDO.md)** - Empieza aquí
- **📋 [Índice Completo](INDEX.md)** - Toda la documentación
- **🔌 [API Endpoints](api/FRONTEND_API_ENDPOINTS.md)** - Referencia de API
- **🎨 [Funcionalidades Frontend](frontend/NUEVAS_FUNCIONALIDADES_FRONTEND.md)** - Guía del frontend

---

## 📂 Estructura

```
docs/
├── README.md (este archivo)
├── INDEX.md (índice completo)
│
├── guides/           # Guías de usuario
│   ├── INICIO_RAPIDO.md
│   ├── README.md
│   └── CONTRIBUTING.md
│
├── api/              # Documentación de APIs
│   ├── FRONTEND_API_ENDPOINTS.md
│   ├── FRONTEND_INTEGRATION_EXAMPLES.md
│   ├── FRONTEND_API_GUIDE.md
│   ├── RESUMEN_IMPLEMENTACION_FRONTEND_API.md
│   └── MEJORAS_IMPLEMENTADAS.md
│
├── frontend/         # Documentación del frontend
│   ├── NUEVAS_FUNCIONALIDADES_FRONTEND.md
│   ├── URLS_DIRECTAS.md
│   ├── TABLA_FUNCIONALIDADES.md
│   ├── RESUMEN_IMPLEMENTACION_COMPLETA.md
│   └── FRONTEND_AIRLINES_INTEGRATION.md
│
├── backend/          # Documentación del backend
│   ├── CONTABILIDAD_VENEZUELA_VEN_NIF.md
│   ├── AUDIT.md
│   ├── NOTIFICACIONES.md
│   ├── REPORTES_CONTABLES.md
│   ├── REDIS_SETUP.md
│   ├── PARSERS_AEROLINEAS.md
│   └── AEROLINEAS_INTEGRATION_SUMMARY.md
│
└── deployment/       # Deployment y configuración
    ├── INSTRUCCIONES_NGROK.md
    ├── COMPARTIR_EN_RED_LOCAL.md
    ├── CIERRE_MENSUAL.md
    └── SECURITY.md
```

---

## 🚀 Para Empezar

### 1. Instalación
```bash
# Clonar repositorio
git clone <repo>

# Instalar dependencias backend
pip install -r requirements.txt

# Instalar dependencias frontend
cd frontend
npm install
```

### 2. Configuración
```bash
# Copiar variables de entorno
cp .env.example .env

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

### 3. Iniciar
```bash
# Backend
python manage.py runserver

# Frontend (en otra terminal)
cd frontend
npm run dev
```

### 4. Acceder
- Frontend: http://localhost:3000
- Backend Admin: http://localhost:8000/admin
- API Docs: http://localhost:8000/api/docs

---

## 📖 Documentación por Rol

### 👨‍💻 Desarrolladores
1. [Inicio Rápido](guides/INICIO_RAPIDO.md)
2. [API Endpoints](api/FRONTEND_API_ENDPOINTS.md)
3. [Ejemplos de Integración](api/FRONTEND_INTEGRATION_EXAMPLES.md)
4. [Guía de Contribución](guides/CONTRIBUTING.md)

### 👥 Usuarios
1. [Inicio Rápido](guides/INICIO_RAPIDO.md)
2. [Funcionalidades](frontend/NUEVAS_FUNCIONALIDADES_FRONTEND.md)
3. [URLs Directas](frontend/URLS_DIRECTAS.md)

### 🔧 DevOps
1. [Deployment con ngrok](deployment/INSTRUCCIONES_NGROK.md)
2. [Seguridad](deployment/SECURITY.md)
3. [Redis Setup](backend/REDIS_SETUP.md)

### 💼 Contadores
1. [Sistema Contable VEN-NIF](backend/CONTABILIDAD_VENEZUELA_VEN_NIF.md)
2. [Reportes Contables](backend/REPORTES_CONTABLES.md)
3. [Cierre Mensual](deployment/CIERRE_MENSUAL.md)

---

## ✨ Funcionalidades Principales

### Dashboard
- Métricas en tiempo real
- Alertas automáticas
- Top clientes
- Ventas por estado

### Gestión Financiera
- Liquidaciones a proveedores
- Pagos parciales y totales
- Generación de vouchers
- Reportes contables

### Automatización
- OCR de pasaportes
- Parseo de boletos
- Creación automática de clientes
- Notificaciones multicanal

### Auditoría
- Timeline de ventas
- Logs de cambios
- Estadísticas de auditoría
- Trazabilidad completa

---

## 🔗 Enlaces Útiles

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Admin Django**: http://localhost:8000/admin/
- **Frontend**: http://localhost:3000/

---

## 📊 Estado del Proyecto

| Componente | Estado | Cobertura |
|------------|--------|-----------|
| Backend | ✅ 100% | Tests: 71% |
| Frontend | ✅ 95% | En desarrollo |
| API | ✅ 100% | Documentada |
| Deployment | ✅ 100% | Configurado |

---

## 🆘 Soporte

¿Necesitas ayuda?

1. Consulta el [Índice](INDEX.md)
2. Revisa [Inicio Rápido](guides/INICIO_RAPIDO.md)
3. Busca en [API Endpoints](api/FRONTEND_API_ENDPOINTS.md)

---

**Versión**: 2.0  
**Última actualización**: Enero 2025
