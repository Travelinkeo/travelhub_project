# Diagnóstico: Problema con Creación de Ventas de Hotel

## Posibles Causas del Problema

### 1. **Estructura de Datos Incorrecta**
El frontend podría estar enviando datos en un formato que no coincide con lo que espera el serializer.

**Solución:**
- Verificar que la estructura JSON coincida con el ejemplo en `ejemplo_venta_hotel.json`
- Asegurar que todos los campos requeridos estén presentes

### 2. **IDs de Catálogos Inexistentes**
Los IDs de cliente, moneda, producto, ciudad o proveedor podrían no existir en la base de datos.

**Solución:**
- Ejecutar el script `test_hotel_api.py` para verificar qué catálogos están disponibles
- Crear los registros faltantes en el admin de Django

### 3. **Problemas de Autenticación**
El frontend podría no estar enviando el token de autenticación correctamente.

**Solución:**
- Verificar que el header `Authorization: Token <tu_token>` esté presente
- Comprobar que el token sea válido

### 4. **Errores de Validación**
Los datos podrían no pasar las validaciones del modelo o serializer.

**Solución:**
- Revisar los errores específicos en la respuesta de la API
- Verificar que las fechas estén en formato correcto (ISO 8601)
- Asegurar que los montos sean números válidos

### 5. **Problemas de CORS**
Si el frontend está en un puerto diferente, podría haber problemas de CORS.

**Solución:**
- Verificar la configuración de CORS en `settings.py`
- Asegurar que `localhost:3000` esté en `CORS_ALLOWED_ORIGINS`

## Pasos para Diagnosticar

### Paso 1: Verificar Catálogos
```bash
python test_hotel_api.py
```

### Paso 2: Probar desde Postman/Insomnia
Usar la estructura del archivo `ejemplo_venta_hotel.json` para hacer una petición manual.

### Paso 3: Revisar Logs del Backend
```bash
python manage.py runserver
# Revisar la consola para errores
```

### Paso 4: Verificar en el Admin
1. Ir a `http://localhost:8000/admin/`
2. Verificar que existan:
   - Clientes
   - Monedas
   - Productos/Servicios (tipo Hotel)
   - Ciudades
   - Proveedores

## Estructura Mínima Requerida

### Para crear una venta básica:
```json
{
  "cliente": 1,
  "moneda": 1,
  "items_venta": [
    {
      "producto_servicio": 1,
      "precio_unitario_venta": 100.00
    }
  ]
}
```

### Para crear con alojamiento:
```json
{
  "cliente": 1,
  "moneda": 1,
  "items_venta": [
    {
      "producto_servicio": 1,
      "precio_unitario_venta": 100.00,
      "alojamiento_details": {
        "nombre_establecimiento": "Hotel Test",
        "ciudad": 1
      }
    }
  ]
}
```

## Comandos Útiles para Debugging

### Crear datos de prueba:
```bash
python manage.py shell
```

```python
from personas.models import Cliente
from core.models_catalogos import Moneda, ProductoServicio, Ciudad, Pais, Proveedor

# Crear cliente de prueba
cliente = Cliente.objects.create(
    nombres="Juan",
    apellidos="Pérez",
    email="juan@test.com"
)

# Crear moneda si no existe
moneda, _ = Moneda.objects.get_or_create(
    codigo_iso="USD",
    defaults={"nombre": "Dólar Americano", "simbolo": "$"}
)

# Crear producto hotel
producto = ProductoServicio.objects.create(
    nombre="Alojamiento Hotel",
    tipo_producto="HOT",
    activo=True
)

# Crear país y ciudad
pais, _ = Pais.objects.get_or_create(
    codigo_iso_2="VE",
    defaults={"nombre": "Venezuela", "codigo_iso_3": "VEN"}
)

ciudad = Ciudad.objects.create(
    nombre="Caracas",
    pais=pais,
    region_estado="Distrito Capital"
)

# Crear proveedor
proveedor = Proveedor.objects.create(
    nombre="Hotel Marriott",
    contacto_email="reservas@marriott.com"
)
```

## Verificación Final

Una vez solucionado el problema, deberías poder:

1. ✅ Crear una venta desde el frontend
2. ✅ Ver la venta en el admin de Django
3. ✅ Ver el alojamiento asociado en la venta
4. ✅ Recibir una respuesta 201 Created de la API

## Contacto para Soporte

Si el problema persiste después de seguir estos pasos, proporciona:
1. El JSON exacto que está enviando el frontend
2. La respuesta completa de la API (incluyendo código de estado)
3. Los logs del servidor Django
4. Capturas de pantalla del error en el frontend