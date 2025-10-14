# Parsers de Aerolíneas - TravelHub

Este documento describe la estructura de parsers para sistemas propietarios de aerolíneas.

## Sistemas Implementados

### ✅ TK Connect (Turkish Airlines)
- **Archivo Parser**: `core/tk_connect_parser.py`
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_tk_connect.html`
- **Detección**: "IDENTIFICACIÓN DEL PEDIDO" o "GRUPO SOPORTE GLOBAL"
- **Estado**: Completamente funcional

### 🔄 COPA SPRK (Copa Airlines)
- **Archivo Parser**: `core/copa_sprk_parser.py`
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_copa_sprk.html`
- **Detección**: "COPA AIRLINES" + "SPRK"
- **Estado**: Estructura creada, pendiente implementación con boleto real

### 🔄 WINGO (Wingo Airlines)
- **Archivo Parser**: `core/wingo_parser.py`
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_wingo.html`
- **Detección**: "WINGO" o "WINGO.COM"
- **Estado**: Estructura creada, pendiente implementación con boleto real

## Estructura de Datos Normalizada

Todos los parsers deben retornar un diccionario con la siguiente estructura:

```python
{
    'SOURCE_SYSTEM': 'NOMBRE_SISTEMA',  # TK_CONNECT, COPA_SPRK, WINGO
    'pnr': 'ABC123',
    'fecha_creacion': '10 oct, 2025',
    'numero_boleto': '2352239449735',
    'pasajero': {
        'nombre_completo': 'APELLIDO/NOMBRE',
        'documento': 'V12345678',
        'telefono': '+584123312314',
        'email': 'email@example.com'
    },
    'vuelos': [
        {
            'numero_vuelo': 'CM123',
            'origen': 'Caracas (CCS)',
            'destino': 'Panama (PTY)',
            'fecha_salida': '23 mar, lun.',
            'hora_salida': '14:30',
            'fecha_llegada': '24 mar, mar.',
            'hora_llegada': '09:20',
            'clase_reserva': 'Y',
            'cabina': 'ECONOMY'
        }
    ],
    'equipaje': {
        'facturado': '2 piezas',
        'cabina': '1 pieza x 8 kg'
    }
}
```

## Plantillas PDF

Todas las plantillas usan el diseño corporativo de Travelinkeo:
- **Header**: Color #232b38 con logo de Travelinkeo
- **Footer**: Información de contacto de la agencia
- **Estructura**: Idéntica entre todas las aerolíneas
- **Colores**: Títulos y textos importantes en #232b38

## Cómo Agregar un Nuevo Parser

1. **Crear archivo parser**: `core/[nombre]_parser.py`
   ```python
   def parse_[nombre]_ticket(text):
       data = {
           'SOURCE_SYSTEM': 'NOMBRE_SISTEMA',
           # ... extraer datos del texto
       }
       return data
   ```

2. **Copiar plantilla base**:
   ```bash
   copy core\templates\core\tickets\ticket_template_tk_connect.html core\templates\core\tickets\ticket_template_[nombre].html
   ```

3. **Agregar detección en `ticket_parser.py`**:
   ```python
   if 'PALABRA_CLAVE' in plain_text_upper:
       from .[nombre]_parser import parse_[nombre]_ticket
       return parse_[nombre]_ticket(plain_text)
   ```

4. **Agregar generación de PDF en `ticket_parser.py`** (función `generate_ticket`):
   ```python
   elif source_system == 'NOMBRE_SISTEMA':
       template_name = "ticket_template_[nombre].html"
       context = { ... }
   ```

## Integración con Boletos Importados

El sistema detecta automáticamente el tipo de boleto al subirlo en "Boletos Importados" y:
1. Aplica el parser correspondiente
2. Extrae todos los datos
3. Genera el PDF con la plantilla de Travelinkeo
4. Crea la venta automáticamente

## Notas Importantes

- Todos los parsers deben manejar errores gracefully
- Siempre retornar 'N/A' para campos no encontrados
- Mantener la estructura de datos consistente
- Las plantillas PDF deben ser idénticas en diseño, solo cambiar el nombre de la aerolínea
