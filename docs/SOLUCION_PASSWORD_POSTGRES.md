# Solución: Password de PostgreSQL Incorrecto

## Error Actual
```
FATAL: la autentificación password falló para el usuario "postgres"
```

## Soluciones

### Opción 1: Recordar/Probar Passwords Comunes

Edita `.env` y prueba estos passwords:

```env
DB_PASSWORD=admin
DB_PASSWORD=root
DB_PASSWORD=12345
DB_PASSWORD=password
DB_PASSWORD=Admin123
DB_PASSWORD=Postgres123
```

Después de cada cambio:
```bash
python manage.py check
```

### Opción 2: Resetear Password de PostgreSQL (RECOMENDADO)

#### Paso 1: Editar pg_hba.conf
1. Abre como Administrador:
   ```
   C:\Program Files\PostgreSQL\17\data\pg_hba.conf
   ```

2. Busca estas líneas:
   ```
   # IPv4 local connections:
   host    all             all             127.0.0.1/32            scram-sha-256
   # IPv6 local connections:
   host    all             all             ::1/128                 scram-sha-256
   ```

3. Cámbialas a:
   ```
   # IPv4 local connections:
   host    all             all             127.0.0.1/32            trust
   # IPv6 local connections:
   host    all             all             ::1/128                 trust
   ```

4. Guarda el archivo

#### Paso 2: Reiniciar PostgreSQL
Abre CMD como Administrador:
```cmd
net stop postgresql-x64-17
net start postgresql-x64-17
```

#### Paso 3: Cambiar Password
```cmd
cd "C:\Program Files\PostgreSQL\17\bin"
psql -U postgres -h localhost
```

Dentro de psql:
```sql
ALTER USER postgres WITH PASSWORD 'nuevo_password';
\q
```

#### Paso 4: Revertir pg_hba.conf
1. Vuelve a abrir `pg_hba.conf`
2. Cambia `trust` de vuelta a `scram-sha-256`
3. Guarda

#### Paso 5: Reiniciar PostgreSQL
```cmd
net stop postgresql-x64-17
net start postgresql-x64-17
```

#### Paso 6: Actualizar .env
```env
DB_PASSWORD=nuevo_password
```

### Opción 3: Usar Autenticación de Windows

Si configuraste PostgreSQL con autenticación de Windows:

1. Edita `.env`:
   ```env
   DB_USER=tu_usuario_windows
   DB_PASSWORD=
   ```

2. O crea un usuario específico en PostgreSQL

## Después de Resolver

Una vez que funcione la conexión:

```bash
# Verificar usuarios
python manage.py shell -c "from django.contrib.auth.models import User; print(f'Usuarios: {User.objects.count()}')"

# Listar usuarios
python manage.py shell -c "from django.contrib.auth.models import User; [print(f'{u.username} - {u.email}') for u in User.objects.all()]"

# Acceder con tus credenciales originales
python manage.py runserver
```

## ¿Qué Password Usar?

**Recomendación para desarrollo:**
```env
DB_PASSWORD=postgres123
```

Fácil de recordar y seguro para desarrollo local.
