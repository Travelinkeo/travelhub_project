# Guía de Autenticación JWT - TravelHub

## Cambio Implementado: Token Legacy → JWT

**Fecha**: 21 de Enero de 2025  
**Motivo**: Mayor seguridad - tokens que expiran automáticamente

---

## 🔐 Configuración JWT

### Duración de Tokens

```python
# travelhub/settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': 30 minutos,    # Token de acceso
    'REFRESH_TOKEN_LIFETIME': 7 días,       # Token de refresco
    'ROTATE_REFRESH_TOKENS': True,          # Rotar en cada uso
    'BLACKLIST_AFTER_ROTATION': True,       # Invalidar tokens viejos
}
```

### Prioridad de Autenticación

1. **JWT** (Prioridad 1) - Para APIs y frontend
2. **Session** (Prioridad 2) - Para Django Admin
3. **Token Legacy** (Prioridad 3) - Deprecado, solo compatibilidad

---

## 📱 Implementación en Frontend

### 1. Login y Obtener Tokens

```javascript
// POST /api/auth/login/
const login = async (username, password) => {
  const response = await fetch('/api/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  
  const data = await response.json();
  
  // Respuesta:
  // {
  //   "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  //   "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  //   "user": {
  //     "id": 1,
  //     "username": "admin",
  //     "email": "admin@travelhub.com",
  //     "first_name": "Admin",
  //     "last_name": "User"
  //   }
  // }
  
  // Guardar tokens
  localStorage.setItem('accessToken', data.access);
  localStorage.setItem('refreshToken', data.refresh);
  localStorage.setItem('user', JSON.stringify(data.user));
  
  return data;
};
```

### 2. Usar Access Token en Requests

```javascript
// Función helper para agregar autenticación
const fetchWithAuth = async (url, options = {}) => {
  const accessToken = localStorage.getItem('accessToken');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  
  return fetch(url, {
    ...options,
    headers,
  });
};

// Ejemplo de uso
const crearBoleto = async (boletoData) => {
  const response = await fetchWithAuth('/api/boletos-importados/', {
    method: 'POST',
    body: JSON.stringify(boletoData)
  });
  
  return response.json();
};
```

### 3. Refrescar Access Token Automáticamente

```javascript
// POST /api/token/refresh/
const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refreshToken');
  
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }
  
  const response = await fetch('/api/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken })
  });
  
  if (!response.ok) {
    // Refresh token expirado o inválido - logout
    localStorage.clear();
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  
  const data = await response.json();
  
  // Guardar nuevo access token
  localStorage.setItem('accessToken', data.access);
  
  // Si hay nuevo refresh token (ROTATE_REFRESH_TOKENS=True)
  if (data.refresh) {
    localStorage.setItem('refreshToken', data.refresh);
  }
  
  return data.access;
};
```

### 4. Interceptor para Refrescar Automáticamente

```javascript
// Interceptor que refresca el token si expira
const fetchWithAuthAndRefresh = async (url, options = {}) => {
  let response = await fetchWithAuth(url, options);
  
  // Si el token expiró (401), refrescar y reintentar
  if (response.status === 401) {
    try {
      await refreshAccessToken();
      // Reintentar request con nuevo token
      response = await fetchWithAuth(url, options);
    } catch (error) {
      // Refresh falló - redirigir a login
      localStorage.clear();
      window.location.href = '/login';
      throw error;
    }
  }
  
  return response;
};
```

### 5. Logout

```javascript
const logout = async () => {
  const refreshToken = localStorage.getItem('refreshToken');
  
  // Opcional: Blacklist del refresh token en el servidor
  if (refreshToken) {
    try {
      await fetch('/api/token/blacklist/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken })
      });
    } catch (error) {
      console.error('Error blacklisting token:', error);
    }
  }
  
  // Limpiar storage
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
  
  // Redirigir a login
  window.location.href = '/login';
};
```

---

## 🔄 Flujo Completo

```
1. Usuario hace login
   ↓
2. Backend devuelve access + refresh tokens
   ↓
3. Frontend guarda tokens en localStorage
   ↓
4. Cada request incluye: Authorization: Bearer <access_token>
   ↓
5. Si access token expira (30 min):
   - Frontend usa refresh token para obtener nuevo access token
   - Reintenta el request original
   ↓
6. Si refresh token expira (7 días):
   - Usuario debe hacer login nuevamente
```

---

## 📋 Endpoints JWT

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/auth/login/` | POST | Login y obtener tokens |
| `/api/token/refresh/` | POST | Refrescar access token |
| `/api/token/blacklist/` | POST | Invalidar refresh token (logout) |
| `/api/token/verify/` | POST | Verificar si token es válido |

---

## 🛡️ Ventajas de JWT vs Token Legacy

| Característica | JWT | Token Legacy |
|----------------|-----|--------------|
| **Expiración** | ✅ Automática (30 min) | ❌ Nunca expira |
| **Seguridad** | ✅ Alta | ⚠️ Media |
| **Rotación** | ✅ Sí | ❌ No |
| **Blacklist** | ✅ Sí | ❌ No |
| **Información** | ✅ Incluye datos del usuario | ❌ Solo ID |
| **Stateless** | ✅ Sí | ❌ No (requiere BD) |

---

## ⚙️ Configuración Personalizada (.env)

```env
# Duración de tokens JWT (opcional)
JWT_ACCESS_MINUTES=30        # Access token: 30 minutos (default)
JWT_REFRESH_DAYS=7           # Refresh token: 7 días (default)
JWT_ALGORITHM=HS256          # Algoritmo de firma (default)

# Para producción, usar clave diferente a SECRET_KEY
JWT_SIGNING_KEY=tu_clave_jwt_super_secreta_aqui
```

---

## 🔍 Debugging

### Verificar Token en el Backend

```python
from rest_framework_simplejwt.tokens import AccessToken

token_string = "eyJ0eXAiOiJKV1QiLCJhbGc..."
token = AccessToken(token_string)

print(f"User ID: {token['user_id']}")
print(f"Expires: {token['exp']}")
print(f"Token Type: {token['token_type']}")
```

### Decodificar Token en el Frontend

```javascript
// Decodificar JWT (sin verificar firma)
const decodeJWT = (token) => {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const jsonPayload = decodeURIComponent(
    atob(base64).split('').map(c => 
      '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
    ).join('')
  );
  return JSON.parse(jsonPayload);
};

const accessToken = localStorage.getItem('accessToken');
const payload = decodeJWT(accessToken);
console.log('Token expira:', new Date(payload.exp * 1000));
console.log('User ID:', payload.user_id);
```

---

## 🚨 Migración desde Token Legacy

Si ya tienes código usando Token Authentication:

### Antes (Token Legacy)
```javascript
headers: {
  'Authorization': 'Token abc123...'
}
```

### Después (JWT)
```javascript
headers: {
  'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...'
}
```

**Cambios necesarios**:
1. Cambiar `Token` → `Bearer`
2. Implementar lógica de refresh
3. Manejar expiración de tokens

---

## 📝 Notas Importantes

1. **Access Token**: Guardar en memoria o localStorage (más conveniente)
2. **Refresh Token**: Guardar en localStorage o httpOnly cookie (más seguro)
3. **Expiración**: El frontend debe refrescar el access token antes de que expire
4. **Logout**: Siempre blacklist el refresh token para invalidarlo
5. **HTTPS**: En producción, usar HTTPS para proteger los tokens en tránsito

---

**Última actualización**: 21 de Enero de 2025  
**Estado**: ✅ Implementado y funcional  
**Autor**: Amazon Q Developer
