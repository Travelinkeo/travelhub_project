# Ajustes de Facturación según Investigación de Gemini

**Fecha**: 24 de Octubre de 2025  
**Fuente**: Investigación exhaustiva de Gemini sobre facturación de agencias de viajes en Venezuela

---

## 📋 Resumen de Ajustes Implementados

### 1. Plantilla PDF Actualizada

**Archivo**: `core/templates/facturas/factura_consolidada_pdf.html`

#### Cambios Implementados:

1. **Leyenda Art. 10 Ley IVA** (Facturación por Cuenta de Terceros)
   - Agregada leyenda destacada: "SE EMITE DE CONFORMIDAD CON EL ARTÍCULO 10 DE LA LEY DE IVA"
   - Solo aparece cuando `tipo_operacion == 'INTERMEDIACION'`
   - Fondo amarillo (#ffffcc) para máxima visibilidad

2. **Identificación del Tercero**
   - Muestra claramente: "Servicio Prestado Por: [Razón Social] - RIF: [RIF]"
   - Aparece en sección "TIPO DE OPERACIÓN"
   - Solo cuando hay intermediación y tercero identificado

3. **Formato de Fecha y Hora**
   - Fecha: Formato DDMMAAAA (ej: 24102025)
   - Hora: Formato HH:MM:SS AM/PM (ej: 02:15:00 p.m.)
   - Cumple con Providencia 0071 y 102

4. **Indicación de Contingencia**
   - Título cambia a "FACTURA - CONTINGENCIA" si aplica
   - Leyenda específica para contingencia en pie de página
   - Referencia a Providencia 0071 para contingencia

5. **Monto Sujeto a Retención ISLR**
   - Nota al pie de totales indicando base de retención
   - Solo aparece en facturas de intermediación (servicios propios)
   - Formato: "Monto sujeto a retención de ISLR (5%): USD X.XX"

6. **Contribuyente Especial**
   - Indicador en encabezado si `es_sujeto_pasivo_especial == True`
   - Texto destacado: "CONTRIBUYENTE ESPECIAL"

7. **Leyendas Normativas**
   - Digital: "Documento emitido conforme a la Providencia Administrativa SNAT/2024/000102"
   - Contingencia: "Documento emitido conforme a la Providencia Administrativa SNAT/2011/00071"
   - Placeholder para datos de imprenta digital autorizada

8. **Totales Condicionales**
   - Solo muestra líneas con valores > 0
   - Evita confusión con bases imponibles vacías
   - Formato más limpio y profesional

---

## 🎯 Conceptos Clave de la Investigación

### Doble Facturación (Obligatoria)

Para cada venta de servicio de tercero, se deben emitir **DOS facturas**:

1. **Factura por Cuenta de Terceros**
   - Documenta el costo del servicio principal (boleto, hotel, paquete)
   - Identifica al proveedor final (aerolínea, hotel) con RIF
   - Leyenda Art. 10 Ley IVA
   - IVA desglosado es del tercero, no de la agencia
   - **NO está sujeta a retención ISLR**

2. **Factura por Servicios Propios**
   - Documenta el fee/comisión de la agencia
   - Ingreso real y gravable de la agencia
   - Base para cálculo de IVA e ISLR de la agencia
   - **SÍ está sujeta a retención ISLR (5%)**

### Tratamiento IVA por Tipo de Servicio

| Tipo de Servicio | Base Gravada | Base No Sujeta | IVA |
|------------------|--------------|----------------|-----|
| **Boleto Aéreo Nacional** | 100% del fee | 0% | 16% sobre 100% |
| **Paquete Turístico Nacional** | 100% del fee | 0% | 16% sobre 100% |
| **Boleto Aéreo Internacional** | 20% del fee | 80% del fee | 16% sobre 20% |
| **Paquete Turístico Internacional** | 20% del fee | 80% del fee | 16% sobre 20% |

**Razón**: Principio de territorialidad (Art. 3 Ley IVA) - Solo se grava la porción del servicio ejecutada/aprovechada en Venezuela.

### Retención ISLR

- **Aplica sobre**: Factura por Servicios Propios (fee de la agencia)
- **NO aplica sobre**: Factura por Cuenta de Terceros (costo del boleto/hotel)
- **Porcentaje**: 5% (Persona Jurídica a Persona Jurídica)
- **Base**: 100% del fee (antes de IVA), incluso si parte es "no sujeto" a IVA

---

## 📊 Ejemplo Práctico

### Venta de Boleto Internacional CCS-MAD

**Datos**:
- Precio boleto: USD 1,000.00
- Fee agencia: USD 100.00
- Tasa BCV: Bs. 36.50

**Factura 1: Por Cuenta de Terceros**
```
Descripción: Boleto aéreo CCS-MAD, Pasajero: Juan Pérez
Servicio prestado por: Iberia Airlines, RIF J-XXXXXXXX-X
Total: USD 1,000.00
Leyenda: "SE EMITE DE CONFORMIDAD CON EL ARTÍCULO 10 DE LA LEY DE IVA"
```

**Factura 2: Por Servicios Propios**
```
Descripción: Fee por servicio de emisión boleto internacional
Base Imponible (16%): USD 20.00 (20% del fee)
Monto No Sujeto: USD 80.00 (80% del fee)
IVA (16% s/ 20.00): USD 3.20
TOTAL A PAGAR: USD 103.20
Equivalente: Bs. 3,766.80

Nota ISLR: Monto sujeto a retención de ISLR (5%): USD 100.00
```

**Retención ISLR que practica el cliente**:
- Base: USD 100.00 (fee completo)
- Retención 5%: USD 5.00
- Pago neto a agencia: USD 98.20 (103.20 - 5.00)

---

## ✅ Checklist de Cumplimiento

### Factura por Cuenta de Terceros
- [ ] Identifica Razón Social y RIF del tercero
- [ ] Incluye leyenda Art. 10 Ley IVA
- [ ] IVA desglosado (si aplica) es del tercero
- [ ] Descripción específica del servicio

### Factura por Servicios Propios
- [ ] Monto es solo el fee/comisión de la agencia
- [ ] Para servicios nacionales: IVA 16% sobre 100% del fee
- [ ] Para servicios internacionales: Separación 20% gravado / 80% no sujeto
- [ ] Indica monto sujeto a retención ISLR

### Ambas Facturas
- [ ] Número único y consecutivo
- [ ] Número de control fiscal
- [ ] Fecha formato DDMMAAAA
- [ ] Hora formato HH:MM:SS AM/PM
- [ ] Datos completos emisor y receptor
- [ ] Leyenda normativa (Providencia 102 o 0071)
- [ ] Datos imprenta digital/física autorizada

---

## 🚨 Errores Críticos a Evitar

1. **Facturar monto total como ingreso propio**
   - ❌ Factura única por USD 1,100 (boleto + fee)
   - ✅ Dos facturas: USD 1,000 (tercero) + USD 100 (propio)

2. **Calcular IVA sobre 100% del fee internacional**
   - ❌ IVA 16% sobre USD 100 = USD 16
   - ✅ IVA 16% sobre USD 20 (20%) = USD 3.20

3. **No identificar al tercero**
   - ❌ "Boleto aéreo CCS-MAD"
   - ✅ "Boleto aéreo CCS-MAD, Servicio prestado por: Iberia, RIF J-XXX"

4. **Permitir retención ISLR sobre factura de tercero**
   - ❌ Cliente retiene 5% sobre USD 1,000
   - ✅ Cliente retiene 5% solo sobre USD 100 (fee)

---

## 📚 Referencias Normativas

- **Providencia SNAT/2024/000102**: Facturación digital (obligatoria desde 19/03/2025)
- **Providencia SNAT/2011/00071**: Facturación tradicional (contingencia)
- **Ley IVA Art. 10**: Facturación por cuenta de terceros
- **Ley IVA Art. 3**: Principio de territorialidad
- **Decreto 1.808**: Retenciones ISLR

---

## 🔄 Próximos Pasos Sugeridos

1. **Implementar lógica de doble facturación automática**
   - Al crear venta con boleto, generar ambas facturas
   - Vincular factura de tercero con factura de servicio

2. **Agregar campo para datos de imprenta digital**
   - Razón Social, RIF, Número de Providencia
   - Configuración en settings o modelo Agencia

3. **Validaciones en frontend**
   - Obligar identificación de tercero si tipo_operacion == 'INTERMEDIACION'
   - Calcular automáticamente proporción 20/80 para servicios internacionales

4. **Reportes fiscales**
   - Libro de Ventas separando operaciones propias vs terceros
   - Reporte de retenciones ISLR recibidas

---

**Última actualización**: 24 de Octubre de 2025  
**Estado**: ✅ Plantilla PDF actualizada con mejores prácticas  
**Autor**: Amazon Q Developer (basado en investigación de Gemini)
