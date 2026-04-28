# Recuperar Datos de PostgreSQL

## Problema
Cambiamos a SQLite pero todos tus datos están en PostgreSQL.

## Solución: Volver a PostgreSQL

### Paso 1: Configurar Password de PostgreSQL

Necesitas saber el password de tu usuario `postgres`. Opciones comunes:
- `postgres` (default)
- El password que configuraste al instalar
- Vacío (sin password)

### Paso 2: Actualizar .env

Ya actualicé el archivo `.env` con:
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=TravelHub
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

**Si tu password es diferente**, edita `.env` y cambia `DB_PASSWORD`.

### Paso 3: Verificar Servicio PostgreSQL

Abre "Servicios" de Windows y verifica que esté corriendo:
- Nombre: `postgresql-x64-17` (o similar)
- Estado: Iniciado

O desde CMD como administrador:
```cmd
net start postgresql-x64-17
```

### Paso 4: Probar Conexión

```bash
python manage.py check
```

Si hay error de autenticación, prueba estos passwords comunes:
1. `postgres`
2. `admin`
3. `root`
4. Tu password de Windows

### Paso 5: Verificar Base de Datos

```bash
python manage.py showmigrations
```

Si ves `[X]` en todas las migraciones, tus datos están ahí.

### Paso 6: Acceder con tus Credenciales Originales

Una vez conectado a PostgreSQL, usa tus credenciales originales para acceder.

## Alternativa: Resetear Password de PostgreSQL

Si no recuerdas el password:

1. Abre `C:\Program Files\PostgreSQL\17\data\pg_hba.conf`
2. Cambia la línea:
   ```
   host    all             all             127.0.0.1/32            scram-sha-256
   ```
   Por:
   ```
   host    all             all             127.0.0.1/32            trust
   ```
3. Reinicia el servicio PostgreSQL
4. Conecta sin password y cambia el password:
   ```sql
   ALTER USER postgres WITH PASSWORD 'nuevo_password';
   ```
5. Revierte el cambio en pg_hba.conf
6. Reinicia el servicio

## Passwords Comunes a Probar

Edita `.env` y prueba estos passwords uno por uno:

```env
DB_PASSWORD=postgres
DB_PASSWORD=admin
DB_PASSWORD=root
DB_PASSWORD=12345
DB_PASSWORD=password
DB_PASSWORD=
```

Después de cada cambio, ejecuta:
```bash
python manage.py check
```

## ¿Necesitas Ayuda?

Dime cuál es el error exacto que recibes al ejecutar:
```bash
python manage.py check
```

Y te ayudaré a resolverlo.
