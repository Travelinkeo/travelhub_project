# Seguridad en TravelHub

Este documento describe las medidas de seguridad implementadas en TravelHub, el estado actual de protección y las recomendaciones para mantener el sistema seguro.

> **Nota para personal no técnico:** La seguridad es el conjunto de medidas que protegen los datos de los viajeros, las agencias y la empresa. Piensa en esto como las "cerraduras, alarmas y vigilancia" de la aplicación.

---

## Índice

1. [Estado actual de seguridad](#1-estado-actual-de-seguridad)
2. [Autenticación y control de acceso](#2-autenticación-y-control-de-acceso)
3. [Protección de datos](#3-protección-de-datos)
4. [Cabeceras de seguridad HTTP](#4-cabeceras-de-seguridad-http)
5. [Hash Chain de auditoría](#5-hash-chain-de-auditoría)
6. [Seguridad en frontend](#6-seguridad-en-frontend)
7. [Buenas prácticas](#7-buenas-prácticas)
8. [Riesgos identificados y hoja de ruta](#8-riesgos-identificados-y-hoja-de-ruta)
9. [Checklist de seguridad](#9-checklist-de-seguridad)

---

## 1. Estado Actual de Seguridad

### Implementado

- **Autenticación:** Sesión Django + JWT (access/refresh rotativos, logout con blacklist)
- **Permisos:** CRUD protegido por permisos a nivel de objeto (ventas por `creado_por`)
- **Auditoría:** Cada cambio queda registrado con IP, User-Agent, y hash chain (SHA-256)
- **CORS:** Restrictivo, solo dominios autorizados
- **Throttling:** Límite de peticiones por usuario y por IP
- **Rate limit en login:** Protege contra ataques de fuerza bruta
- **Cabeceras de seguridad:** CSP enforce, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy
- **HTTPS forzado:** En producción, todas las conexiones son cifradas

### Pendiente

- Escaneo de dependencias en CI (pytest + coverage + pip-audit)
- Antivirus para archivos subidos (ClamAV)
- Logging estructurado en JSON con limpieza de datos personales
- Redis multi-instancia (actualmente un solo Redis para todo)

---

## 2. Autenticación y Control de Acceso

### Tipos de autenticación

| Método | ¿Cuándo se usa? |
|--------|-----------------|
| Sesión Django | Navegador web (dashboard, admin) |
| JWT (JSON Web Token) | API REST (consumida por sistemas externos) |
| Magic Link | Enlace mágico por correo (login sin contraseña) |

### Control de acceso por roles

- **Staff:** Acceso completo al panel de administración y base de conocimiento
- **Agencias (tenants):** Acceso solo a sus propios datos (ventas, clientes, reportes)
- **Usuarios:** Acceso según permisos asignados por su agencia

### Protección contra fuerza bruta

El sistema limita automáticamente los intentos de inicio de sesión desde una misma IP. Superado el límite, la IP queda temporalmente bloqueada.

---

## 3. Protección de Datos

### Datos cifrados

- **Campos sensibles:** Cifrados con Fernet (clave `ENCRYPTION_KEY`) en la base de datos
- **Contraseñas:** Almacenadas con hash (nunca en texto plano)
- **Tráfico:** Todo cifrado con TLS/SSL (HTTPS) en producción

### Base de datos

- Cifrado en reposo (PostgreSQL)
- Conexiones a través de PgBouncer (pool de conexiones)
- Backups automáticos diarios con 7 días de retención

---

## 4. Cabeceras de Seguridad HTTP

TravelHub envía las siguientes cabeceras en todas las respuestas HTTP:

| Cabecera | ¿Qué hace? |
|----------|------------|
| `Content-Security-Policy` | Controla qué scripts y estilos puede cargar el navegador |
| `X-Content-Type-Options: nosniff` | Evita que el navegador "adivine" el tipo de archivo |
| `X-Frame-Options: DENY` | Evita que la página se muestre en un iframe (clickjacking) |
| `Referrer-Policy: strict-origin-when-cross-origin` | Controla qué información se envía al hacer clic en enlaces |
| `Permissions-Policy` | Controla qué APIs del navegador pueden usarse (cámara, micrófono, etc.) |

### Content Security Policy (CSP)

La política CSP usa `nonce` (número de uso único) para scripts, lo que significa que solo los scripts que llevan un nonce válido pueden ejecutarse. Esto bloquea ataques de inyección de scripts (XSS).

---

## 5. Hash Chain de Auditoría

TravelHub registra cada operación importante (crear, modificar, eliminar) en un registro de auditoría encadenado criptográficamente:

- Cada registro contiene un hash del registro anterior (`previous_hash`)
- Se calcula un `record_hash` como SHA-256 de los datos del registro
- Si alguien modifica un registro histórico, la cadena se rompe y el sistema lo detecta

### Verificar integridad

```bash
python manage.py verify_audit_chain
```

Este comando recorre toda la cadena de auditoría y reporta si encuentra alguna manipulación.

---

## 6. Seguridad en Frontend

- **CSP enforce con nonce:** Sin `unsafe-inline` en scripts
- **Sin atributos `style=` en plantillas:** Todas las pruebas verifican que no hay estilos en línea
- **Nonce en DOM:** Verificado automáticamente contra la cabecera CSP

---

## 7. Buenas Prácticas

### Para desarrolladores

- Nunca subir secretos al repositorio (usar `.env`)
- No hardcodear contraseñas en scripts
- Revisar código enfocándose en: inyección SQL, exposición de datos, asignación masiva
- Ejecutar tests antes de cada commit

### Para administradores

- Configurar firewall (UFW) para permitir solo puertos 80, 443 y SSH
- Habilitar actualizaciones automáticas de seguridad
- Monitorear logs con Sentry
- Rotar credenciales periódicamente

### Gestión de superusuarios

```bash
# Crear superusuario (método seguro, sin contraseñas en comandos)
python manage.py createsuperuser

# Resetear contraseña (usa el script seguro)
python scripts/reset_password.py
```

Nunca uses scripts con contraseñas hardcodeadas. Las credenciales no deben vivir en el repositorio.

---

## 8. Riesgos Identificados y Hoja de Ruta

### Riesgos actuales

| ID | Riesgo | Severidad | Estado |
|----|--------|-----------|--------|
| R01 | Redis único para caché + sesiones + Celery | Crítico | Pendiente de dividir |
| R02 | PostgreSQL sin réplicas ni HA | Crítico | Pendiente |
| R03 | Sin deep healthchecks | Alto | Pendiente |
| R04 | Celery Beat sin alta disponibilidad | Alto | Pendiente |
| R05 | Sin CDN para archivos multimedia | Medio | Pendiente |
| R06 | Logs no estructurados | Medio | Pendiente |

### Hoja de ruta

**Corto plazo:**
- [ ] Tests automatizados en CI (pytest + coverage + pip-audit)
- [ ] Antivirus para archivos subidos
- [ ] Deep healthchecks (DB, Redis, Celery)
- [ ] Split de Redis en instancias separadas

**Medio plazo:**
- [ ] Logging estructurado JSON con limpieza de datos personales
- [ ] Cluster de PostgreSQL con Patroni
- [ ] RedBeat para alta disponibilidad de Celery Beat
- [ ] Métricas Prometheus + alertas

---

## 9. Checklist de Seguridad

- [x] CORS restrictivo
- [x] Throttling en API
- [x] Rate limit en login
- [x] Cabeceras de seguridad HTTP
- [x] HTTPS forzado en producción
- [x] Permisos a nivel de objeto
- [x] IP + User-Agent en registro de auditoría
- [x] JWT con refresh rotativo + logout
- [x] CSP enforce con nonce (sin unsafe-inline)
- [x] Hash chain de auditoría con verificación
- [ ] Escaneo de dependencias en CI
- [ ] Antivirus en subida de archivos
- [ ] Logging estructurado
- [ ] Redis multi-instancia
- [ ] PostgreSQL con alta disponibilidad
