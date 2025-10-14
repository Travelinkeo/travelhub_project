# Plan de Ajustes del Modelo de Facturación para Venezuela

## Objetivo
Adaptar el sistema de facturación actual de TravelHub para cumplir con la normativa fiscal venezolana específica para agencias de viajes, incluyendo facturación digital, dualidad monetaria y múltiples impuestos.

## Fase 1: Extensión del Modelo de Facturación (Prioridad Alta)

### 1.1 Nuevos Campos en el Modelo Factura

```python
# Campos obligatorios para Venezuela
numero_control = models.CharField("Número de Control Fiscal", max_length=50, blank=True)
modalidad_emision = models.CharField("Modalidad", choices=MODALIDAD_CHOICES, default='DIGITAL')
firma_digital = models.TextField("Firma Digital", blank=True, null=True)

# Información fiscal del emisor (agencia)
emisor_rif = models.CharField("RIF Emisor", max_length=20)
emisor_razon_social = models.CharField("Razón Social Emisor", max_length=200)
emisor_direccion_fiscal = models.TextField("Dirección Fiscal Emisor")
es_sujeto_pasivo_especial = models.BooleanField("Es SPE", default=False)
esta_inscrita_rtn = models.BooleanField("Inscrita RTN", default=False)

# Información del cliente
cliente_es_residente = models.BooleanField("Cliente Residente", default=True)
cliente_identificacion = models.CharField("Identificación Cliente", max_length=50)
cliente_direccion = models.TextField("Dirección Cliente", blank=True)

# Operación y moneda
tipo_operacion = models.CharField("Tipo Operación", choices=TIPO_OPERACION_CHOICES)
moneda_operacion = models.CharField("Moneda Operación", choices=MONEDA_OPERACION_CHOICES)
tasa_cambio_bcv = models.DecimalField("Tasa BCV", max_digits=12, decimal_places=4, null=True)

# Cálculos fiscales
subtotal_base_gravada = models.DecimalField("Base Gravada 16%", max_digits=12, decimal_places=2, default=0)
subtotal_exento = models.DecimalField("Base Exenta", max_digits=12, decimal_places=2, default=0)
subtotal_exportacion = models.DecimalField("Base Exportación 0%", max_digits=12, decimal_places=2, default=0)
monto_iva_16 = models.DecimalField("IVA 16%", max_digits=12, decimal_places=2, default=0)
monto_iva_adicional = models.DecimalField("IVA Adicional Divisas", max_digits=12, decimal_places=2, default=0)
monto_igtf = models.DecimalField("IGTF 3%", max_digits=12, decimal_places=2, default=0)

# Datos del tercero (para intermediación)
tercero_rif = models.CharField("RIF Tercero", max_length=20, blank=True)
tercero_razon_social = models.CharField("Razón Social Tercero", max_length=200, blank=True)

# Equivalencias en bolívares (si factura en divisas)
subtotal_base_gravada_bs = models.DecimalField("Base Gravada Bs", max_digits=15, decimal_places=2, null=True)
subtotal_exento_bs = models.DecimalField("Base Exenta Bs", max_digits=15, decimal_places=2, null=True)
monto_iva_16_bs = models.DecimalField("IVA 16% Bs", max_digits=15, decimal_places=2, null=True)
monto_igtf_bs = models.DecimalField("IGTF Bs", max_digits=15, decimal_places=2, null=True)
monto_total_bs = models.DecimalField("Total Bs", max_digits=15, decimal_places=2, null=True)
```

### 1.2 Nuevos Campos en ItemFactura

```python
# Clasificación fiscal del servicio
tipo_servicio = models.CharField("Tipo Servicio", choices=TIPO_SERVICIO_CHOICES)
es_gravado = models.BooleanField("Es Gravado", default=True)
alicuota_iva = models.DecimalField("Alícuota IVA", max_digits=5, decimal_places=2, default=16.00)

# Datos específicos para boletos aéreos
nombre_pasajero = models.CharField("Nombre Pasajero", max_length=200, blank=True)
numero_boleto = models.CharField("Número Boleto", max_length=50, blank=True)
itinerario = models.TextField("Itinerario", blank=True)
codigo_aerolinea = models.CharField("Código Aerolínea", max_length=10, blank=True)
```

### 1.3 Enumeraciones y Choices

```python
class TipoOperacion(models.TextChoices):
    VENTA_PROPIA = 'VENTA_PROPIA', 'Venta Propia'
    INTERMEDIACION = 'INTERMEDIACION', 'Intermediación'

class MonedaOperacion(models.TextChoices):
    BOLIVAR = 'BOLIVAR', 'Bolívar'
    DIVISA = 'DIVISA', 'Divisa'

class ModalidadEmision(models.TextChoices):
    DIGITAL = 'DIGITAL', 'Digital'
    CONTINGENCIA_FISICA = 'CONTINGENCIA_FISICA', 'Contingencia Física'

class TipoServicio(models.TextChoices):
    COMISION_INTERMEDIACION = 'COMISION_INTERMEDIACION', 'Comisión Intermediación'
    TRANSPORTE_AEREO_NACIONAL = 'TRANSPORTE_AEREO_NACIONAL', 'Transporte Aéreo Nacional'
    ALOJAMIENTO_Y_OTROS_GRAVADOS = 'ALOJAMIENTO_Y_OTROS_GRAVADOS', 'Alojamiento y Otros Gravados'
    SERVICIO_EXPORTACION = 'SERVICIO_EXPORTACION', 'Servicio Exportación'
```

## Fase 2: Lógica de Cálculo Fiscal (Prioridad Alta)

### 2.1 Método de Cálculo Principal

```python
def calcular_impuestos_venezuela(self):
    """
    Calcula todos los impuestos según normativa venezolana
    """
    # 1. Determinar bases imponibles por tipo de servicio
    self._calcular_bases_imponibles()
    
    # 2. Calcular IVA según tipo de servicio y residencia del cliente
    self._calcular_iva()
    
    # 3. Calcular alícuota adicional si pago en divisas sobre exentos
    self._calcular_alicuota_adicional()
    
    # 4. Calcular IGTF si aplica (SPE + pago en divisas)
    self._calcular_igtf()
    
    # 5. Calcular equivalencias en bolívares si factura en divisas
    self._calcular_equivalencias_bolivares()
    
    # 6. Actualizar totales
    self._actualizar_totales()
```

### 2.2 Métodos de Cálculo Específicos

```python
def _calcular_bases_imponibles(self):
    """Clasifica items según tipo de servicio"""
    self.subtotal_base_gravada = Decimal('0.00')
    self.subtotal_exento = Decimal('0.00')
    self.subtotal_exportacion = Decimal('0.00')
    
    for item in self.items_factura.all():
        if item.tipo_servicio == 'TRANSPORTE_AEREO_NACIONAL':
            self.subtotal_exento += item.subtotal_item
        elif item.tipo_servicio == 'SERVICIO_EXPORTACION' or not self.cliente_es_residente:
            self.subtotal_exportacion += item.subtotal_item
        else:
            self.subtotal_base_gravada += item.subtotal_item

def _calcular_iva(self):
    """Calcula IVA según bases y tipo de operación"""
    # IVA 16% sobre base gravada
    self.monto_iva_16 = self.subtotal_base_gravada * Decimal('0.16')
    
    # IVA 0% sobre exportaciones (se registra pero es 0)
    # Los exentos no generan IVA

def _calcular_igtf(self):
    """Calcula IGTF si la agencia es SPE y pago en divisas"""
    if self.es_sujeto_pasivo_especial and self.moneda_operacion == 'DIVISA':
        # Base IGTF = Subtotal + IVA (impuesto sobre impuesto)
        base_igtf = (self.subtotal_base_gravada + self.subtotal_exento + 
                    self.subtotal_exportacion + self.monto_iva_16 + self.monto_iva_adicional)
        self.monto_igtf = base_igtf * Decimal('0.03')
    else:
        self.monto_igtf = Decimal('0.00')
```

## Fase 3: Validaciones y Reglas de Negocio (Prioridad Media)

### 3.1 Validaciones Específicas

```python
def clean(self):
    """Validaciones específicas para facturación venezolana"""
    errors = {}
    
    # Validar datos obligatorios según tipo de operación
    if self.tipo_operacion == 'INTERMEDIACION':
        if not self.tercero_rif or not self.tercero_razon_social:
            errors['tercero_rif'] = 'Datos del tercero obligatorios en intermediación'
    
    # Validar datos de boletos aéreos
    if self.items_factura.filter(tipo_servicio='TRANSPORTE_AEREO_NACIONAL').exists():
        for item in self.items_factura.all():
            if not item.nombre_pasajero or not item.numero_boleto:
                errors['items'] = 'Datos de pasajero y boleto obligatorios'
    
    # Validar tasa de cambio si factura en divisas
    if self.moneda_operacion == 'DIVISA' and not self.tasa_cambio_bcv:
        errors['tasa_cambio_bcv'] = 'Tasa BCV obligatoria para facturas en divisas'
    
    # Validar documentación para exportación
    if not self.cliente_es_residente and not hasattr(self, 'documentos_exportacion'):
        errors['cliente'] = 'Documentación de exportación requerida para no residentes'
    
    if errors:
        raise ValidationError(errors)
```

## Fase 4: Plantillas de Factura (Prioridad Media)

### 4.1 Plantillas Específicas por Tipo

- `factura_intermediacion_venezuela.html` - Para venta de boletos
- `factura_paquete_nacional_venezuela.html` - Para paquetes nacionales
- `factura_exportacion_venezuela.html` - Para turismo receptivo

### 4.2 Elementos Obligatorios en Plantillas

- Desglose detallado de impuestos
- Leyendas obligatorias según tipo de operación
- Equivalencias en bolívares para facturas en divisas
- Datos específicos de boletos aéreos
- Información del tercero en intermediación

## Fase 5: Integración con Sistemas Externos (Prioridad Baja)

### 5.1 Imprenta Digital Autorizada

```python
class ImprentaDigitalService:
    """Servicio para obtener números de control fiscal"""
    
    def obtener_numero_control(self, factura):
        """Obtiene número de control de imprenta digital autorizada"""
        pass
    
    def aplicar_firma_digital(self, factura_pdf):
        """Aplica firma digital al PDF de la factura"""
        pass
```

### 5.2 Integración con BCV

```python
class BCVService:
    """Servicio para obtener tasas de cambio oficiales"""
    
    def obtener_tasa_oficial(self, fecha):
        """Obtiene tasa oficial BCV para una fecha"""
        pass
```

## Fase 6: Comandos de Gestión (Prioridad Baja)

### 6.1 Comando de Migración de Facturas

```bash
python manage.py migrar_facturas_venezuela
```

### 6.2 Comando de Validación Fiscal

```bash
python manage.py validar_cumplimiento_fiscal --desde=2025-01-01
```

## Cronograma de Implementación

### Semana 1-2: Fase 1 (Modelo)
- [ ] Crear migración para nuevos campos
- [ ] Actualizar admin interface
- [ ] Crear tests básicos

### Semana 3-4: Fase 2 (Lógica)
- [ ] Implementar métodos de cálculo
- [ ] Crear tests de cálculo fiscal
- [ ] Validar con casos reales

### Semana 5: Fase 3 (Validaciones)
- [ ] Implementar validaciones
- [ ] Tests de validación
- [ ] Documentación

### Semana 6: Fase 4 (Plantillas)
- [ ] Crear plantillas HTML
- [ ] Generar PDFs de prueba
- [ ] Validar formato fiscal

### Semana 7-8: Fase 5-6 (Integraciones)
- [ ] Servicios externos (opcional)
- [ ] Comandos de gestión
- [ ] Tests de integración

## Riesgos y Consideraciones

### Riesgos Técnicos
- Complejidad de cálculos fiscales
- Integración con sistemas externos
- Migración de datos existentes

### Riesgos Legales
- Cambios en normativa fiscal
- Homologación de software
- Responsabilidad compartida

### Mitigación
- Implementación por fases
- Tests exhaustivos
- Asesoría fiscal especializada
- Documentación detallada

## Criterios de Aceptación

### Funcionales
- [ ] Cálculo correcto de IVA según tipo de servicio
- [ ] Cálculo correcto de IGTF para SPE
- [ ] Generación de facturas con formato legal
- [ ] Validación de datos obligatorios
- [ ] Equivalencias en bolívares para divisas

### No Funcionales
- [ ] Performance: < 2 segundos para cálculo de factura
- [ ] Disponibilidad: 99.9% uptime
- [ ] Seguridad: Firma digital válida
- [ ] Usabilidad: Interface intuitiva para usuarios

## Conclusión

Este plan proporciona una hoja de ruta completa para adaptar TravelHub a la normativa fiscal venezolana. La implementación por fases permite un desarrollo controlado y la validación continua del cumplimiento normativo.

La prioridad debe estar en las Fases 1 y 2 (modelo y lógica de cálculo) para tener una base sólida antes del 1 de marzo de 2025, fecha límite para la facturación digital obligatoria.