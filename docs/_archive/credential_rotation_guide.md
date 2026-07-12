# Guía de Rotación de Credenciales - TravelHub

## Resumen de Auditoría de Seguridad

**Fecha:** 2026-06-08
**Auditor:** Sistema de Auditoría Automatizada
**Hallazgo:** Archivo `frontend/.env.production` fue commiteado históricamente (commits: 53eaf1e, 5887059, 75d6647)

## Estado Actual

✅ **Archivos .env de backend NUNCA fueron commiteados** (verificado con `git log`)
⚠️ **Archivo frontend/.env.production SÍ fue commiteado** (3 commits históricos)
✅ **Archivos .env actuales están en .gitignore** y NO están trackeados

## Acciones Requeridas

### 1. Rotación de Credenciales (PRIORIDAD CRÍTICA)

Todas las credenciales que alguna vez estuvieron en `frontend/.env.production` deben considerarse **COMPROMETIDAS** y deben ser rotadas inmediatamente.

#### Checklist de Rotación

- [ ] **GitHub Tokens** (si existen en frontend/.env.production)
  - Ir a: GitHub → Settings → Developer settings → Personal access tokens
  - Revocar tokens antiguos
  - Generar nuevos tokens
  - Actualizar en `.env.production` (NO commitear)

- [ ] **API Keys de Frontend** (Vercel, etc.)
  - Ir a: Vercel Dashboard → Settings → Environment Variables
  - Rotar todas las variables sensibles
  - Actualizar en `.env.production` (NO commitear)

- [ ] **Stripe Keys** (si existen en frontend)
  - Ir a: Stripe Dashboard → Developers → API keys
  - Rotar Publishable Key y Secret Key
  - Actualizar webhooks si es necesario
  - Actualizar en `.env.production` (NO commitear)

- [ ] **Cloudinary/Cloudflare Keys** (si existen en frontend)
  - Ir a: Cloudinary Dashboard → Settings → API Keys
  - Rotar API Key y API Secret
  - Actualizar en `.env.production` (NO commitear)

- [ ] **Google Analytics/Tag Manager** (si existen)
  - Ir a: Google Analytics → Admin → Property Settings
  - Rotar Measurement ID si es necesario
  - Actualizar en `.env.production` (NO commitear)

### 2. Saneamiento del Historial Git (PRIORIDAD ALTA)

**ADVERTENCIA:** Esto reescribirá el historial de Git. Todos los desarrolladores deberán clonar el repositorio nuevamente.

#### Opción A: Usar BFG Repo-Cleaner (Recomendado)

```bash
# 1. Instalar BFG (si no está instalado)
# Windows: Descargar desde https://rtyley.github.io/bfg-repo-cleaner/
# O con Scoop: scoop install bfg

# 2. Clonar el repositorio en modo espejo
git clone --mirror https://github.com/tu-usuario/travelhub_project.git
cd travelhub_project.git

# 3. Eliminar el archivo del historial
bfg --delete-files frontend/.env.production

# 4. Limpiar y forzar push
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force --all
git push --force --tags

# 5. Notificar a todos los desarrolladores que deben re-clonar
```

#### Opción B: Usar git-filter-repo

```bash
# 1. Instalar git-filter-repo
pip install git-filter-repo

# 2. Eliminar el archivo del historial
git filter-repo --path frontend/.env.production --invert-paths

# 3. Forzar push
git push --force --all
git push --force --tags
```

### 3. Verificación Post-Rotación

Después de rotar credenciales y limpiar el historial:

```bash
# Verificar que el archivo ya no existe en ningún commit
git log --all --full-history -- frontend/.env.production
# Debería retornar vacío

# Verificar que no hay credenciales en el historial
git log -p --all | grep -i "password\|secret\|api_key\|token"
# Revisar manualmente los resultados

# Verificar que .env está en .gitignore
cat .gitignore | grep -E "^\.env"
# Debería mostrar: .env, .env.production, .env.local, etc.
```

### 4. Prevención Futura

#### Pre-commit Hook para detectar secrets

Crear archivo `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

Instalar:
```bash
pip install pre-commit detect-secrets
pre-commit install
```

#### Variables de Entorno en Desarrollo

Para desarrollo local, usar un archivo `.env.example` sin valores reales:

```bash
# .env.example (SAFE TO COMMIT)
DATABASE_URL=postgresql://user:password@localhost:5432/travelhub
SECRET_KEY=your-secret-key-here
STRIPE_SECRET_KEY=sk_test_your_test_key_here
```

Cada desarrollador debe crear su propio `.env` local (NUNCA commitear).

## Credenciales Específicas del Backend

Aunque los archivos `.env` del backend NUNCA fueron commiteados, por precaución se recomienda rotar:

### Base de Datos
- [ ] PostgreSQL password (en `DB_PASSWORD`)
- [ ] Redis password (si se configura, ver acción 1-2)

### APIs Externas
- [ ] Gemini API Key (`GEMINI_API_KEY`)
- [ ] Stripe Secret Key (`STRIPE_SECRET_KEY`)
- [ ] Telegram Bot Token (`TELEGRAM_BOT_TOKEN`)
- [ ] Twilio Auth Token (`TWILIO_AUTH_TOKEN`)
- [ ] Resend API Key (`RESEND_API_KEY`)
- [ ] Cloudinary API Secret (`CLOUDINARY_API_SECRET`)
- [ ] Cloudflare R2 Secret Key (`R2_SECRET_ACCESS_KEY`)
- [ ] Binance API Secret (si existe)

### Django
- [ ] Django Secret Key (`SECRET_KEY`)
- [ ] Encryption Key (`ENCRYPTION_KEY`)

### Servicios de Terceros
- [ ] Amadeus API Secret (si existe)
- [ ] Unsplash Secret Key (si existe)
- [ ] Google Cloud credentials (si existen)

## Procedimiento de Rotación

Para cada credencial:

1. **Generar nueva credencial** en el dashboard del proveedor
2. **Actualizar en `.env.production`** del servidor de producción
3. **Actualizar en `.env`** del entorno de desarrollo local
4. **Reiniciar servicios** afectados:
   ```bash
   docker-compose restart web celery_worker celery_beat
   ```
5. **Verificar funcionamiento** de la funcionalidad afectada
6. **Marcar como completado** en el checklist de arriba

## Timeline Sugerido

- **Día 1:** Rotar todas las credenciales del frontend (las que estuvieron en git)
- **Día 2:** Saneamiento del historial git con BFG
- **Día 3:** Rotación preventiva de credenciales del backend
- **Día 4:** Verificación y testing
- **Día 5:** Implementación de pre-commit hooks y documentación

## Contacto

Si encuentras problemas durante la rotación:
- Revisar logs de la aplicación: `docker-compose logs web`
- Verificar que las variables de entorno estén cargadas: `docker-compose exec web env | grep -E "SECRET|KEY|TOKEN"`
- Consultar documentación del proveedor para rotación de credenciales

---

**NOTA IMPORTANTE:** Después de completar este proceso, marca la tarea 1-1 como completada en el plan de auditoría.
