# Diccionario de Datos y Reglas de Negocio

**Versión:** 1.0
**Última Actualización:** 28 de Noviembre de 2025

Este documento define las estructuras de datos críticas, el plan de cuentas contable y las reglas de negocio automatizadas del sistema TravelHub.

## 1. Modelos Principales (Core)

### Venta (`core.models.Venta`)
Entidad central que agrupa toda transacción comercial.
*   **`localizador`**: Código único de reserva (PNR).
*   **`estado`**:
    *   `PENDIENTE`: Creada pero no cobrada.
    *   `PAGADO`: Cobrada en su totalidad (Saldo = 0).
    *   `ANULADO`: Cancelada sin efectos financieros.
*   **`moneda`**: Moneda base de la transacción (usualmente USD).

### BoletoImportado (`core.models.BoletoImportado`)
Representa un ticket aéreo extraído automáticamente.
*   **`datos_parseados` (JSON)**: Contiene la data cruda extraída por el Parser.
*   **`monto_iva` (Decimal)**: El valor exacto del impuesto YN (Venezuela) extraído del boleto.
*   **`comision_agencia` (Decimal)**: Ganancia calculada automáticamente según `AerolineaConfig`.

### AerolineaConfig (`core.models.AerolineaConfig`)
Reglas de negocio para el cálculo de comisiones.
*   **`identificador_parser`**: Texto clave (ej: "LASER") que el parser busca en el PDF.
*   **`porcentaje_comision`**: % de ganancia que aplica la agencia sobre la Tarifa Base.

## 2. Plan de Cuentas (VEN-NIF)

Mapeo de cuentas contables para la automatización financiera. Las cuentas marcadas con `*` reciben movimientos automáticos.

### Activos
*   `1.1.01.02` **Caja General (USD)** *
*   `1.1.01.04` **Bancos Nacionales (USD)** *
*   `1.1.02.02` **Cuentas por Cobrar Clientes (USD)** * (Se debita al facturar)

### Pasivos
*   `2.1.01.02` **Cuentas por Pagar Proveedores (USD)** * (Se acredita al vender boleto de tercero)
*   `2.1.02.01` **IVA Débito Fiscal por Pagar** * (Impuesto YN retenido)
*   `2.1.02.02` **Contribución INATUR por Pagar** *
*   `2.1.02.03` **IGTF por Pagar** *

### Ingresos
*   `4.1.01` **Comisiones por Venta de Boletos Aéreos** * (Solo el Fee/Comisión)
*   `4.2` **Ingresos por Venta de Paquetes** * (Venta Propia)
*   `7.1.01` **Ingreso por Diferencial Cambiario** * (Ganancia por tasa BCV)

### Egresos
*   `7.2.01` **Pérdida por Diferencial Cambiario** *

## 3. Lógica de Automatización Contable

### A. Generación de Asiento de Venta
Cuando se procesa un boleto de **Intermediación** (ej: Laser):
1.  **Debe (CxC):** Total Factura (lo que paga el cliente).
2.  **Haber (CxP Aerolínea):** Costo del boleto (Total - Comisión).
3.  **Haber (Ingreso Comisión):** Monto de la comisión (`AerolineaConfig`).
4.  **Haber (IVA DF):** Monto del impuesto YN.

### B. Diferencial Cambiario (Cobranza)
Al registrar un pago en Bolívares:
1.  Se compara `Tasa Factura` vs `Tasa Pago`.
2.  Si `Tasa Pago > Tasa Factura`:
    *   Se registra **Ganancia Cambiaria** (Cuenta 7.1.01).
    *   **Automático:** Se genera una **Nota de Débito** por el 16% (IVA) de esa ganancia.

## 4. Lógica del Parser (Extracción)

El sistema usa heurísticas para detectar el tipo de boleto y extraer datos financieros.

### Detección de GDS
*   **Sabre:** `ETICKET RECEIPT` + `RESERVATION CODE`.
*   **KIU:** `KIUSYS.COM` o `PASSENGER ITINERARY RECEIPT`.
*   **Amadeus:** `ELECTRONIC TICKET RECEIPT` + `BOOKING REF:`.

### Extracción Financiera (KIU)
*   **IVA (YN):** Se busca explícitamente el patrón `123.45YN` o `YN 123.45`.
*   **Base Imponible:** Si no está explícita, se calcula: `Total - Impuestos`.
