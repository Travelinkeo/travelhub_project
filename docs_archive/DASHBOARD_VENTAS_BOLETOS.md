# Dashboard de Ventas de Boletos

## Resumen

Dashboard consolidado que muestra todas las ventas de boletos agrupadas por localizador, con información financiera editable y datos de pasajeros, aerolíneas y proveedores.

## Características

### Información Consolidada por Localizador

Cada fila muestra:
- **Localizador**: Código único de la reserva
- **Fecha**: Fecha de la venta
- **Cliente**: Cliente asignado o "Sin asignar"
- **Pasajeros**: Lista con apellidos, nombres y tipo (Adulto, Niño, Infante, etc.)
- **Cantidad de Boletos**: Total de boletos en la venta
- **Aerolínea**: Aerolínea emisora (extraída del parseo)
- **Proveedor**: Agente emisor (a quién se le debe)
- **Total Venta**: Monto total de la venta
- **Costo Neto**: Suma de costos netos de proveedores
- **Fee Proveedor**: Suma de fees de emisión
- **Comisión Agencia**: Suma de comisiones ganadas
- **Fee Agencia**: Suma de fees internos
- **Margen**: Utilidad calculada automáticamente
- **Estado**: Estado actual de la venta
- **Moneda**: Moneda de la transacción

### Campos Editables

Al hacer clic en "Ver Items", se despliegan los boletos individuales con campos editables:

- ✏️ **Costo Neto Proveedor**: Costo base del servicio
- ✏️ **Fee Proveedor**: Fee de emisión del proveedor
- ✏️ **Comisión Agencia**: Comisión ganada
- ✏️ **Fee Agencia**: Fee de servicio interno

Los campos editables están resaltados en amarillo y se actualizan en tiempo real.

### Estadísticas Globales

Panel superior con:
- Total de ventas
- Total de boletos
- Ingresos totales
- Margen total

### Filtros

- **Localizador**: Buscar por código de reserva
- **Fecha Desde**: Filtrar desde fecha
- **Fecha Hasta**: Filtrar hasta fecha

## Acceso

**URL**: `/dashboard/ventas-boletos/`

**Requiere**: Usuario autenticado

## Uso

### 1. Visualizar Ventas

Acceder a la URL para ver todas las ventas de boletos agrupadas por localizador.

### 2. Filtrar

Usar los filtros superiores para buscar ventas específicas:
```
Localizador: ABC123
Fecha Desde: 2025-01-01
Fecha Hasta: 2025-01-31
```

### 3. Ver Detalles

Hacer clic en "Ver Items" para expandir los boletos individuales de una venta.

### 4. Editar Información Financiera

1. Hacer clic en cualquier campo amarillo (editable)
2. Ingresar el nuevo valor en el prompt
3. Confirmar
4. El sistema actualiza automáticamente:
   - El campo editado
   - Los totales de la venta
   - El margen calculado

### 5. Información de Pasajeros

Cada venta muestra la lista de pasajeros con:
- Apellidos y nombres
- Tipo de pasajero (Adulto, Niño, Infante, Tercera Edad, Discapacitado)
- Documento de identidad

## Flujo de Datos

```
Email con Boleto
    ↓
Parseo Automático
    ↓
JSON guardado en BoletoParseo
    ↓
Venta creada/actualizada (agrupada por localizador)
    ↓
Items de Venta (boletos individuales)
    ↓
Dashboard muestra información consolidada
    ↓
Usuario edita campos financieros
    ↓
Sistema recalcula totales y margen
```

## Agrupación por Localizador

El sistema agrupa automáticamente:
- Múltiples boletos del mismo localizador en una sola venta
- Diferentes tipos de pasajero (adulto, niño, infante, etc.)
- Información financiera consolidada

**Ejemplo**:
```
Localizador: ABC123
- Boleto 1: Juan Pérez (Adulto) - $500
- Boleto 2: María Pérez (Niño) - $350
- Boleto 3: Pedro Pérez (Infante) - $100
Total: $950
```

## Información de Proveedores

El dashboard identifica:
- **Agente Emisor**: Proveedor que emitió el boleto (a quién se le debe)
- **Aerolínea**: Compañía aérea (para análisis de ventas por aerolínea)

Esto permite:
- Saber cuánto se le debe a cada proveedor
- Analizar qué aerolíneas se venden más
- Calcular comisiones por proveedor

## Cálculo de Margen

El margen se calcula automáticamente:

```
Margen = Total Venta - Costo Neto - Fee Proveedor + Comisión Agencia
```

Se actualiza en tiempo real al editar cualquier campo financiero.

## API de Actualización

**Endpoint**: `/api/boletos/actualizar-item/`

**Método**: POST

**Parámetros**:
- `item_id`: ID del item de venta
- `campo`: Campo a actualizar (costo_neto_proveedor, fee_proveedor, comision_agencia_monto, fee_agencia_interno)
- `valor`: Nuevo valor

**Respuesta**:
```json
{
    "success": true,
    "nuevo_valor": "100.00",
    "total_venta": "1500.00",
    "margen": "250.00"
}
```

## Tipos de Pasajero Soportados

El sistema reconoce y muestra:
- **ADT**: Adulto
- **CHD**: Niño
- **INF**: Infante
- **SEN**: Tercera Edad
- **DIS**: Discapacitado
- **STU**: Estudiante
- **MIL**: Militar

## Integración con Parseo

El dashboard extrae automáticamente:
- **Aerolínea**: Del campo `aerolinea_emisora` del parseo
- **Localizador**: Del campo `codigo_reservacion`
- **Pasajeros**: De la lista de pasajeros parseados
- **Información financiera**: De los campos `fare`, `taxes`, `total`

## Mejores Prácticas

1. ✅ **Editar información financiera inmediatamente**: Después de que se crea la venta
2. ✅ **Verificar proveedores**: Asegurar que el proveedor correcto esté asignado
3. ✅ **Revisar márgenes**: Validar que los márgenes sean correctos
4. ✅ **Filtrar por fecha**: Para análisis de períodos específicos
5. ✅ **Exportar datos**: Usar filtros para generar reportes

## Troubleshooting

### No aparecen ventas

**Causa**: No hay ventas con items de boletos.

**Solución**: Verificar que las ventas tengan items con producto "boleto" en el nombre.

### Aerolínea muestra "N/A"

**Causa**: No se encontró información de aerolínea en el parseo.

**Solución**: Verificar que el parseo del boleto incluya el campo `aerolinea_emisora`.

### No se puede editar campo

**Causa**: Error de permisos o conexión.

**Solución**: Verificar que el usuario esté autenticado y tenga permisos.

### Margen incorrecto

**Causa**: Campos financieros sin completar.

**Solución**: Editar todos los campos financieros (costo, fees, comisión).

## Próximas Mejoras

1. **Exportación a Excel**: Descargar datos filtrados
2. **Gráficos**: Visualización de ventas por aerolínea/proveedor
3. **Edición masiva**: Actualizar múltiples items a la vez
4. **Historial de cambios**: Auditoría de ediciones
5. **Alertas**: Notificar márgenes negativos
6. **Integración contable**: Generar asientos desde el dashboard

---

**Estado**: ✅ Implementado y Funcional  
**Versión**: 1.0  
**Fecha**: Enero 2025  
**URL**: `/dashboard/ventas-boletos/`
