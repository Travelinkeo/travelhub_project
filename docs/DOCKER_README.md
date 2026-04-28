# TravelHub - Docker Setup

## Inicio Rápido

```bash
# 1. Clonar y configurar
git clone https://github.com/Travelinkeo/travelhub_project.git
cd travelhub_project
cp .env.example .env

# 2. Editar .env con tus credenciales
# DB_PASSWORD, SECRET_KEY, etc.

# 3. Iniciar con Docker
docker-compose up -d

# 4. Ejecutar migraciones
docker-compose exec web python manage.py migrate

# 5. Cargar catálogos
docker-compose exec web python manage.py load_catalogs

# 6. Crear superusuario
docker-compose exec web python manage.py createsuperuser

# 7. Acceder
# http://localhost:8000/admin/
```

## Comandos Útiles

```bash
# Ver logs
docker-compose logs -f web

# Reiniciar servicios
docker-compose restart

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v

# Ejecutar comando en contenedor
docker-compose exec web python manage.py <comando>

# Acceder a shell de Django
docker-compose exec web python manage.py shell

# Acceder a PostgreSQL
docker-compose exec db psql -U postgres -d TravelHub
```

## Producción

```bash
# Build optimizado
docker build -t travelhub:latest .

# Run con variables de entorno
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name travelhub \
  travelhub:latest

# Con PostgreSQL externo
docker run -d \
  -p 8000:8000 \
  -e DB_HOST=your-db-host \
  -e DB_PASSWORD=your-password \
  -e SECRET_KEY=your-secret \
  travelhub:latest
```

## Troubleshooting

### Puerto 8000 ocupado
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Cambiar puerto
docker-compose up -d
# Editar docker-compose.yml: "8001:8000"
```

### Base de datos no conecta
```bash
# Verificar que PostgreSQL esté corriendo
docker-compose ps

# Ver logs de DB
docker-compose logs db

# Recrear contenedor
docker-compose down
docker-compose up -d
```

### Permisos en Windows
```bash
# Ejecutar Docker Desktop como administrador
# O agregar usuario a grupo docker-users
```
