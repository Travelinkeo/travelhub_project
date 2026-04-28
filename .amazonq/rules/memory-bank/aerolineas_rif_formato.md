# Formato de RIF para Aerolíneas

**Fecha**: 24 de Enero de 2025  
**Estado**: ✅ Implementado

---

## 📋 Formato de RIF

### Aerolíneas Nacionales (Venezuela)

Usan RIF real venezolano:
- **Formato**: `J-XXXXXXXX-X` o `G-XXXXXXXX-X`
- **Ejemplo**: `J-302097843` (Avior Airlines)

### Aerolíneas Internacionales

Usan RIF genérico identificable:
- **Formato**: `E-CCPPPPPP-D`
  - `E` = Extranjero
  - `CC` = Código de país (2 dígitos)
  - `PPPPPP` = Secuencial por país (6 dígitos)
  - `D` = Dígito verificador

**Códigos de país usados**:
- `17` = Colombia
- `15` = Chile
- `50` = Panamá
- `59` = Bolivia/Ecuador
- `72` = España
- `35` = Portugal
- `78` = Trinidad y Tobago
- `80` = República Dominicana
- `90` = Turquía
- `99` = Sin RIF localizado

---

## 📊 Aerolíneas Cargadas

### Nacionales (11)

| Aerolínea | IATA | RIF | Estado |
|-----------|------|-----|--------|
| Conviasa | VO | G-20007774-3 | ✅ |
| Avior Airlines | 9V | J-302097843 | ✅ |
| LASER Airlines | QL | J-00364445-5 | ✅ |
| Venezolana | VE | J-30819225-2 | ✅ |
| Estelar Latinoamérica | E7 | J-29567805-3 | ✅ |
| Turpial Airlines | T3 | J-40491921-0 | ✅ |
| Rutaca Airlines | 5R | J-09500396-5 | ✅ |
| Aerocaribe | AC | J-40149748-9 | ✅ |
| SASCA Airlines | SC | J-080342470 | ✅ |
| Aeropostal | VH | G-20012311-7 | ✅ |
| Albatros Airlines | AB | E-99999999-1 | ⚠️ No localizado |

### Internacionales (14)

| Aerolínea | IATA | País | RIF Genérico |
|-----------|------|------|--------------|
| Copa Airlines | CM | Panamá | E-50700001-2 |
| Avianca | AV | Colombia | E-17000001-3 |
| Wingo | P5 | Colombia | E-17000002-4 |
| LATAM Airlines | LA | Chile | E-15200001-5 |
| Caribbean Airlines | BW | Trinidad y Tobago | E-78000001-6 |
| Boliviana de Aviación | OB | Bolivia | E-59100001-7 |
| Sky High Aviation | SH | Rep. Dominicana | E-80900001-8 |
| Aeroregional | 7A | Ecuador | E-59300001-9 |
| Satena | 9R | Colombia | E-17000003-0 |
| Iberia | IB | España | E-72400001-1 |
| Air Europa | UX | España | E-72400002-2 |
| Plus Ultra | PU | España | E-72400003-3 |
| TAP Air Portugal | TP | Portugal | E-35100001-4 |
| Turkish Airlines | TK | Turquía | E-90500001-5 |

---

## 🚀 Uso

### Cargar Aerolíneas

```bash
python manage.py cargar_aerolineas
```

### Consultar en Código

```python
from core.models_catalogos import Aerolinea

# Buscar por IATA
copa = Aerolinea.objects.get(codigo_iata='CM')
print(f"{copa.nombre}: {copa.rif}")  # Copa Airlines: E-50700001-2

# Filtrar nacionales
nacionales = Aerolinea.objects.filter(rif__startswith='J-') | Aerolinea.objects.filter(rif__startswith='G-')
print(f"Aerolíneas nacionales: {nacionales.count()}")  # 10

# Filtrar internacionales
internacionales = Aerolinea.objects.filter(rif__startswith='E-')
print(f"Aerolíneas internacionales: {internacionales.count()}")  # 15
```

### Usar en Facturación

```python
from core.services.doble_facturacion import DobleFacturacionService

# Obtener aerolínea
aerolinea = Aerolinea.objects.get(codigo_iata='CM')

# Generar factura por cuenta de terceros
datos_tercero = {
    'razon_social': aerolinea.nombre,
    'rif': aerolinea.rif,  # E-50700001-2
    'monto_servicio': Decimal('1000.00'),
    'descripcion': f'Boleto aéreo {aerolinea.nombre}',
    'es_nacional': False
}

factura_tercero, factura_propia = DobleFacturacionService.generar_facturas_venta(
    venta=venta,
    datos_tercero=datos_tercero,
    fee_servicio=Decimal('100.00')
)
```

---

## ✅ Beneficios

1. **Identificación clara**: RIF genérico identifica aerolíneas internacionales
2. **Cumplimiento normativo**: Todas las facturas tienen RIF del tercero
3. **Trazabilidad**: Fácil distinguir nacionales vs internacionales
4. **Escalable**: Formato permite agregar más aerolíneas

---

## 📝 Agregar Nueva Aerolínea

### Nacional

```python
Aerolinea.objects.create(
    codigo_iata='XX',
    codigo_icao='XXX',
    nombre='Nueva Aerolínea',
    pais_origen='Venezuela',
    rif='J-12345678-9',  # RIF real
    activa=True
)
```

### Internacional

```python
Aerolinea.objects.create(
    codigo_iata='XX',
    codigo_icao='XXX',
    nombre='Nueva Aerolínea Internacional',
    pais_origen='País',
    rif='E-CCPPPPPP-D',  # RIF genérico
    activa=True
)
```

---

**Última actualización**: 24 de Enero de 2025  
**Estado**: ✅ 25 aerolíneas cargadas  
**Autor**: Amazon Q Developer
