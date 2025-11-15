# 🤖 Configuración de Auto Shutdown/Startup en Railway

## 📋 Pasos para Configurar

### 1. Obtener Railway Token

Ejecuta en tu terminal:
```bash
railway whoami --token
```

Copia el token (empieza con `railway_...`)

### 2. Obtener IDs de los Servicios

Ve a Railway Dashboard y copia los IDs de cada servicio:

**Opción A: Desde la URL del servicio**
- Web: `https://railway.app/project/[PROJECT_ID]/service/[SERVICE_ID]`
- Worker: `https://railway.app/project/[PROJECT_ID]/service/[SERVICE_ID]`
- Beat: `https://railway.app/project/[PROJECT_ID]/service/[SERVICE_ID]`

**Opción B: Desde Railway CLI**
```bash
railway service list
```

### 3. Agregar Secrets en GitHub

1. Ve a tu repositorio: https://github.com/Travelinkeo/travelhub_project
2. Click en `Settings` (arriba derecha)
3. En el menú izquierdo: `Secrets and variables` → `Actions`
4. Click en `New repository secret`
5. Agrega estos 4 secrets:

| Name | Value |
|------|-------|
| `RAILWAY_TOKEN` | El token de `railway whoami --token` |
| `RAILWAY_SERVICE_WEB` | ID del servicio web |
| `RAILWAY_SERVICE_WORKER` | ID del servicio worker |
| `RAILWAY_SERVICE_BEAT` | ID del servicio beat |

### 4. Commit y Push

```bash
git add .github/workflows/railway_schedule.yml
git add RAILWAY_AUTO_SHUTDOWN_SETUP.md
git commit -m "Add: Auto shutdown/startup Railway (11 PM - 7 AM)"
git push origin master
```

### 5. Verificar en GitHub

1. Ve a tu repo → `Actions`
2. Deberías ver el workflow "Railway Auto Shutdown/Startup"
3. Puedes ejecutarlo manualmente con "Run workflow"

## ⏰ Horarios Configurados

- 🌙 **11:00 PM** (Venezuela): Apaga servicios
- ☀️ **7:00 AM** (Venezuela): Enciende servicios

## 💰 Ahorro Estimado

- **Antes**: $38.76/mes (24/7)
- **Después**: $25.84/mes (16 horas/día)
- **Ahorro**: $12.92/mes (33%)

## 🔧 Comandos Manuales

Si necesitas apagar/encender manualmente:

```bash
# Apagar
railway service --service [SERVICE_ID] down

# Encender
railway service --service [SERVICE_ID] up
```

## ⚠️ Notas Importantes

1. Los correos que lleguen entre 11 PM - 7 AM se procesarán a las 7 AM
2. La base de datos PostgreSQL sigue corriendo (no se puede apagar)
3. GitHub Actions es gratis (2000 minutos/mes)
4. Puedes cambiar los horarios editando el archivo `.github/workflows/railway_schedule.yml`

## 🐛 Troubleshooting

**Si no funciona:**
1. Verifica que los secrets estén bien configurados
2. Revisa los logs en GitHub Actions
3. Asegúrate de que el token de Railway sea válido
4. Verifica que los IDs de servicios sean correctos

**Para probar manualmente:**
1. Ve a GitHub → Actions
2. Selecciona "Railway Auto Shutdown/Startup"
3. Click "Run workflow"
4. Elige "stop" o "start"
