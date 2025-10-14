# API del Traductor de Itinerarios

Esta documentación describe las APIs disponibles para el traductor de itinerarios de TravelHub.

## Autenticación

Todas las APIs requieren autenticación JWT. Incluye el token en el header:
```
Authorization: Bearer <tu_jwt_token>
```

## Endpoints Disponibles

### 1. Traducir Itinerario

**POST** `/api/translator/itinerary/`

Traduce un itinerario de formato GDS a formato legible.

**Request Body:**
```json
{
    "itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200",
    "gds_system": "SABRE"
}
```

**Response:**
```json
{
    "success": true,
    "translated_itinerary": "<div class=\"flight-result\">...</div>",
    "gds_system": "SABRE",
    "original_itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200"
}
```

**Sistemas GDS Soportados:**
- `SABRE`
- `AMADEUS`
- `KIU`

### 2. Calcular Precio de Boleto

**POST** `/api/translator/calculate/`

Calcula el precio final de un boleto basado en tarifas y fees.

**Request Body:**
```json
{
    "tarifa": 100.0,
    "fee_consolidador": 25.0,
    "fee_interno": 15.0,
    "porcentaje": 10.0
}
```

**Response:**
```json
{
    "success": true,
    "calculation": {
        "tarifa": 100.0,
        "fee_consolidador": 25.0,
        "fee_interno": 15.0,
        "suma_base": 140.0,
        "porcentaje": 10.0,
        "monto_porcentaje": 14.0,
        "precio_final": 154.0,
        "desglose": "Tarifa: $100.00 + Fee Consolidador: $25.00 + Fee Interno: $15.00 = $140.00 + 10% ($14.00) = $154.00"
    }
}
```

### 3. Obtener Sistemas GDS Soportados

**GET** `/api/translator/gds/`

Obtiene la lista de sistemas GDS soportados.

**Response:**
```json
{
    "success": true,
    "supported_gds": [
        {
            "code": "SABRE",
            "name": "Sabre",
            "description": "Sistema de reservas Sabre"
        },
        {
            "code": "AMADEUS",
            "name": "Amadeus",
            "description": "Sistema de reservas Amadeus"
        },
        {
            "code": "KIU",
            "name": "KIU",
            "description": "Sistema de reservas KIU"
        }
    ]
}
```

### 4. Obtener Catálogo de Aerolíneas

**GET** `/api/translator/airlines/`

Obtiene el catálogo de aerolíneas activas.

**Response:**
```json
{
    "success": true,
    "airlines": [
        {
            "code": "AA",
            "name": "American Airlines",
            "country": "Estados Unidos"
        },
        {
            "code": "UA",
            "name": "United Airlines",
            "country": "Estados Unidos"
        }
    ],
    "total": 2
}
```

### 5. Obtener Catálogo de Aeropuertos

**GET** `/api/translator/airports/`

Obtiene el catálogo de aeropuertos disponibles.

**Response:**
```json
{
    "success": true,
    "airports": [
        {
            "code": "MIA",
            "name": "Miami"
        },
        {
            "code": "BOG",
            "name": "Bogotá"
        }
    ],
    "total": 2
}
```

### 6. Validar Formato de Itinerario

**POST** `/api/translator/validate/`

Valida el formato de un itinerario sin traducirlo.

**Request Body:**
```json
{
    "itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200\n2 UA 5678 16JAN W BOGMIA 1400 1800",
    "gds_system": "SABRE"
}
```

**Response:**
```json
{
    "success": true,
    "gds_system": "SABRE",
    "validation": {
        "is_valid": true,
        "total_lines": 2,
        "valid_lines": 2,
        "invalid_lines": [],
        "warnings": []
    }
}
```

**Response (con errores):**
```json
{
    "success": true,
    "gds_system": "SABRE",
    "validation": {
        "is_valid": false,
        "total_lines": 2,
        "valid_lines": 1,
        "invalid_lines": [
            {
                "line_number": 2,
                "content": "formato incorrecto",
                "reason": "No coincide con el formato esperado para SABRE"
            }
        ],
        "warnings": [
            "1 líneas tienen formato incorrecto"
        ]
    }
}
```

### 7. Traducción en Lote

**POST** `/api/translator/batch/`

Traduce múltiples itinerarios en una sola petición (máximo 10).

**Request Body:**
```json
{
    "itineraries": [
        {
            "id": "flight_1",
            "itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200",
            "gds_system": "SABRE"
        },
        {
            "id": "flight_2",
            "itinerary": "2 UA 5678 16JAN W BOGMIA 1400 1800",
            "gds_system": "SABRE"
        }
    ]
}
```

**Response:**
```json
{
    "success": true,
    "summary": {
        "total": 2,
        "successful": 2,
        "failed": 0
    },
    "results": [
        {
            "id": "flight_1",
            "success": true,
            "translated_itinerary": "<div class=\"flight-result\">...</div>",
            "gds_system": "SABRE",
            "original_itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200"
        },
        {
            "id": "flight_2",
            "success": true,
            "translated_itinerary": "<div class=\"flight-result\">...</div>",
            "gds_system": "SABRE",
            "original_itinerary": "2 UA 5678 16JAN W BOGMIA 1400 1800"
        }
    ]
}
```

## Códigos de Error

### 400 Bad Request
- Itinerario vacío
- Valores negativos en cálculo de precios
- Formato de datos inválido
- Límite de itinerarios excedido (>10 en lote)
- Sistema GDS no soportado

### 401 Unauthorized
- Token JWT faltante o inválido

### 500 Internal Server Error
- Error interno del servidor
- Error en procesamiento de datos

## Ejemplos de Uso

### JavaScript/Fetch
```javascript
// Traducir itinerario
const response = await fetch('/api/translator/itinerary/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
        itinerary: '1 AA 1234 15JAN W MIABOG 0800 1200',
        gds_system: 'SABRE'
    })
});

const data = await response.json();
console.log(data.translated_itinerary);
```

### Python/Requests
```python
import requests

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

data = {
    'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
    'gds_system': 'SABRE'
}

response = requests.post(
    'http://localhost:8000/api/translator/itinerary/',
    headers=headers,
    json=data
)

result = response.json()
print(result['translated_itinerary'])
```

### cURL
```bash
curl -X POST http://localhost:8000/api/translator/itinerary/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200",
    "gds_system": "SABRE"
  }'
```

## Formatos de Itinerario por GDS

### SABRE
```
1 AA 1234 15JAN W MIABOG 0800 1200
```
- Número de segmento
- Código de aerolínea (2 caracteres)
- Número de vuelo
- Fecha (DDMMM)
- Día de la semana
- Origen y destino (3 caracteres cada uno)
- Hora de salida y llegada (HHMM)

### AMADEUS
```
1 AA 1234A A 15JAN W MIABOG 0800 1200
```
- Similar a SABRE con variaciones en el formato

### KIU
```
1 AA 1234 15JAN WE MIABOG 0800 1200
```
- Similar a SABRE con día de la semana de 2 caracteres

## Notas Importantes

1. **Límites de Rate**: No hay límites específicos implementados actualmente.
2. **Caché**: Los catálogos de aerolíneas y aeropuertos se cargan dinámicamente.
3. **Validación**: La validación de formato es básica y puede no detectar todos los errores.
4. **HTML Output**: La traducción devuelve HTML formateado para mostrar en frontend.
5. **Batch Processing**: Máximo 10 itinerarios por lote para evitar timeouts.

## Próximas Mejoras

- [ ] Soporte para más formatos de GDS
- [ ] Validación más robusta de formatos
- [ ] Caché de traducciones frecuentes
- [ ] Exportación a diferentes formatos (PDF, Excel)
- [ ] Integración con APIs de aerolíneas para datos en tiempo real