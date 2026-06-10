# Guía de Mejores Prácticas - Django Models

## CharFields y TextFields: null=True vs blank=True

### Problema Identificado

Se encontraron 38 CharFields/TextFields con `null=True` en el proyecto. Según las [mejores prácticas de Django](https://docs.djangoproject.com/en/stable/ref/models/fields/#null), para campos de texto se debe evitar usar `null=True`.

### ¿Por qué?

Django almacena cadenas vacías como `''` (cadena vacía) en la base de datos, no como `NULL`. Esto significa que:

1. **Inconsistencia de datos**: Puedes tener tanto `''` como `NULL` representando "sin valor"
2. **Consultas complejas**: Necesitas hacer `Q(campo='') | Q(campo__isnull=True)` en lugar de solo `Q(campo='')`
3. **Validación inconsistente**: Los formularios de Django tratan `''` y `NULL` de manera diferente
4. **Índices ineficientes**: Los índices en campos con NULL son menos eficientes

### Solución Recomendada

**Para nuevos campos:**
```python
# ✅ CORRECTO
nombre = models.CharField(max_length=100, blank=True)
descripcion = models.TextField(blank=True)

# ❌ INCORRECTO
nombre = models.CharField(max_length=100, blank=True, null=True)
descripcion = models.TextField(blank=True, null=True)
```

**Para campos existentes:**

1. **No cambiar inmediatamente** - Puede requerir migraciones masivas
2. **Priorizar campos críticos** - Campos de búsqueda, filtros, etc.
3. **Migración gradual** - Cambiar modelo por modelo

### Script de Migración de Datos

Para migrar datos existentes de NULL a '':

```python
# migration.py
from django.db import migrations

def migrate_null_to_empty(apps, schema_editor):
    Cliente = apps.get_model('crm', 'Cliente')
    Cliente.objects.filter(apellidos__isnull=True).update(apellidos='')
    Cliente.objects.filter(nombre_empresa__isnull=True).update(nombre_empresa='')
    # ... repetir para otros campos

class Migration(migrations.Migration):
    dependencies = [...]
    operations = [
        migrations.RunPython(migrate_null_to_empty),
    ]
```

### Campos Excepción

**Sí usar `null=True` en:**
- `EncryptedCharField` - Campos encriptados pueden necesitar NULL
- `ForeignKey` - Relaciones opcionales
- `DateTimeField` - Fechas opcionales
- Campos numéricos donde 0 tiene significado diferente a NULL

## Row Level Security (RLS)

### Estado Actual

El proyecto usa un sistema de multi-tenancy basado en el campo `agencia` en los modelos. La seguridad se implementa a nivel de aplicación mediante:

1. **Middleware**: `MultiTenantMiddleware` establece el contexto de agencia
2. **Manager personalizado**: `TenantManager` filtra automáticamente por agencia
3. **Mixins**: `TenantMixin` agrega el campo `agencia` a los modelos

### Políticas RLS Faltantes

Para defense-in-depth, se recomienda implementar RLS a nivel de base de datos:

```sql
-- Habilitar RLS en tabla
ALTER TABLE crm_cliente ENABLE ROW LEVEL SECURITY;

-- Crear política
CREATE POLICY agencia_policy ON crm_cliente
    USING (agencia_id = current_setting('app.current_agencia_id')::int);

-- Forzar RLS incluso para el owner de la tabla
ALTER TABLE crm_cliente FORCE ROW LEVEL SECURITY;
```

### Implementación en Django

1. **Configurar variable de sesión en middleware:**
```python
# core/middleware.py
def __call__(self, request):
    if request.user.is_authenticated and hasattr(request, 'agencia'):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL app.current_agencia_id = %s",
                [request.agencia.id]
            )
    return self.get_response(request)
```

2. **Crear migración para habilitar RLS:**
```python
# migrations/0003_enable_rls.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [...]
    
    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE crm_cliente ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE crm_cliente FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY agencia_policy ON crm_cliente
                USING (agencia_id = current_setting('app.current_agencia_id', true)::int);
                """,
            ],
            reverse_sql=[
                "DROP POLICY IF EXISTS agencia_policy ON crm_cliente;",
                "ALTER TABLE crm_cliente DISABLE ROW LEVEL SECURITY;",
            ]
        ),
    ]
```

### Tablas que Necesitan RLS

Prioridad alta (contienen datos sensibles de agencias):
- [ ] `crm_cliente`
- [ ] `crm_pasajero`
- [ ] `bookings_venta`
- [ ] `bookings_boletoimportado`
- [ ] `finance_factura`
- [ ] `contabilidad_asientocontable`

Prioridad media:
- [ ] `cotizaciones_cotizacion`
- [ ] `marketing_campana`
- [ ] `cms_articulo`

### Consideraciones

1. **Superusuarios**: Necesitan bypass de RLS
2. **Comandos de gestión**: `manage.py` no tiene contexto de agencia
3. **Tareas Celery**: Necesitan establecer contexto explícitamente
4. **Tests**: Requieren configuración especial

### Alternativa: Auditoría Automática

En lugar de RLS, implementar auditoría automática de accesos cross-agencia:

```python
# core/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save)
def check_tenant_isolation(sender, instance, **kwargs):
    if hasattr(instance, 'agencia_id') and instance.agencia_id:
        from core.middleware import get_current_agencia
        current_agencia = get_current_agencia()
        if current_agencia and instance.agencia_id != current_agencia.id:
            raise PermissionDenied(
                f"Cross-tenant access detected: "
                f"Current agency {current_agencia.id}, "
                f"Instance agency {instance.agencia_id}"
            )
```

## Índices de Base de Datos

### Índices Agregados

Se crearon índices para campos de búsqueda frecuente en:
- `crm_cliente`: email, nombres+apellidos, telefono_principal
- `crm_pasajero`: nombres+apellidos, documento_hash
- `bookings_venta`: localizador, fecha_venta, estado
- `bookings_boletoimportado`: numero_boleto, fecha_importacion
- `finance_factura`: numero_factura, fecha_emision, estado
- `contabilidad_asientocontable`: numero_asiento, fecha

### Índices Compuestos Recomendados

Para consultas frecuentes con múltiples filtros:

```python
class Meta:
    indexes = [
        models.Index(fields=['agencia', 'fecha_venta', 'estado'], 
                     name='idx_venta_agencia_fecha_estado'),
        models.Index(fields=['agencia', 'cliente', 'fecha_venta'],
                     name='idx_venta_agencia_cliente_fecha'),
    ]
```

### Índices Parciales

Para campos con valores mayoritariamente NULL:

```python
class Meta:
    indexes = [
        models.Index(
            fields=['fecha_cancelacion'],
            name='idx_venta_fecha_cancelacion',
            condition=Q(fecha_cancelacion__isnull=False)
        ),
    ]
```

### Monitoreo de Performance

Usar Django Debug Toolbar o `django-extensions` para identificar queries lentas:

```bash
python manage.py runserver_plus --print-sql
```

Revisar el output para identificar:
- Queries sin índices (aparecen como "Seq Scan")
- Queries con JOINs innecesarios
- Queries N+1

## Checklist de Mejores Prácticas

### Para Nuevos Modelos

- [ ] Usar `blank=True` en lugar de `null=True` para CharField/TextField
- [ ] Agregar `db_index=True` a campos de búsqueda frecuente
- [ ] Agregar índices compuestos para consultas frecuentes
- [ ] Usar `related_name` descriptivo en ForeignKeys
- [ ] Agregar `verbose_name` y `help_text` a todos los campos
- [ ] Implementar `__str__` method
- [ ] Agregar `class Meta` con `ordering` y `verbose_name`

### Para Modelos Existentes

- [ ] Identificar campos con `null=True` innecesario
- [ ] Crear migración de datos para convertir NULL a ''
- [ ] Agregar índices a campos de búsqueda
- [ ] Revisar queries lentas con Django Debug Toolbar
- [ ] Documentar decisiones de diseño en docstrings

## Referencias

- [Django Models Documentation](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Django Multi-tenancy](https://django-tenants.readthedocs.io/)
