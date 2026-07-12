# Guía de Resolución de Imports Circulares

## Estado Actual del Proyecto

El proyecto TravelHub **no tiene errores de imports circulares** gracias al uso de imports locales (dentro de funciones/métodos). Esta es una solución válida y aceptada en Django.

## Patrones Identificados

### 1. Imports Locales en Métodos/Properties (Patrón Actual)

```python
# ✅ CORRECTO - Import local dentro de método
class Factura(models.Model):
    @property
    def venta_asociada(self):
        from apps.bookings.models import Venta  # Import local
        return Venta.objects.filter(pk=self.venta_asociada_id).first()
```

**Ventajas:**
- Evita imports circulares al momento de cargar módulos
- Simple de implementar
- No requiere cambios en la arquitectura

**Desventajas:**
- Overhead de performance (import se ejecuta cada vez que se llama el método)
- Puede ser difícil de rastrear dependencias
- No es explícito en la API del módulo

### 2. String References en ForeignKeys (Patrón Actual)

```python
# ✅ CORRECTO - Referencia como string
class Factura(models.Model):
    cliente = models.ForeignKey(
        'crm.Cliente',  # String reference
        on_delete=models.PROTECT
    )
```

**Ventajas:**
- Django resuelve la referencia en runtime
- Evita imports circulares a nivel de módulo
- Es el patrón recomendado por Django

### 3. apps.get_model() (Alternativa Recomendada)

```python
# ✅ RECOMENDADO - Usar apps.get_model()
from django.apps import apps

class Factura(models.Model):
    @property
    def venta_asociada(self):
        Venta = apps.get_model('bookings', 'Venta')
        return Venta.objects.filter(pk=self.venta_asociada_id).first()
```

**Ventajas:**
- Más explícito que imports locales
- Mejor performance (Django cachea los modelos)
- Fácil de rastrear dependencias
- Patrón oficial de Django para evitar imports circulares

## Casos de Uso Específicos

### Caso 1: Properties que Referencian Otros Modelos

**Antes (Import Local):**
```python
class Factura(models.Model):
    @property
    def venta_asociada(self):
        from apps.bookings.models import Venta
        return Venta.objects.filter(pk=self.venta_asociada_id).first()
```

**Después (apps.get_model):**
```python
from django.apps import apps

class Factura(models.Model):
    @property
    def venta_asociada(self):
        Venta = apps.get_model('bookings', 'Venta')
        return Venta.objects.filter(pk=self.venta_asociada_id).first()
```

### Caso 2: Signals que Referencian Otros Modelos

**Antes (Import Local):**
```python
# finance/signals.py
from django.db.models.signals import post_save

@receiver(post_save, sender='finance.Factura')
def factura_saved(sender, instance, **kwargs):
    from apps.bookings.models import Venta
    # ... lógica
```

**Después (apps.get_model):**
```python
from django.apps import apps
from django.db.models.signals import post_save

@receiver(post_save, sender='finance.Factura')
def factura_saved(sender, instance, **kwargs):
    Venta = apps.get_model('bookings', 'Venta')
    # ... lógica
```

### Caso 3: Tasks de Celery

**Antes (Import Local):**
```python
# finance/tasks.py
@shared_task
def procesar_factura(factura_id):
    from apps.bookings.models import Venta
    # ... lógica
```

**Después (Import en el nivel del task):**
```python
# finance/tasks.py
from celery import shared_task

@shared_task
def procesar_factura(factura_id):
    from django.apps import apps
    Venta = apps.get_model('bookings', 'Venta')
    # ... lógica
```

### Caso 4: Serializers que Referencian Otros Modelos

**Antes (Import Local):**
```python
# finance/serializers.py
class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

    def to_representation(self, instance):
        from apps.bookings.models import Venta
        data = super().to_representation(instance)
        # ... lógica
        return data
```

**Después (Import al inicio del método):**
```python
from django.apps import apps

class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

    def to_representation(self, instance):
        Venta = apps.get_model('bookings', 'Venta')
        data = super().to_representation(instance)
        # ... lógica
        return data
```

## Arquitectura de Dependencias

### Diagrama de Dependencias Actual

```
common (base)
    ↓
core (auth, multi-tenant)
    ↓
crm (clientes, pasajeros)
    ↓
bookings (ventas, boletos)
    ↓
finance (facturas, pagos)
    ↓
contabilidad (asientos, tasas)
    ↓
cotizaciones (cotizaciones)
    ↓
automation (parsers, IA)
    ↓
communications (email, WhatsApp)
    ↓
marketing (campañas)
    ↓
cms (contenido)
```

### Reglas de Dependencia

1. **Apps de base** (`common`, `core`) NO deben importar de apps de negocio
2. **Apps de negocio** pueden importar de apps de base
3. **Apps del mismo nivel** deben usar imports locales o `apps.get_model()`
4. **Apps de mayor nivel** pueden importar de apps de menor nivel

## Refactorización Recomendada

### Prioridad Alta (Imports en Properties Frecuentes)

Archivos a refactorizar:
- [ ] `apps/finance/models/facturacion.py` - `venta_asociada` property
- [ ] `apps/finance/models/core_finance.py` - `venta_asociada` property
- [ ] `apps/cotizaciones/models.py` - imports de `Venta`
- [ ] `apps/bookings/models/venta.py` - imports de `Factura`

### Prioridad Media (Imports en Tasks)

Archivos a refactorizar:
- [ ] `apps/bookings/tasks.py` - múltiples imports de modelos
- [ ] `apps/finance/tasks.py` - imports de `Venta`, `BoletoImportado`
- [ ] `apps/automation/tasks.py` - imports de `BoletoImportado`

### Prioridad Baja (Imports en Views/Services)

Archivos a refactorizar:
- [ ] `apps/cotizaciones/views.py` - imports de `TasaCambioBCV`
- [ ] `apps/finance/services/*.py` - varios imports locales
- [ ] `apps/bookings/services/*.py` - varios imports locales

## Script de Refactorización Automática

```python
#!/usr/bin/env python
"""
Script para refactorizar imports locales a apps.get_model()
Uso: python scripts/refactor_imports.py
"""
import re
from pathlib import Path

def refactor_file(file_path):
    content = file_path.read_text()

    # Patrón: from apps.X.models import Y (dentro de funciones)
    pattern = r'(\s+)from apps\.(\w+)\.models import (\w+)'

    def replace(match):
        indent = match.group(1)
        app_name = match.group(2)
        model_name = match.group(3)
        return f"{indent}{model_name} = apps.get_model('{app_name}', '{model_name}')"

    new_content = re.sub(pattern, replace, content)

    # Agregar import de apps si no existe
    if 'from django.apps import apps' not in new_content:
        # Buscar el último import de Django
        django_import_pattern = r'(from django\.[^\n]+\n)'
        matches = list(re.finditer(django_import_pattern, new_content))
        if matches:
            last_match = matches[-1]
            insert_pos = last_match.end()
            new_content = (
                new_content[:insert_pos] +
                'from django.apps import apps\n' +
                new_content[insert_pos:]
            )

    if new_content != content:
        file_path.write_text(new_content)
        print(f"Refactored: {file_path}")

# Ejecutar en todos los archivos Python
for py_file in Path('apps').rglob('*.py'):
    refactor_file(py_file)
```

## Mejores Prácticas

### ✅ Hacer

1. **Usar `apps.get_model()`** para imports dinámicos de modelos
2. **Usar string references** en ForeignKeys (`'app.Model'`)
3. **Importar al inicio de funciones** si `apps.get_model()` no es posible
4. **Documentar dependencias** en el docstring del módulo
5. **Seguir la arquitectura de dependencias** (base → negocio → especialización)

### ❌ No Hacer

1. **No usar imports circulares** a nivel de módulo
2. **No importar modelos** en `__init__.py` de apps
3. **No crear dependencias bidireccionales** entre apps del mismo nivel
4. **No usar `import *`** nunca
5. **No ignorar errores de import** con `try/except ImportError`

## Herramientas de Detección

### Django Extensions

```bash
pip install django-extensions
python manage.py graph_models -a -g -o dependencies.png
```

### Importanize

```bash
pip install importanize
importanize .
```

### Ruff (Linter)

```bash
pip install ruff
ruff check . --select I
```

## Testing

Después de refactorizar, verificar que no hay imports circulares:

```bash
python manage.py check
python manage.py shell -c "from django.apps import apps; print([m.__name__ for m in apps.get_models()])"
```

## Referencias

- [Django Documentation: Applications](https://docs.djangoproject.com/en/stable/ref/applications/)
- [Django Documentation: Models](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [Two Scoops of Django: Best Practices](https://www.feldroy.com/books/two-scoops-of-django-3-x)
- [Django Packages: Circular Imports](https://djangopackages.org/grids/g/circular-imports/)
