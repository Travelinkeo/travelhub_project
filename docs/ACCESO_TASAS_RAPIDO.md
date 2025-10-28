# Acceso Rápido a Tasas de Cambio

## ✅ Tasa Creada

Ya creé una tasa manual para hoy:
- **Fecha**: 18 de Octubre de 2025
- **Tasa**: 52.50 Bs/USD
- **Fuente**: Manual

## 📍 Ver en Django Admin

1. **Iniciar servidor**:
   ```bash
   python manage.py runserver
   ```

2. **Ir a**: http://127.0.0.1:8000/admin/

3. **Login**:
   - Usuario: `Armando3105`
   - Password: `Linkeo1331*`

4. **Navegar a**: Contabilidad → Tasas de Cambio BCV

5. **Verás**: La tasa de hoy (52.50 Bs/USD)

## 🔧 Crear Más Tasas Manualmente

### Desde Django Admin
1. Ir a: Contabilidad → Tasas de Cambio BCV
2. Click en "Agregar Tasa de Cambio BCV"
3. Llenar:
   - Fecha: Hoy
   - Tasa BSD/USD: 52.50 (o la tasa actual)
   - Fuente: Manual
4. Guardar

### Desde Comando
```bash
python manage.py shell
```

```python
from contabilidad.models import TasaCambioBCV
from datetime import date
from decimal import Decimal

# Crear tasa de hoy
TasaCambioBCV.objects.create(
    fecha=date.today(),
    tasa_bsd_por_usd=Decimal('52.50'),
    fuente='Manual'
)
```

## 🌐 API Endpoints

### Endpoint 1: Solo BCV
```
GET http://127.0.0.1:8000/api/contabilidad/api/tasas/bcv/
```

**Respuesta**:
```json
{
  "valor": 52.50,
  "fecha": "2025-10-18"
}
```

### Endpoint 2: Todas las Tasas
```
GET http://127.0.0.1:8000/api/contabilidad/api/tasas/actuales/
```

**Respuesta**:
```json
{
  "bcv": {
    "valor": 52.50,
    "fecha": "2025-10-18",
    "nombre": "BCV Oficial (DB)"
  }
}
```

## 💻 Integración Frontend

```javascript
// En tu componente Header
useEffect(() => {
  fetch('http://127.0.0.1:8000/api/contabilidad/api/tasas/bcv/')
    .then(res => res.json())
    .then(data => {
      console.log('Tasa BCV:', data.valor);
      setTasaBCV(data.valor);
    })
    .catch(err => console.error('Error:', err));
}, []);
```

## 🔄 Sincronización Automática

Las APIs externas no están disponibles actualmente, pero puedes:

### Opción 1: Crear Tasas Manualmente
Cada día, crear la tasa en Django Admin.

### Opción 2: Script Personalizado
Crear un script que obtenga la tasa de otra fuente y la guarde.

### Opción 3: Usar BCV Scraper Original
El `bcv_client.py` original hace scraping del sitio del BCV:

```bash
python manage.py shell
```

```python
from contabilidad.bcv_client import BCVClient

# Intentar obtener del BCV directamente
tasa = BCVClient.obtener_tasa_actual()
if tasa:
    BCVClient.actualizar_tasa_db(tasa, fuente="BCV Web")
    print(f"Tasa actualizada: {tasa}")
```

## 📊 Verificar Tasa Actual

```bash
python manage.py shell -c "from contabilidad.models import TasaCambioBCV; from datetime import date; t = TasaCambioBCV.objects.filter(fecha=date.today()).first(); print(f'Tasa: {t.tasa_bsd_por_usd} Bs/USD' if t else 'No hay tasa')"
```

## ✅ Estado Actual

- ✅ Tasa de hoy creada: 52.50 Bs/USD
- ✅ Modelo funcionando
- ✅ Django Admin accesible
- ✅ API endpoints configurados
- ⏳ Frontend pendiente de integración

## 🎯 Próximo Paso

1. **Iniciar servidor**: `python manage.py runserver`
2. **Verificar en Admin**: http://127.0.0.1:8000/admin/contabilidad/tasacambiobcv/
3. **Probar API**: http://127.0.0.1:8000/api/contabilidad/api/tasas/bcv/
4. **Integrar en Frontend**: Usar el código JavaScript de arriba

---

**Tasa actual**: 52.50 Bs/USD (Manual)  
**Última actualización**: 18 de Octubre de 2025
