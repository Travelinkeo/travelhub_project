# Guía de API para Frontend - TravelHub

## 🔐 **Autenticación**

### Login
```javascript
POST /api/auth/login/
{
  "username": "tu_usuario",
  "password": "tu_contraseña"
}
// Respuesta: {"token": "61af56d1f722f4cc71889e07e9d49ebdb33bdd36"}
```

### Headers para requests autenticados
```javascript
headers: {
  "Authorization": "Token 61af56d1f722f4cc71889e07e9d49ebdb33bdd36",
  "Content-Type": "application/json"
}
```

## 🏨 **Crear Venta de Hotel**

### Estructura completa
```javascript
POST /api/ventas/
{
  "cliente": 6,                    // ID del cliente (requerido)
  "moneda": 4,                     // ID de la moneda (requerido)
  "descripcion_general": "Reserva Hotel Marriott Caracas",
  "tipo_venta": "B2C",             // B2C, B2B, MICE, PKG, CIR, TLD, SEG, OTR
  "canal_origen": "WEB",           // ADM, IMP, API, WEB, MIG, OTR
  "items_venta": [
    {
      "producto_servicio": 2,      // ID del producto/servicio (requerido)
      "precio_unitario_venta": 450.00,  // Precio (requerido)
      "cantidad": 1,
      "descripcion_personalizada": "Hotel Marriott - Habitación Doble Superior",
      "fecha_inicio_servicio": "2025-10-30T15:00:00Z",
      "fecha_fin_servicio": "2025-11-02T11:00:00Z",
      "proveedor_servicio": 1,     // ID del proveedor
      "costo_neto_proveedor": 350.00,
      "fee_proveedor": 25.00,
      "comision_agencia_monto": 50.00,
      "fee_agencia_interno": 25.00,
      "alojamiento_details": {     // Datos específicos del hotel
        "nombre_establecimiento": "Hotel Marriott Caracas",
        "check_in": "2025-10-30",
        "check_out": "2025-11-02",
        "regimen_alimentacion": "Todo Incluido",  // Solo Desayuno, Media Pensión, Pensión Completa
        "habitaciones": 1,
        "ciudad": 1,               // ID de la ciudad (requerido)
        "proveedor": 1,            // ID del proveedor
        "notas": "Habitación con vista al mar"
      }
    }
  ]
}
```

### Respuesta exitosa (201)
```javascript
{
  "id_venta": 29,
  "localizador": "VTA-20250930-0027",
  "cliente_detalle": {
    "id_cliente": 6,
    "get_nombre_completo": "Armando Alemán",
    "email": "armando@example.com"
  },
  "total_venta": "450.00",
  "estado": "PEN",
  "estado_display": "Pendiente de Pago",
  "alojamientos": [
    {
      "id_alojamiento_reserva": 1,
      "nombre_establecimiento": "Hotel Marriott Caracas",
      "check_in": "2025-10-30",
      "check_out": "2025-11-02",
      "regimen_alimentacion": "Todo Incluido",
      "habitaciones": 1,
      "ciudad_detalle": {
        "id_ciudad": 1,
        "nombre": "Caracas",
        "pais_detalle": {
          "nombre": "Venezuela"
        }
      }
    }
  ]
}
```

## 🔍 **Búsqueda de Catálogos**

### Clientes
```javascript
GET /api/clientes/?search=armando
```

### Ciudades (con búsqueda)
```javascript
GET /api/ciudades/?search=caracas
GET /api/ciudades/?search=venezuela  // Busca por país
GET /api/ciudades/?ordering=nombre   // Ordenar alfabéticamente
```

### Monedas
```javascript
GET /api/monedas/
// Sin paginación, devuelve todas las monedas
```

### Productos/Servicios
```javascript
GET /api/productos-servicio/
GET /api/productos-servicio/?search=hotel
```

### Proveedores
```javascript
GET /api/proveedores/?search=marriott
```

## 🚗 **Otros Tipos de Venta**

### Alquiler de Autos
```javascript
// Usar endpoint directo
POST /api/alquileres-autos/
{
  "venta": 29,  // ID de la venta creada
  "categoria_auto": "SUV",
  "compania_rentadora": "Hertz",
  "fecha_hora_retiro": "2025-10-30T10:00:00Z",
  "fecha_hora_devolucion": "2025-11-02T10:00:00Z",
  "ciudad_retiro": 1,
  "ciudad_devolucion": 1,
  "incluye_seguro": true,
  "numero_confirmacion": "ABC123456"
}
```

### Traslados
```javascript
POST /api/traslados/
{
  "venta": 29,
  "tipo_traslado": "ARR",  // ARR, DEP, INT
  "origen": "Aeropuerto Internacional",
  "destino": "Hotel Marriott",
  "fecha_hora": "2025-10-30T14:00:00Z",
  "pasajeros": 2,
  "proveedor": 1
}
```

## ⚠️ **Errores Comunes**

### Error 400 - Datos inválidos
```javascript
{
  "cliente": ["Este campo es requerido."],
  "items_venta": [
    {
      "producto_servicio": ["Este campo es requerido."]
    }
  ]
}
```

### Error 401 - No autenticado
```javascript
{
  "detail": "Las credenciales de autenticación no se proveyeron."
}
```

## 💡 **Consejos para el Frontend**

1. **Siempre validar** que cliente, moneda y producto_servicio existan antes de enviar
2. **Usar búsqueda** en ciudades: `?search=cara` para encontrar "Caracas"
3. **Fechas en ISO format**: `2025-10-30T15:00:00Z`
4. **Manejar paginación** en endpoints que la tienen
5. **Guardar el token** y renovarlo cuando expire

## 🔄 **Estados de Venta**

- `PEN`: Pendiente de Pago
- `PAR`: Pagada Parcialmente  
- `PAG`: Pagada Totalmente
- `CNF`: Confirmada
- `VIA`: En Proceso/Viaje
- `COM`: Completada
- `CAN`: Cancelada

## 📱 **Ejemplo para React/Next.js**

```javascript
const crearVentaHotel = async (datosVenta) => {
  const token = localStorage.getItem('token');
  
  const response = await fetch('/api/ventas/', {
    method: 'POST',
    headers: {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(datosVenta)
  });
  
  if (response.ok) {
    const venta = await response.json();
    console.log('Venta creada:', venta.localizador);
    return venta;
  } else {
    const errors = await response.json();
    console.error('Errores:', errors);
    throw new Error('Error creando venta');
  }
};
```