# Solución Error 403 - Frontend

## Problema
```
GET http://127.0.0.1:8000/api/cotizaciones/ 403 (Forbidden)
{detail: 'Given token not valid for any token type', code: 'token_not_valid'}
```

## Causa
El token JWT almacenado en el frontend está expirado o es inválido.

## Solución Rápida

### Opción 1: Limpiar LocalStorage y Volver a Iniciar Sesión

1. **Abrir DevTools** (F12)
2. **Ir a Application/Aplicación** → Storage → Local Storage
3. **Eliminar** `access_token` y `refresh_token`
4. **Recargar** la página (F5)
5. **Iniciar sesión** nuevamente con:
   - Usuario: `Armando3105`
   - Password: `Linkeo1331*`

### Opción 2: Desde Consola del Navegador

```javascript
// Abrir consola (F12) y ejecutar:
localStorage.clear();
location.reload();
```

Luego iniciar sesión nuevamente.

## Solución Permanente: Refresh Token Automático

El frontend debe refrescar el token automáticamente. Verifica que tu `useApi.ts` o `AuthContext.tsx` tenga lógica de refresh.

### Código Sugerido para AuthContext

```typescript
// En tu AuthContext.tsx
const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return null;

  try {
    const response = await fetch('http://127.0.0.1:8000/api/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken })
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access);
      return data.access;
    }
  } catch (error) {
    console.error('Error refreshing token:', error);
  }
  
  return null;
};
```

### Interceptor para Fetch

```typescript
// En tu useApi.ts o fetcher
const fetcher = async (url: string) => {
  let token = localStorage.getItem('access_token');
  
  let response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });

  // Si es 403, intentar refresh
  if (response.status === 403) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      // Reintentar con nuevo token
      response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${newToken}`,
          'Content-Type': 'application/json'
        }
      });
    }
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
};
```

## Verificar Backend

### 1. Verificar que JWT esté configurado

```bash
cd C:\Users\ARMANDO\travelhub_project
python manage.py shell
```

```python
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='Armando3105')
refresh = RefreshToken.for_user(user)

print(f"Access: {refresh.access_token}")
print(f"Refresh: {refresh}")
```

### 2. Verificar tiempo de expiración

En `travelhub/settings.py`:

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),  # Aumentar si expira muy rápido
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

## Pasos Inmediatos

1. **Limpiar localStorage**: `localStorage.clear()`
2. **Recargar página**: F5
3. **Iniciar sesión**: Armando3105 / Linkeo1331*
4. **Verificar que funcione**

## Si Persiste el Error

Verifica CORS en backend:

```python
# travelhub/settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True
```

Reinicia el backend:
```bash
python manage.py runserver
```

---

**Solución más rápida**: `localStorage.clear()` + F5 + Login
