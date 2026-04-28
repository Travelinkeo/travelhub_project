# Fix: Confusión de Parsers y Errores de BD - Enero 2025

**Fecha**: 25 de Enero de 2025  
**Problemas**: 3 errores críticos en el sistema de parseo de boletos

---

## 🐛 Problemas Identificados

### 1. Confusión entre KIU y SABRE
**Síntoma**: "No se pudo determinar el GDS del boleto; intentando con Sabre como fallback"

**Causa**: Las heurísticas de detección no eran suficientemente específicas. Algunos boletos tenían características de ambos sistemas.

**Solución**: Heurísticas mutuamente excluyentes
```python
# SABRE: Debe tener marcadores SABRE Y NO tener marcadores KIU
is_sabre = ('ETICKET RECEIPT' in text or 'E-TICKET RECEIPT' in text) and \
           ('RESERVATION CODE' in text or 'RECORD LOCATOR' in text)
is_not_kiu = 'KIUSYS.COM' not in text and 'PASSENGER ITINERARY RECEIPT' not in text

if is_sabre and is_not_kiu:
    # Usar parser SABRE

# KIU: Marcadores específicos de KIU
is_kiu = 'KIUSYS.COM' in text or \
         'PASSENGER ITINERARY RECEIPT' in text or \
         ('ISSUE AGENT/AGENTE EMISOR' in text and 'FROM/TO' in text)

if is_kiu:
    # Usar parser KIU
```

---

### 2. Campo formato_detectado Muy Corto
**Síntoma**: "el valor es demasiado largo para el tipo character varying(10)"

**Causa**: El campo `formato_detectado` tenía `max_length=10`, pero algunos valores como `'ERROR_FORMATO'` tienen 13 caracteres.

**Solución**: Aumentado a `max_length=20`
```python
# core/models/boletos.py
formato_detectado = models.CharField(
    _("Formato Detectado"),
    max_length=20,  # Aumentado de 10 a 20
    choices=FormatoDetectado.choices,
    default=FormatoDetectado.OTRO,
    blank=True
)
```

**Migración**: `0032_aumentar_formato_detectado.py`

---

### 3. Llave Duplicada venta_asociada_id
**Síntoma**: 
```
IntegrityError: llave duplicada viola restricción de unicidad 
«core_boletoimportado_venta_asociada_id_key»
DETAIL: Ya existe la llave (venta_asociada_id)=(99).
```

**Causa**: El campo `venta_asociada` es `OneToOneField`, pero el signal intentaba asociar múltiples boletos a la misma venta.

**Solución**: Verificar si ya existe otro boleto asociado antes de intentar asociar
```python
# core/signals.py
# Verificar si ya existe otro boleto con esta venta
boleto_existente = BoletoImportado.objects.filter(
    venta_asociada=venta
).exclude(pk=instance.pk).first()

if boleto_existente:
    logger.warning(f"Ya existe BoletoImportado {boleto_existente.pk} asociado a Venta {venta.pk}.")
else:
    instance.venta_asociada = venta
    instance.save(update_fields=['venta_asociada'])
```

---

## 📁 Archivos Modificados

### 1. core/ticket_parser.py
- Heurísticas de detección más específicas
- SABRE verifica que NO sea KIU
- KIU tiene 3 criterios de detección

### 2. core/models/boletos.py
- Campo `formato_detectado` aumentado a 20 caracteres

### 3. core/signals.py
- Verificación de boleto existente antes de asociar venta
- Evita IntegrityError por llave duplicada

### 4. core/migrations/0032_aumentar_formato_detectado.py
- Migración para aumentar tamaño del campo

---

## ✅ Verificación

### Probar Detección de GDS
```python
from core.ticket_parser import extract_data_from_text

# Boleto KIU
texto_kiu = """
KIUSYS.COM
PASSENGER ITINERARY RECEIPT
...
"""
data = extract_data_from_text(texto_kiu)
assert data['SOURCE_SYSTEM'] == 'KIU'

# Boleto SABRE
texto_sabre = """
ETICKET RECEIPT
RESERVATION CODE: ABC123
...
"""
data = extract_data_from_text(texto_sabre)
assert data['SOURCE_SYSTEM'] == 'SABRE'
```

### Probar Campo formato_detectado
```python
from core.models import BoletoImportado

boleto = BoletoImportado.objects.create(
    formato_detectado='ERROR_FORMATO'  # 13 caracteres - ahora funciona
)
```

### Probar Asociación de Venta
```python
from core.models import BoletoImportado, Venta

venta = Venta.objects.create(localizador='ABC123')

# Primer boleto - OK
boleto1 = BoletoImportado.objects.create(
    localizador_pnr='ABC123',
    datos_parseados={'normalized': {'reservation_code': 'ABC123'}}
)
# Signal asocia boleto1 a venta

# Segundo boleto - NO asocia (ya existe boleto1)
boleto2 = BoletoImportado.objects.create(
    localizador_pnr='ABC123',
    datos_parseados={'normalized': {'reservation_code': 'ABC123'}}
)
# Signal detecta que boleto1 ya está asociado y no asocia boleto2
```

---

## 🎯 Beneficios

1. **Detección más precisa**: Menos falsos positivos en identificación de GDS
2. **Sin errores de BD**: Campo suficientemente grande para todos los valores
3. **Sin duplicados**: Solo un boleto por venta (OneToOneField respetado)
4. **Logs informativos**: Warnings cuando hay conflictos

---

## 📝 Notas Importantes

### OneToOneField vs ForeignKey
El campo `venta_asociada` es `OneToOneField`, lo que significa:
- ✅ **1 boleto → 1 venta** (correcto)
- ❌ **Múltiples boletos → 1 venta** (no permitido)

Si necesitas múltiples boletos por venta, cambiar a:
```python
venta_asociada = models.ForeignKey(
    Venta, 
    on_delete=models.SET_NULL, 
    blank=True, 
    null=True, 
    related_name='boletos_importados'  # Plural
)
```

### Fallback a SABRE
Si ningún GDS es detectado, el sistema intenta con SABRE como último recurso. Esto es útil para boletos con formato no estándar.

---

**Última actualización**: 25 de Enero de 2025  
**Estado**: ✅ 3 problemas corregidos  
**Autor**: Amazon Q Developer
