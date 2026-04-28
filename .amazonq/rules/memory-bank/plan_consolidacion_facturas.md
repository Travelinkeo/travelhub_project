# Plan de Consolidación de Modelos de Facturación

**Fecha**: 21 de Enero de 2025  
**Problema**: Duplicación de modelos Factura/FacturaVenezuela e ItemFactura/ItemFacturaVenezuela

---

## Situación Actual

### Modelos Existentes

1. **Factura** (básico)
   - Campos: numero_factura, cliente, fecha_emision, moneda, subtotal, monto_impuestos, monto_total, estado
   - Ubicación: `core/models/facturacion.py`

2. **FacturaVenezuela** (hereda de Factura)
   - Campos adicionales: numero_control, modalidad_emision, firma_digital, emisor_rif, tipo_operacion, moneda_operacion, tasa_cambio_bcv, subtotal_base_gravada, subtotal_exento, monto_iva_16, monto_igtf, etc.
   - Ubicación: Migración 0014
   - Cumple con normativa venezolana completa

3. **ItemFactura** (básico)
   - Campos: descripcion, cantidad, precio_unitario, subtotal_item

4. **ItemFacturaVenezuela** (hereda de ItemFactura)
   - Campos adicionales: tipo_servicio, es_gravado, alicuota_iva, nombre_pasajero, numero_boleto, itinerario, codigo_aerolinea

---

## Decisión: Consolidar en FacturaVenezuela

### Razones

1. **FacturaVenezuela cumple con normativa completa**:
   - Providencias 0071, 0032, 102, 121 del SENIAT
   - Ley de IVA (Art. 10 intermediación, alícuota adicional divisas)
   - Ley IGTF (3% sobre pagos en divisas)
   - Ley Orgánica de Turismo (contribución 1% INATUR)

2. **Dualidad monetaria USD/BSD**:
   - Campos para moneda funcional (USD) y presentación (BSD)
   - Tasa de cambio BCV automática
   - Diferencial cambiario

3. **Tipos de operación específicos**:
   - Intermediación (comisiones)
   - Venta propia (paquetes)
   - Exportación de servicios (turismo receptivo)

4. **Campos obligatorios para boletos aéreos**:
   - Nombre pasajero, número boleto, itinerario, código aerolínea
   - Requeridos por Providencia 0032

---

## Plan de Migración

### Fase 1: Crear Modelo Consolidado ✅

**Archivo**: `core/models/facturacion_venezuela.py`

```python
class FacturaVenezuela(models.Model):
    # Campos básicos (de Factura original)
    id_factura = AutoField(primary_key=True)
    numero_factura = CharField(max_length=50, unique=True)
    numero_control = CharField(max_length=50)  # Fiscal
    
    # Relaciones
    venta_asociada = ForeignKey('Venta', null=True)
    cliente = ForeignKey('personas.Cliente')
    moneda = ForeignKey(Moneda)
    
    # Fechas
    fecha_emision = DateField(default=timezone.now)
    fecha_vencimiento = DateField(null=True)
    
    # Emisor (agencia)
    emisor_rif = CharField(max_length=20)
    emisor_razon_social = CharField(max_length=200)
    emisor_direccion_fiscal = TextField()
    es_sujeto_pasivo_especial = BooleanField(default=False)
    esta_inscrita_rtn = BooleanField(default=False)
    
    # Cliente
    cliente_es_residente = BooleanField(default=True)
    cliente_identificacion = CharField(max_length=50)
    cliente_direccion = TextField(blank=True)
    
    # Tipo de operación
    tipo_operacion = CharField(choices=[
        ('VENTA_PROPIA', 'Venta Propia'),
        ('INTERMEDIACION', 'Intermediación')
    ])
    
    # Moneda y cambio
    moneda_operacion = CharField(choices=[
        ('BOLIVAR', 'Bolívar'),
        ('DIVISA', 'Divisa')
    ])
    tasa_cambio_bcv = DecimalField(max_digits=12, decimal_places=4, null=True)
    
    # Bases imponibles (moneda funcional USD)
    subtotal_base_gravada = DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal_exento = DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal_exportacion = DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Impuestos (moneda funcional USD)
    monto_iva_16 = DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_iva_adicional = DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_igtf = DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Totales (moneda funcional USD)
    subtotal = DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_total = DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_pendiente = DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Equivalentes en Bolívares (moneda de presentación BSD)
    subtotal_base_gravada_bs = DecimalField(max_digits=15, decimal_places=2, null=True)
    subtotal_exento_bs = DecimalField(max_digits=15, decimal_places=2, null=True)
    monto_iva_16_bs = DecimalField(max_digits=15, decimal_places=2, null=True)
    monto_igtf_bs = DecimalField(max_digits=15, decimal_places=2, null=True)
    monto_total_bs = DecimalField(max_digits=15, decimal_places=2, null=True)
    
    # Intermediación (Art. 10 Ley IVA)
    tercero_rif = CharField(max_length=20, blank=True)
    tercero_razon_social = CharField(max_length=200, blank=True)
    
    # Digital
    modalidad_emision = CharField(choices=[
        ('DIGITAL', 'Digital'),
        ('CONTINGENCIA_FISICA', 'Contingencia Física')
    ], default='DIGITAL')
    firma_digital = TextField(blank=True, null=True)
    
    # Estado
    estado = CharField(choices=[
        ('BOR', 'Borrador'),
        ('EMI', 'Emitida'),
        ('PAR', 'Pagada Parcialmente'),
        ('PAG', 'Pagada Totalmente'),
        ('VEN', 'Vencida'),
        ('ANU', 'Anulada')
    ], default='BOR')
    
    # Archivos
    archivo_pdf = FileField(upload_to='facturas/%Y/%m/', blank=True)
    
    # Contabilidad
    asiento_contable_factura = ForeignKey(AsientoContable, null=True)
    
    notas = TextField(blank=True)
    
    def save(self, *args, **kwargs):
        # Generar número de factura
        if not self.numero_factura:
            consecutivo = FacturaVenezuela.objects.count() + 1
            self.numero_factura = f"F-{self.fecha_emision.strftime('%Y%m%d')}-{consecutivo:04d}"
        
        # Calcular totales en USD
        self.subtotal = self.subtotal_base_gravada + self.subtotal_exento + self.subtotal_exportacion
        self.monto_total = self.subtotal + self.monto_iva_16 + self.monto_iva_adicional + self.monto_igtf
        
        # Convertir a Bolívares si hay tasa
        if self.tasa_cambio_bcv:
            self.subtotal_base_gravada_bs = self.subtotal_base_gravada * self.tasa_cambio_bcv
            self.subtotal_exento_bs = self.subtotal_exento * self.tasa_cambio_bcv
            self.monto_iva_16_bs = self.monto_iva_16 * self.tasa_cambio_bcv
            self.monto_igtf_bs = self.monto_igtf * self.tasa_cambio_bcv
            self.monto_total_bs = self.monto_total * self.tasa_cambio_bcv
        
        # Actualizar estado
        if self.saldo_pendiente <= 0 and self.monto_total > 0:
            self.estado = 'PAG'
        elif 0 < self.saldo_pendiente < self.monto_total:
            self.estado = 'PAR'
        
        super().save(*args, **kwargs)
```

```python
class ItemFacturaVenezuela(models.Model):
    id_item_factura = AutoField(primary_key=True)
    factura = ForeignKey(FacturaVenezuela, related_name='items_factura')
    
    # Descripción
    descripcion = CharField(max_length=500)
    cantidad = DecimalField(max_digits=10, decimal_places=2, default=1)
    precio_unitario = DecimalField(max_digits=12, decimal_places=2)
    subtotal_item = DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    # Tipo de servicio (determina tratamiento fiscal)
    tipo_servicio = CharField(choices=[
        ('COMISION_INTERMEDIACION', 'Comisión Intermediación'),
        ('TRANSPORTE_AEREO_NACIONAL', 'Transporte Aéreo Nacional'),
        ('ALOJAMIENTO_Y_OTROS_GRAVADOS', 'Alojamiento y Otros Gravados'),
        ('SERVICIO_EXPORTACION', 'Servicio Exportación')
    ], default='ALOJAMIENTO_Y_OTROS_GRAVADOS')
    
    # IVA
    es_gravado = BooleanField(default=True)
    alicuota_iva = DecimalField(max_digits=5, decimal_places=2, default=16.00)
    
    # Datos específicos para boletos aéreos (Providencia 0032)
    nombre_pasajero = CharField(max_length=200, blank=True)
    numero_boleto = CharField(max_length=50, blank=True)
    itinerario = TextField(blank=True)
    codigo_aerolinea = CharField(max_length=10, blank=True)
    
    def save(self, *args, **kwargs):
        self.subtotal_item = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)
        
        # Recalcular totales de factura
        self.factura.recalcular_totales()
```

### Fase 2: Migración de Datos

**Script**: `core/management/commands/consolidar_facturas.py`

```python
from django.core.management.base import BaseCommand
from core.models.facturacion import Factura, ItemFactura
from core.models.facturacion_venezuela import FacturaVenezuela, ItemFacturaVenezuela

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Migrar Facturas básicas a FacturaVenezuela
        for factura in Factura.objects.all():
            FacturaVenezuela.objects.create(
                numero_factura=factura.numero_factura,
                cliente=factura.cliente,
                fecha_emision=factura.fecha_emision,
                moneda=factura.moneda,
                subtotal_base_gravada=factura.subtotal,
                monto_iva_16=factura.monto_impuestos,
                monto_total=factura.monto_total,
                estado=factura.estado,
                # Valores por defecto para campos nuevos
                tipo_operacion='VENTA_PROPIA',
                moneda_operacion='DIVISA',
                cliente_es_residente=True,
                # ... otros campos
            )
```

### Fase 3: Actualizar Serializers y Views

**Archivo**: `core/serializers.py`

```python
class ItemFacturaVenezuelaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemFacturaVenezuela
        fields = '__all__'

class FacturaVenezuelaSerializer(serializers.ModelSerializer):
    items_factura = ItemFacturaVenezuelaSerializer(many=True)
    
    class Meta:
        model = FacturaVenezuela
        fields = '__all__'
    
    def create(self, validated_data):
        items_data = validated_data.pop('items_factura', [])
        factura = FacturaVenezuela.objects.create(**validated_data)
        
        for item_data in items_data:
            ItemFacturaVenezuela.objects.create(factura=factura, **item_data)
        
        return factura
```

### Fase 4: Actualizar Frontend

**Archivo**: `frontend/src/app/erp/facturas-clientes/FacturaForm.tsx`

Agregar campos específicos de Venezuela:
- Tipo de operación (Venta Propia / Intermediación)
- Moneda de operación (Bolívar / Divisa)
- Cliente residente (Sí / No)
- Desglose de bases imponibles (Gravada / Exenta / Exportación)
- Cálculo automático de IVA e IGTF

### Fase 5: Deprecar Modelos Antiguos

1. Marcar Factura e ItemFactura como deprecados
2. Agregar warnings en código
3. Después de 1 mes, eliminar modelos antiguos

---

## Beneficios de la Consolidación

1. **Un solo modelo** que cumple con toda la normativa venezolana
2. **Dualidad monetaria** USD/BSD nativa
3. **Cálculos automáticos** de IVA, IGTF, conversión a bolívares
4. **Campos obligatorios** para boletos aéreos
5. **Tipos de operación** claros (intermediación vs venta propia)
6. **Exportación de servicios** (turismo receptivo) con alícuota 0%
7. **Integración contable** con asientos automáticos

---

## Próximos Pasos

1. ✅ Crear `facturacion_venezuela.py` con modelos consolidados
2. ⏳ Crear migración de datos
3. ⏳ Actualizar serializers y views
4. ⏳ Actualizar frontend con campos completos
5. ⏳ Generar PDF con formato legal venezolano
6. ⏳ Integración con Libro de Ventas (IVA)
7. ⏳ Cálculo automático de contribución INATUR (1%)

---

**Última actualización**: 21 de Enero de 2025  
**Estado**: Plan definido, pendiente implementación  
**Autor**: Amazon Q Developer
