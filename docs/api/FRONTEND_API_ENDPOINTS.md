# API Endpoints para Frontend - TravelHub

Documentación completa de los endpoints implementados para el frontend, organizados por prioridad.

## 🔐 Autenticación

Todos los endpoints requieren autenticación JWT excepto donde se indique lo contrario.

**Headers requeridos:**
```
Authorization: Bearer <access_token>
```

---

## 🚀 Alta Prioridad

### 1. Dashboard de Métricas

#### GET `/api/dashboard/metricas/`
Obtiene métricas generales del dashboard.

**Query Params:**
- `fecha_desde` (opcional): YYYY-MM-DD
- `fecha_hasta` (opcional): YYYY-MM-DD

**Response:**
```json
{
  "resumen": {
    "total_ventas": 150,
    "monto_total": 125000.50,
    "saldo_pendiente": 15000.00,
    "margen_estimado": 12500.00,
    "co2_estimado_kg": 5000.00
  },
  "ventas_por_estado": [
    {"estado": "PAG", "count": 80, "total": 80000.00},
    {"estado": "PEN", "count": 50, "total": 35000.00}
  ],
  "ventas_por_tipo": [...],
  "ventas_por_canal": [...],
  "top_clientes": [
    {
      "cliente__id_cliente": 1,
      "cliente__nombres": "Juan",
      "cliente__apellidos": "Pérez",
      "total_compras": 50000.00,
      "num_ventas": 10
    }
  ],
  "liquidaciones_pendientes": {
    "count": 5,
    "total": 10000.00
  },
  "facturas_pendientes": {
    "count": 8,
    "total": 15000.00
  },
  "tendencia_semanal": [
    {"fecha": "2025-01-01", "total": 5000.00, "count": 3}
  ]
}
```

#### GET `/api/dashboard/alertas/`
Obtiene alertas y notificaciones importantes.

**Response:**
```json
{
  "alertas": [
    {
      "tipo": "ventas_sin_cliente",
      "count": 5,
      "mensaje": "5 venta(s) sin cliente asignado",
      "severidad": "warning"
    },
    {
      "tipo": "ventas_mora",
      "count": 3,
      "mensaje": "3 venta(s) con saldo pendiente > 7 días",
      "severidad": "error"
    }
  ]
}
```

---

### 2. Liquidaciones a Proveedores

#### GET `/api/liquidaciones/`
Lista todas las liquidaciones (con paginación, filtros y búsqueda).

**Query Params:**
- `estado`: PEN, PAR, PAG
- `proveedor`: ID del proveedor
- `venta`: ID de la venta
- `search`: Búsqueda por ID, nombre proveedor o localizador
- `ordering`: Ordenamiento (ej: `-fecha_emision`)

**Response:**
```json
{
  "count": 50,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id_liquidacion": 1,
      "proveedor": 5,
      "proveedor_detalle": {...},
      "venta": 10,
      "venta_detalle": "Venta #10",
      "fecha_emision": "2025-01-15T10:00:00Z",
      "monto_total": 5000.00,
      "saldo_pendiente": 2000.00,
      "estado": "PAR",
      "estado_display": "Pagada Parcialmente",
      "notas": "",
      "items_liquidacion": [...]
    }
  ]
}
```

#### POST `/api/liquidaciones/{id}/marcar_pagada/`
Marca una liquidación como pagada completamente.

**Response:**
```json
{
  "status": "Liquidación marcada como pagada"
}
```

#### POST `/api/liquidaciones/{id}/registrar_pago_parcial/`
Registra un pago parcial.

**Body:**
```json
{
  "monto": 1000.00
}
```

**Response:**
```json
{
  "status": "Pago registrado",
  "saldo_pendiente": 1000.00,
  "estado": "PAR"
}
```

#### GET `/api/liquidaciones/pendientes/`
Obtiene solo liquidaciones pendientes.

#### GET `/api/liquidaciones/por_proveedor/?proveedor_id=5`
Filtra liquidaciones por proveedor específico.

---

### 3. Generación de Vouchers

#### POST `/api/ventas/{venta_id}/generar-voucher/`
Genera un voucher unificado en PDF para una venta.

**Response:**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="Voucher-{localizador}.pdf"`

---

## 📊 Prioridad Media

### 4. Auditoría y Trazabilidad

#### GET `/api/auditoria/venta/{venta_id}/`
Obtiene el historial completo de auditoría para una venta.

**Response:**
```json
{
  "venta_id": 10,
  "total_eventos": 15,
  "timeline": [
    {
      "id": 1,
      "fecha": "2025-01-15T10:00:00Z",
      "accion": "CREATE",
      "modelo": "Venta",
      "descripcion": "Venta creada",
      "datos_previos": null,
      "datos_nuevos": {...},
      "metadata": {}
    }
  ]
}
```

#### GET `/api/auditoria/estadisticas/`
Estadísticas generales de auditoría.

**Response:**
```json
{
  "por_accion": [
    {"accion": "UPDATE", "count": 150},
    {"accion": "CREATE", "count": 80}
  ],
  "por_modelo": [
    {"modelo": "Venta", "count": 200},
    {"modelo": "ItemVenta", "count": 150}
  ],
  "total_registros": 500
}
```

#### GET `/api/audit-logs/`
ViewSet completo para logs de auditoría (CRUD, filtros, búsqueda).

---

### 5. Gestión de Pasaportes OCR

#### GET `/api/pasaportes/`
Lista todos los pasaportes escaneados.

**Filtros:**
- `verificado_manualmente`: true/false
- `nacionalidad`: Código país
- `confianza_ocr`: Valor decimal (0-1)

**Response:**
```json
{
  "count": 20,
  "results": [
    {
      "id": 1,
      "imagen_original": "/media/pasaportes/...",
      "cliente": 5,
      "cliente_detalle": {...},
      "numero_pasaporte": "AB123456",
      "nombres": "Juan",
      "apellidos": "Pérez",
      "nombre_completo": "Juan Pérez",
      "nacionalidad": "VE",
      "fecha_nacimiento": "1990-01-15",
      "fecha_vencimiento": "2030-01-15",
      "sexo": "M",
      "confianza_ocr": 0.95,
      "verificado_manualmente": false,
      "es_valido": true,
      "fecha_procesamiento": "2025-01-15T10:00:00Z"
    }
  ]
}
```

#### POST `/api/pasaportes/{id}/verificar/`
Marca un pasaporte como verificado manualmente.

#### POST `/api/pasaportes/{id}/crear_cliente/`
Crea o actualiza un cliente desde los datos del pasaporte.

**Response:**
```json
{
  "status": "Cliente creado",
  "cliente_id": 10
}
```

#### GET `/api/pasaportes/pendientes/`
Pasaportes sin cliente asociado.

#### GET `/api/pasaportes/baja_confianza/?umbral=0.7`
Pasaportes con baja confianza OCR que requieren revisión.

---

### 6. Gestión de Boletos Importados

#### GET `/api/boletos/sin-venta/`
Lista de boletos parseados sin venta asociada.

**Response:**
```json
[
  {
    "id_boleto_importado": 1,
    "archivo_boleto": "/media/boletos/...",
    "estado_parseo": "COM",
    "numero_boleto": "0577280309142",
    "nombre_pasajero_completo": "PEREZ/JUAN",
    "total_boleto": 500.00,
    "localizador_pnr": "ABC123",
    "venta_asociada": null
  }
]
```

#### POST `/api/boletos/{boleto_id}/reintentar-parseo/`
Reintentar parseo de un boleto.

**Response:**
```json
{
  "status": "Parseo reiniciado",
  "boleto_id": 1
}
```

#### POST `/api/boletos/{boleto_id}/crear-venta/`
Crear venta automáticamente desde un boleto parseado.

**Response:**
```json
{
  "status": "Venta creada exitosamente",
  "venta_id": 50,
  "localizador": "TH-2025-00050"
}
```

#### GET `/api/boletos-importados/`
ViewSet completo para boletos (CRUD, filtros, búsqueda).

---

## 📈 Baja Prioridad

### 7. Reportes Contables

#### GET `/api/reportes/libro-diario/`
Libro diario contable.

**Query Params:**
- `fecha_desde`: YYYY-MM-DD
- `fecha_hasta`: YYYY-MM-DD

**Response:**
```json
{
  "periodo": {
    "desde": "2025-01-01",
    "hasta": "2025-01-31"
  },
  "total_asientos": 50,
  "asientos": [
    {
      "numero_asiento": "ASI-2025-001",
      "fecha": "2025-01-15",
      "descripcion": "Venta de servicios",
      "total_debe": 1000.00,
      "total_haber": 1000.00,
      "esta_cuadrado": true,
      "estado": "CON",
      "detalles": [
        {
          "cuenta": "1101",
          "cuenta_nombre": "Caja",
          "descripcion": "Cobro cliente",
          "debe": 1000.00,
          "haber": 0.00
        }
      ]
    }
  ]
}
```

#### GET `/api/reportes/balance-comprobacion/`
Balance de comprobación (sumas y saldos).

**Query Params:**
- `fecha_hasta`: YYYY-MM-DD

**Response:**
```json
{
  "fecha_corte": "2025-01-31",
  "balance": [
    {
      "cuenta": "1101",
      "nombre": "Caja",
      "debe": 50000.00,
      "haber": 30000.00,
      "saldo": 20000.00,
      "naturaleza": "Deudora"
    }
  ],
  "totales": {
    "debe": 500000.00,
    "haber": 500000.00,
    "diferencia": 0.00
  }
}
```

#### GET `/api/reportes/validar-cuadre/`
Valida que todos los asientos estén cuadrados.

**Response:**
```json
{
  "cuadrado": false,
  "asientos_con_problemas": 2,
  "problemas": [
    {
      "numero_asiento": "ASI-2025-005",
      "fecha": "2025-01-20",
      "debe": 1000.00,
      "haber": 999.00,
      "diferencia": 1.00
    }
  ]
}
```

#### GET `/api/reportes/exportar-excel/`
Exporta libro diario a Excel.

**Query Params:**
- `fecha_desde`: YYYY-MM-DD
- `fecha_hasta`: YYYY-MM-DD

**Response:**
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: `attachment; filename="libro_diario_YYYYMMDD.xlsx"`

---

### 8. Comunicaciones con Proveedores

#### GET `/api/comunicaciones/`
Lista todas las comunicaciones.

**Filtros:**
- `categoria`: Categoría de comunicación
- `remitente`: Email del remitente
- `search`: Búsqueda en asunto, remitente, cuerpo

**Response:**
```json
{
  "count": 100,
  "results": [
    {
      "id": 1,
      "remitente": "proveedor@example.com",
      "asunto": "Confirmación de reserva",
      "fecha_recepcion": "2025-01-15T10:00:00Z",
      "categoria": "RESERVA",
      "contenido_extraido": "...",
      "cuerpo_completo": "..."
    }
  ]
}
```

#### GET `/api/comunicaciones/por_categoria/`
Agrupa comunicaciones por categoría.

**Response:**
```json
[
  {"categoria": "RESERVA", "count": 50},
  {"categoria": "FACTURA", "count": 30}
]
```

#### GET `/api/comunicaciones/recientes/`
Últimas 20 comunicaciones.

---

## 📋 ViewSets Existentes (CRUD Completo)

Todos estos endpoints soportan operaciones CRUD estándar:
- `GET /api/{resource}/` - Listar
- `POST /api/{resource}/` - Crear
- `GET /api/{resource}/{id}/` - Detalle
- `PUT /api/{resource}/{id}/` - Actualizar completo
- `PATCH /api/{resource}/{id}/` - Actualizar parcial
- `DELETE /api/{resource}/{id}/` - Eliminar

### Recursos disponibles:
- `/api/ventas/`
- `/api/facturas/`
- `/api/clientes/`
- `/api/proveedores/`
- `/api/productos-servicios/`
- `/api/paises/`
- `/api/ciudades/`
- `/api/monedas/`
- `/api/aerolineas/`
- `/api/segmentos-vuelo/`
- `/api/alojamientos/`
- `/api/traslados/`
- `/api/actividades/`
- `/api/alquileres-autos/`
- `/api/eventos-servicios/`
- `/api/circuitos-turisticos/`
- `/api/paquetes-aereos/`
- `/api/servicios-adicionales/`
- `/api/fees-venta/`
- `/api/pagos-venta/`
- `/api/cotizaciones/`
- `/api/asientos-contables/`

---

## 🔍 Características Comunes

### Paginación
Todos los endpoints de lista soportan paginación:
```
?page=1&page_size=20
```

### Búsqueda
Endpoints con `search_fields` soportan:
```
?search=termino
```

### Filtros
Endpoints con `filterset_fields` soportan:
```
?campo=valor&otro_campo=otro_valor
```

### Ordenamiento
Endpoints con `ordering_fields` soportan:
```
?ordering=-fecha_creacion
```

---

## 🛠️ Próximos Pasos Sugeridos

1. **Acciones Masivas**: Implementar endpoints para operaciones en lote
2. **Webhooks**: Notificaciones en tiempo real
3. **GraphQL**: Alternativa a REST para queries complejas
4. **WebSockets**: Actualizaciones en tiempo real del dashboard
5. **Rate Limiting**: Protección contra abuso de API

---

## 📝 Notas de Implementación

- Todos los endpoints están protegidos con autenticación JWT
- Los serializers incluyen validaciones automáticas
- Los ViewSets incluyen permisos configurables
- Las respuestas siguen el estándar REST
- Los errores devuelven códigos HTTP apropiados (400, 404, 500, etc.)
