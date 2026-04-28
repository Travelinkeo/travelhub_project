# Configuración de Redis para Caché (Opcional)

Redis mejora significativamente el rendimiento del dashboard y reportes al cachear respuestas frecuentes.

## Instalación

### Windows
```bash
# Descargar desde https://github.com/microsoftarchive/redis/releases
# O usar WSL:
wsl --install
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

### Linux/macOS
```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis
```

### Docker (Recomendado)
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

## Configuración Django

1. Instalar dependencias:
```bash
pip install redis django-redis
```

2. Agregar a `requirements.txt`:
```
redis==5.0.1
django-redis==5.4.0
```

3. Configurar en `settings.py`:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'travelhub',
        'TIMEOUT': 300,  # 5 minutos default
    }
}

# Session storage en Redis (opcional)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

4. Variables de entorno (`.env`):
```
REDIS_URL=redis://127.0.0.1:6379/1
```

## Uso en Código

### Cachear respuesta de API
```python
from core.cache import cache_api_response

@api_view(['GET'])
@cache_api_response(timeout=600, key_prefix='dashboard')
def dashboard_metricas(request):
    # Esta respuesta se cacheará por 10 minutos
    ...
```

### Invalidar caché manualmente
```python
from core.cache import invalidate_cache_pattern

# Invalidar todo el caché del dashboard
invalidate_cache_pattern('dashboard')

# Invalidar caché de una venta específica
invalidate_cache_pattern(f'venta:{venta_id}')
```

### Uso directo de Django cache
```python
from django.core.cache import cache

# Guardar
cache.set('mi_clave', {'data': 'valor'}, timeout=300)

# Obtener
data = cache.get('mi_clave')

# Eliminar
cache.delete('mi_clave')

# Limpiar todo
cache.clear()
```

## Endpoints que Benefician de Caché

1. **Dashboard de Métricas** - Caché de 5-10 minutos
2. **Reportes Contables** - Caché de 1 hora
3. **Listas de Catálogos** - Caché de 24 horas
4. **Estadísticas de Auditoría** - Caché de 15 minutos

## Monitoreo

### Ver estadísticas de Redis
```bash
redis-cli info stats
```

### Ver claves almacenadas
```bash
redis-cli keys "travelhub:*"
```

### Limpiar caché manualmente
```bash
redis-cli flushdb
```

## Consideraciones

- **Sin Redis**: El sistema funciona normalmente sin caché
- **Desarrollo**: Caché deshabilitado por default en DEBUG=True
- **Producción**: Habilitar caché para mejor rendimiento
- **Memoria**: Redis usa ~50-100MB para caché típico

## Troubleshooting

### Error: "Connection refused"
```bash
# Verificar que Redis esté corriendo
redis-cli ping
# Debe responder: PONG
```

### Limpiar caché corrupto
```python
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### Deshabilitar caché temporalmente
```python
# En settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
```
