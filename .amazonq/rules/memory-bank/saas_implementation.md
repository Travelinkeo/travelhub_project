# Implementación SaaS Multi-Tenant - TravelHub

**Fecha**: 21 de Enero de 2025  
**Estado**: ✅ Implementado y funcional

---

## 📋 Resumen

TravelHub ahora es un **SaaS Multi-Tenant** con 4 planes de suscripción, integración completa con Stripe, y límites por plan.

---

## 🏗️ Arquitectura

### Modelo Multi-Tenant

Cada **Agencia** es un tenant independiente con:
- Plan de suscripción (FREE, BASIC, PRO, ENTERPRISE)
- Límites de usuarios y ventas
- Datos aislados por agencia
- Facturación independiente vía Stripe

### Planes y Precios

| Plan | Precio | Usuarios | Ventas/Mes | Trial |
|------|--------|----------|------------|-------|
| **FREE** | $0 | 1 | 50 | 30 días |
| **BASIC** | $29/mes | 3 | 200 | No |
| **PRO** | $99/mes | 10 | 1000 | No |
| **ENTERPRISE** | $299/mes | Ilimitado | Ilimitado | No |

---

## 🗄️ Modelo de Datos

### Agencia (core/models/agencia.py)

```python
class Agencia(models.Model):
    # Información básica
    nombre = models.CharField(max_length=200, unique=True)
    rif = models.CharField(max_length=20)
    iata = models.CharField(max_length=20)
    
    # Plan SaaS
    PLAN_CHOICES = [
        ('FREE', 'Gratuito (Trial 30 días)'),
        ('BASIC', 'Básico - $29/mes'),
        ('PRO', 'Profesional - $99/mes'),
        ('ENTERPRISE', 'Enterprise - Personalizado'),
    ]
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE')
    fecha_inicio_plan = models.DateField(default=timezone.now)
    fecha_fin_trial = models.DateField(null=True, blank=True)
    
    # Límites por plan
    limite_usuarios = models.IntegerField(default=1)
    limite_ventas_mes = models.IntegerField(default=50)
    ventas_mes_actual = models.IntegerField(default=0)
    
    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    
    # Flags
    es_demo = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)
    
    def puede_crear_venta(self):
        """Verifica si puede crear más ventas este mes."""
        if self.plan == 'ENTERPRISE':
            return True
        return self.ventas_mes_actual < self.limite_ventas_mes
    
    def puede_agregar_usuario(self):
        """Verifica si puede agregar más usuarios."""
        if self.plan == 'ENTERPRISE':
            return True
        return self.usuarios.filter(activo=True).count() < self.limite_usuarios
```

---

## 🔒 Middleware de Límites

### SaaSLimitMiddleware (core/middleware_saas.py)

Intercepta requests y verifica límites antes de permitir operaciones:

```python
class SaaSLimitMiddleware:
    def __call__(self, request):
        # Verificar límites en POST de ventas
        if request.path.startswith('/api/ventas/') and request.method == 'POST':
            agencia = obtener_agencia_del_usuario(request.user)
            if not agencia.puede_crear_venta():
                return JsonResponse({
                    'error': 'Límite de ventas alcanzado',
                    'plan_actual': agencia.get_plan_display(),
                    'limite': agencia.limite_ventas_mes,
                    'usado': agencia.ventas_mes_actual,
                    'mensaje': 'Actualiza tu plan para crear más ventas'
                }, status=403)
```

---

## 💳 Integración Stripe

### Billing Views (core/views/billing_views.py)

#### 1. Ver Planes Disponibles

```http
GET /api/billing/plans/
```

Respuesta:
```json
{
  "plans": [
    {
      "id": "FREE",
      "name": "Gratuito",
      "price": 0,
      "features": ["1 usuario", "50 ventas/mes", "Trial 30 días"]
    },
    {
      "id": "BASIC",
      "name": "Básico",
      "price": 29,
      "stripe_price_id": "price_1ABC...",
      "features": ["3 usuarios", "200 ventas/mes", "Soporte email"]
    }
  ]
}
```

#### 2. Ver Suscripción Actual

```http
GET /api/billing/subscription/
Authorization: Bearer <jwt_token>
```

Respuesta:
```json
{
  "plan": "PRO",
  "plan_display": "Profesional - $99/mes",
  "limite_usuarios": 10,
  "limite_ventas_mes": 1000,
  "ventas_mes_actual": 45,
  "fecha_inicio": "2025-01-21",
  "fecha_fin_trial": null,
  "stripe_customer_id": "cus_ABC123",
  "stripe_subscription_id": "sub_DEF456"
}
```

#### 3. Crear Checkout Session

```http
POST /api/billing/checkout/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "plan": "PRO"
}
```

Respuesta:
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_ABC123..."
}
```

#### 4. Webhook de Stripe

```http
POST /api/billing/webhook/
Stripe-Signature: t=...,v1=...

{
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "customer": "cus_ABC123",
      "subscription": "sub_DEF456"
    }
  }
}
```

Eventos manejados:
- `checkout.session.completed` - Actualiza agencia con customer_id y subscription_id
- `customer.subscription.updated` - Actualiza plan y límites
- `customer.subscription.deleted` - Downgrade a FREE
- `invoice.payment_succeeded` - Log de pago exitoso
- `invoice.payment_failed` - Notificar fallo de pago

#### 5. Cancelar Suscripción

```http
POST /api/billing/cancel/
Authorization: Bearer <jwt_token>
```

---

## 🎯 Flujo Completo de Suscripción

### 1. Usuario se Registra (FREE)

```python
# Al crear usuario, se crea agencia FREE automáticamente
agencia = Agencia.objects.create(
    nombre="Mi Agencia",
    propietario=user,
    plan='FREE',
    fecha_fin_trial=date.today() + timedelta(days=30),
    limite_usuarios=1,
    limite_ventas_mes=50
)
```

### 2. Usuario Usa Trial (30 días)

- Puede crear hasta 50 ventas/mes
- 1 usuario
- Todas las funcionalidades disponibles

### 3. Trial Expira

- Middleware bloquea creación de ventas
- Mensaje: "Tu trial ha expirado. Actualiza tu plan."

### 4. Usuario Elige Plan (BASIC/PRO/ENTERPRISE)

```javascript
// Frontend
const response = await fetch('/api/billing/checkout/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ plan: 'PRO' })
});

const { checkout_url } = await response.json();
window.location.href = checkout_url;  // Redirigir a Stripe Checkout
```

### 5. Usuario Completa Pago en Stripe

- Ingresa datos de tarjeta
- Stripe procesa pago
- Stripe envía webhook a `/api/billing/webhook/`

### 6. Webhook Actualiza Agencia

```python
# core/views/billing_views.py
if event.type == 'checkout.session.completed':
    session = event.data.object
    agencia.stripe_customer_id = session.customer
    agencia.stripe_subscription_id = session.subscription
    agencia.plan = plan_elegido
    agencia.actualizar_limites_por_plan()
    agencia.save()
```

### 7. Usuario Tiene Acceso Completo

- Límites actualizados según plan
- Facturación automática mensual
- Puede cancelar en cualquier momento

---

## 🧪 Testing

### Agencia Demo

```bash
python manage.py crear_agencia_demo
```

Crea:
- Usuario: `demo` / `demo2025`
- Agencia: "TravelHub Demo"
- Plan: PRO (1 año trial)
- Flag: `es_demo=True`
- 2 clientes de ejemplo

### Test Cards de Stripe

```
Exitosa:           4242 4242 4242 4242
Rechazada:         4000 0000 0000 0002
Requiere 3D:       4000 0025 0000 3155
Fondos insuf.:     4000 0000 0000 9995
```

---

## 📊 Monitoreo

### Métricas Clave

1. **MRR (Monthly Recurring Revenue)**
   ```sql
   SELECT plan, COUNT(*) as agencias, 
          SUM(CASE 
            WHEN plan='BASIC' THEN 29
            WHEN plan='PRO' THEN 99
            WHEN plan='ENTERPRISE' THEN 299
            ELSE 0
          END) as mrr
   FROM core_agencia
   WHERE activa=true AND plan != 'FREE'
   GROUP BY plan;
   ```

2. **Churn Rate**
   ```sql
   SELECT COUNT(*) as cancelaciones
   FROM core_agencia
   WHERE activa=false 
   AND fecha_actualizacion >= NOW() - INTERVAL '30 days';
   ```

3. **Uso por Plan**
   ```sql
   SELECT plan, 
          AVG(ventas_mes_actual) as promedio_ventas,
          AVG(ventas_mes_actual::float / limite_ventas_mes * 100) as porcentaje_uso
   FROM core_agencia
   WHERE activa=true
   GROUP BY plan;
   ```

---

## 🚀 Deployment

### Variables de Entorno Requeridas

```env
# Stripe (Test)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_BASIC=price_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_ENTERPRISE=price_...
```

### Railway.app

1. Agregar variables de entorno en dashboard
2. Deploy automático desde GitHub
3. Configurar webhook con URL de Railway

### Render.com

1. Agregar variables en Environment
2. Deploy desde GitHub
3. Configurar webhook con URL de Render

---

## 📝 Próximos Pasos

### Funcionalidades Adicionales

1. **Dashboard de Billing**
   - Historial de facturas
   - Próximo pago
   - Método de pago

2. **Notificaciones**
   - Email cuando trial expira
   - Email cuando pago falla
   - Email de bienvenida al suscribirse

3. **Analytics**
   - Uso de límites en tiempo real
   - Proyección de costos
   - Recomendación de plan

4. **Upgrades/Downgrades**
   - Cambiar plan sin cancelar
   - Proration automática
   - Confirmación de cambio

---

## 🔗 Recursos

- **Guía de Stripe**: `.amazonq/rules/memory-bank/stripe_setup_guide.md`
- **Script de productos**: `scripts/crear_productos_stripe.py`
- **Billing views**: `core/views/billing_views.py`
- **Middleware**: `core/middleware_saas.py`
- **Modelo**: `core/models/agencia.py`

---

**Última actualización**: 21 de Enero de 2025  
**Estado**: ✅ Completamente implementado  
**Autor**: Amazon Q Developer
