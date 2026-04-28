# Opciones de Despliegue para TravelHub - Económico/Gratuito

**Fecha**: 21 de Enero de 2025  
**Objetivo**: Desplegar TravelHub en producción con costo mínimo o gratuito

---

## 🏆 Opción Recomendada: Railway.app

### ✅ Por qué Railway

- **Gratis**: $5 USD de crédito mensual (suficiente para empezar)
- **PostgreSQL incluido**: Base de datos gratis
- **Redis incluido**: Cache gratis
- **Deploy automático**: Conecta GitHub y despliega automáticamente
- **SSL gratis**: HTTPS automático
- **Fácil**: Sin configuración compleja
- **Escalable**: Cuando crezcas, solo pagas lo que usas

### 📦 Recursos Incluidos (Plan Gratuito)

```
Backend Django:    512 MB RAM, 1 vCPU
PostgreSQL:        1 GB storage
Redis:             100 MB
Bandwidth:         100 GB/mes
```

### 🚀 Pasos para Desplegar

1. **Crear cuenta en Railway.app**
   - https://railway.app
   - Login con GitHub

2. **Crear nuevo proyecto**
   - "New Project" → "Deploy from GitHub repo"
   - Seleccionar `travelhub_project`

3. **Agregar servicios**
   ```
   + Add Service → PostgreSQL
   + Add Service → Redis
   ```

4. **Configurar variables de entorno**
   ```env
   DEBUG=False
   SECRET_KEY=<generar_nueva_clave_50_caracteres>
   ALLOWED_HOSTS=*.railway.app
   
   # PostgreSQL (Railway las genera automáticamente)
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   
   # Redis (Railway las genera automáticamente)
   REDIS_URL=${{Redis.REDIS_URL}}
   
   # Gemini API
   GEMINI_API_KEY=<tu_clave>
   
   # Email
   EMAIL_HOST_USER=<tu_email>
   EMAIL_HOST_PASSWORD=<tu_password>
   
   # WhatsApp (opcional)
   TWILIO_ACCOUNT_SID=<tu_sid>
   TWILIO_AUTH_TOKEN=<tu_token>
   ```

5. **Crear `railway.json`** (en raíz del proyecto)
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn travelhub.wsgi:application",
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 10
     }
   }
   ```

6. **Deploy automático**
   - Railway detecta Django automáticamente
   - Instala dependencias de `requirements.txt`
   - Ejecuta migraciones
   - Inicia con Gunicorn

### 💰 Costos Estimados

| Usuarios/Mes | Costo Mensual | Notas |
|--------------|---------------|-------|
| 0-100 | **$0** | Plan gratuito suficiente |
| 100-500 | **$5-10** | Upgrade a plan Hobby |
| 500-2000 | **$20-30** | Plan Pro |

---

## 🥈 Opción 2: Render.com

### ✅ Ventajas

- **Gratis**: Plan gratuito permanente
- **PostgreSQL gratis**: 1 GB storage
- **SSL gratis**: HTTPS automático
- **Deploy automático**: GitHub integration
- **Sin tarjeta de crédito**: Para empezar

### ⚠️ Limitaciones

- **Sleep después de 15 min inactividad** (plan gratuito)
- **750 horas/mes** de uptime gratis
- **Arranque lento** después de sleep (~30 segundos)

### 🚀 Pasos para Desplegar

1. **Crear cuenta en Render.com**
   - https://render.com
   - Login con GitHub

2. **Crear Web Service**
   - "New" → "Web Service"
   - Conectar repositorio GitHub
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn travelhub.wsgi:application`

3. **Crear PostgreSQL**
   - "New" → "PostgreSQL"
   - Plan: Free
   - Copiar `DATABASE_URL`

4. **Configurar variables de entorno**
   - Igual que Railway
   - Agregar `DATABASE_URL` manualmente

### 💰 Costos

- **Gratis**: Suficiente para demos y pruebas
- **$7/mes**: Plan Starter (sin sleep, mejor performance)

---

## 🥉 Opción 3: Fly.io

### ✅ Ventajas

- **Gratis**: 3 VMs pequeñas gratis
- **PostgreSQL gratis**: 3 GB storage
- **Global**: Deploy en múltiples regiones
- **Sin sleep**: Siempre activo

### ⚠️ Limitaciones

- **Requiere tarjeta de crédito** (no cobra si no excedes límites)
- **Configuración más técnica**: Requiere Dockerfile

### 🚀 Pasos para Desplegar

1. **Instalar Fly CLI**
   ```bash
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

2. **Login y crear app**
   ```bash
   fly auth login
   fly launch
   ```

3. **Crear PostgreSQL**
   ```bash
   fly postgres create
   fly postgres attach <postgres-app-name>
   ```

4. **Deploy**
   ```bash
   fly deploy
   ```

### 💰 Costos

- **Gratis**: 3 VMs + 3 GB PostgreSQL
- **$1.94/mes**: Por VM adicional

---

## 🎯 Comparación Rápida

| Característica | Railway | Render | Fly.io |
|----------------|---------|--------|--------|
| **Precio inicial** | 💰 Gratis ($5 crédito) | 💰 Gratis | 💰 Gratis |
| **PostgreSQL** | ✅ Incluido | ✅ Incluido | ✅ Incluido |
| **Redis** | ✅ Incluido | ❌ Pago | ✅ Incluido |
| **Sleep** | ❌ No | ⚠️ Sí (plan gratis) | ❌ No |
| **SSL/HTTPS** | ✅ Automático | ✅ Automático | ✅ Automático |
| **Deploy automático** | ✅ GitHub | ✅ GitHub | ⚠️ CLI |
| **Facilidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Tarjeta requerida** | ❌ No | ❌ No | ⚠️ Sí |

---

## 🏅 Recomendación Final

### Para Empezar (0-3 meses)
**Railway.app** - Más fácil, incluye todo, $5 gratis

### Para Demos/Pruebas
**Render.com** - Gratis permanente, acepta sleep

### Para Producción Seria
**Railway.app** o **Fly.io** - Sin sleep, mejor performance

---

## 📋 Checklist Pre-Deploy

### 1. Preparar el Proyecto

```bash
# Crear requirements.txt optimizado
pip freeze > requirements.txt

# Crear Procfile (para Render/Railway)
echo "web: gunicorn travelhub.wsgi:application" > Procfile

# Crear runtime.txt
echo "python-3.13" > runtime.txt
```

### 2. Configurar Settings para Producción

```python
# travelhub/settings.py

# Usar DATABASE_URL de Railway/Render
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600
    )
}

# Whitenoise para archivos estáticos
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← Importante
    ...
]

# Configurar ALLOWED_HOSTS
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
```

### 3. Instalar Dependencias Adicionales

```bash
pip install gunicorn dj-database-url psycopg2-binary whitenoise
pip freeze > requirements.txt
```

### 4. Crear `.env.production` (ejemplo)

```env
DEBUG=False
SECRET_KEY=<generar_nueva_clave_segura>
ALLOWED_HOSTS=*.railway.app,*.render.com
DATABASE_URL=<proporcionado_por_plataforma>
REDIS_URL=<proporcionado_por_plataforma>
```

---

## 🚀 Deploy en Railway (Paso a Paso)

### 1. Preparar Repositorio

```bash
# Commit todos los cambios
git add .
git commit -m "Preparar para deploy en Railway"
git push origin main
```

### 2. Crear Proyecto en Railway

1. Ir a https://railway.app
2. "New Project" → "Deploy from GitHub repo"
3. Seleccionar `travelhub_project`
4. Railway detecta Django automáticamente

### 3. Agregar PostgreSQL

1. En el proyecto, click "New"
2. "Database" → "Add PostgreSQL"
3. Railway crea `DATABASE_URL` automáticamente

### 4. Agregar Redis

1. Click "New" → "Database" → "Add Redis"
2. Railway crea `REDIS_URL` automáticamente

### 5. Configurar Variables de Entorno

En "Variables" del servicio Django:

```env
DEBUG=False
SECRET_KEY=<generar_con: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'>
ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}}
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
GEMINI_API_KEY=<tu_clave>
```

### 6. Deploy

- Railway despliega automáticamente
- Monitorea logs en tiempo real
- Obtén URL pública: `https://tu-app.railway.app`

### 7. Ejecutar Migraciones (primera vez)

```bash
# En Railway CLI o desde el dashboard
railway run python manage.py migrate
railway run python manage.py createsuperuser
railway run python manage.py load_catalogs
```

---

## 🎓 Frontend (Next.js)

### Opción 1: Vercel (Recomendado)

- **Gratis**: Plan Hobby gratuito
- **Deploy automático**: GitHub integration
- **SSL gratis**: HTTPS automático
- **CDN global**: Ultra rápido

```bash
# En carpeta frontend/
npm install -g vercel
vercel login
vercel
```

### Opción 2: Netlify

- Similar a Vercel
- También gratis
- Drag & drop deploy

---

## 💡 Tips para Reducir Costos

1. **Usar plan gratuito de Railway** hasta tener usuarios reales
2. **Optimizar queries** para reducir uso de CPU/RAM
3. **Usar cache Redis** para reducir queries a PostgreSQL
4. **Comprimir imágenes** antes de subir
5. **Lazy loading** en frontend
6. **Monitorear uso** en dashboard de Railway

---

## 📊 Estimación de Costos por Etapa

### Fase 1: MVP/Demo (0-3 meses)
- **Railway**: $0 (plan gratuito)
- **Vercel**: $0 (plan gratuito)
- **Total**: **$0/mes**

### Fase 2: Primeros Clientes (3-6 meses)
- **Railway**: $5-10/mes
- **Vercel**: $0
- **Total**: **$5-10/mes**

### Fase 3: Crecimiento (6-12 meses)
- **Railway**: $20-30/mes
- **Vercel**: $20/mes (Pro)
- **Total**: **$40-50/mes**

---

## 🆘 Soporte y Recursos

### Railway
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app

### Render
- Docs: https://render.com/docs
- Community: https://community.render.com

### Fly.io
- Docs: https://fly.io/docs
- Community: https://community.fly.io

---

**Última actualización**: 21 de Enero de 2025  
**Recomendación**: Railway.app para empezar  
**Autor**: Amazon Q Developer
