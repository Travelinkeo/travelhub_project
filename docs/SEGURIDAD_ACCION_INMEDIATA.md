# 🔴 ACCIÓN INMEDIATA DE SEGURIDAD - TRAVELHUB

## ⚠️ CAMBIOS CRÍTICOS IMPLEMENTADOS

Se han realizado cambios de seguridad críticos que **REQUIEREN ACCIÓN INMEDIATA** antes de ejecutar el proyecto.

---

## 📋 CHECKLIST DE ACCIÓN (OBLIGATORIO)

### ✅ Paso 1: Crear archivo .env (5 minutos)

```bash
# Copiar el archivo de ejemplo
copy .env.example .env
```

### ✅ Paso 2: Configurar variables de entorno en .env

Edita el archivo `.env` y configura:

```env
# 1. SECRET_KEY (OBLIGATORIO - mínimo 50 caracteres)
# Genera una nueva con:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=tu-secret-key-generada-aqui-minimo-50-caracteres

# 2. Contraseña de Base de Datos (OBLIGATORIO)
DB_PASSWORD=Linkeo1331*

# 3. Otras configuraciones de BD
DB_NAME=TravelHub
DB_USER=postgres
DB_HOST=localhost
DB_PORT=5432

# 4. Debug (cambiar a False en producción)
DEBUG=True
```

### ✅ Paso 3: Generar SECRET_KEY segura

```bash
# Ejecutar en terminal:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Copiar el resultado y pegarlo en .env como SECRET_KEY
```

### ✅ Paso 4: Verificar que .env NO esté en Git

```bash
# Verificar que .env está ignorado
git status

# Si aparece .env, ejecutar:
git rm --cached .env
git commit -m "Remove .env from repository"
```

### ✅ Paso 5: Proteger credenciales GCP (si aplica)

```bash
# Si tienes credenciales GCP, asegúrate de que estén fuera del repo
# El archivo auth/*.json ya está en .gitignore

# Verificar:
git status auth/

# Si aparece, ejecutar:
git rm --cached auth/*.json
git commit -m "Remove GCP credentials from repository"
```

---

## 🚨 ERRORES QUE VERÁS SI NO CONFIGURAS

### Error 1: SECRET_KEY no configurada
```
RuntimeError: SECRET_KEY no está configurada en el entorno.
Por favor, configúrala en tu archivo .env con al menos 50 caracteres.
```

**Solución**: Sigue el Paso 2 y 3 arriba.

---

### Error 2: DB_PASSWORD no configurada
```
RuntimeError: DB_PASSWORD no está configurada.
Por favor, configúrala en tu archivo .env
```

**Solución**: Agrega `DB_PASSWORD=Linkeo1331*` en tu archivo .env

---

### Error 3: SECRET_KEY muy corta (solo en producción)
```
RuntimeError: SECRET_KEY debe tener al menos 50 caracteres en producción.
```

**Solución**: Genera una nueva SECRET_KEY con el comando del Paso 3.

---

## 🔒 CAMBIOS DE SEGURIDAD IMPLEMENTADOS

### 1. Credenciales Movidas a Variables de Entorno ✅
- ❌ ANTES: Contraseña hardcodeada en `settings.py`
- ✅ AHORA: Contraseña en `.env` (no versionado)

### 2. Validación de SECRET_KEY ✅
- ✅ Valida que exista
- ✅ Valida longitud mínima (50 caracteres en producción)

### 3. Endpoints Protegidos ✅
- ✅ `/api/facturas/` → Requiere autenticación
- ✅ `/api/ventas/` → Requiere autenticación
- ✅ `/api/boletos-importados/` → Requiere autenticación
- ✅ `/api/proveedores/` → Requiere autenticación
- ✅ `/api/paises/` → Solo lectura pública, escritura requiere auth
- ✅ `/api/ciudades/` → Solo lectura pública, escritura requiere auth
- ✅ `/api/monedas/` → Solo lectura pública, escritura requiere auth

### 4. .gitignore Mejorado ✅
- ✅ `.env` y variantes ignoradas
- ✅ `auth/*.json` ignorado
- ✅ Credenciales protegidas

---

## 🔐 AUTENTICACIÓN EN APIs

### Para Frontend/Aplicaciones Externas

Ahora necesitas autenticarte para acceder a los endpoints protegidos:

#### Opción 1: JWT (Recomendado)
```javascript
// 1. Obtener token
const response = await fetch('http://localhost:8000/api/auth/jwt/obtain/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'tu_usuario',
    password: 'tu_contraseña'
  })
});

const { access, refresh } = await response.json();

// 2. Usar token en requests
const ventas = await fetch('http://localhost:8000/api/ventas/', {
  headers: {
    'Authorization': `Bearer ${access}`
  }
});
```

#### Opción 2: Session Authentication (Django Admin)
```python
# Ya autenticado en Django Admin, las requests funcionan automáticamente
```

---

## 📝 PRÓXIMOS PASOS RECOMENDADOS

### Esta Semana:
1. ✅ Configurar .env (HECHO)
2. ⏳ Rotar credenciales GCP si estaban en el repo
3. ⏳ Revisar logs de acceso para detectar accesos no autorizados
4. ⏳ Actualizar frontend para usar autenticación JWT

### Este Mes:
1. ⏳ Implementar rate limiting en todos los endpoints
2. ⏳ Configurar HTTPS en producción
3. ⏳ Implementar monitoreo de seguridad (Sentry)
4. ⏳ Auditoría completa de permisos

---

## 🆘 SOPORTE

Si tienes problemas:

1. **Verifica que .env existe**: `dir .env`
2. **Verifica contenido de .env**: Abre el archivo y confirma que tiene SECRET_KEY y DB_PASSWORD
3. **Regenera SECRET_KEY**: Usa el comando del Paso 3
4. **Consulta logs**: `python manage.py runserver` mostrará el error específico

---

## ✅ VERIFICACIÓN FINAL

Antes de continuar, verifica:

- [ ] Archivo `.env` creado y configurado
- [ ] SECRET_KEY generada (50+ caracteres)
- [ ] DB_PASSWORD configurada
- [ ] `.env` NO aparece en `git status`
- [ ] Servidor Django inicia sin errores: `python manage.py runserver`

---

**Fecha de implementación**: Enero 2025  
**Prioridad**: 🔴 CRÍTICA  
**Estado**: ✅ IMPLEMENTADO - REQUIERE CONFIGURACIÓN
