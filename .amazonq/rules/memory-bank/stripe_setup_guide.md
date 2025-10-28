# Guía de Configuración de Stripe - TravelHub SaaS

**Fecha**: 21 de Enero de 2025  
**Objetivo**: Configurar Stripe para billing de suscripciones SaaS

---

## 📋 Paso 1: Crear Cuenta en Stripe

1. Ir a https://dashboard.stripe.com/register
2. Crear cuenta con email de negocio
3. Completar información de la empresa
4. Activar modo TEST para desarrollo

---

## 🔑 Paso 2: Obtener API Keys

### Test Mode (Desarrollo)

1. Ir a https://dashboard.stripe.com/test/apikeys
2. Copiar las claves:
   - **Publishable key**: `pk_test_...` (para frontend)
   - **Secret key**: `sk_test_...` (para backend)

### Agregar a .env

```env
STRIPE_SECRET_KEY=sk_test_51ABC...
STRIPE_PUBLISHABLE_KEY=pk_test_51ABC...
```

---

## 💰 Paso 3: Crear Productos y Precios

### Opción A: Dashboard Manual

1. Ir a https://dashboard.stripe.com/test/products
2. Click "Add product"

**Plan BASIC**:
- Name: `TravelHub Basic`
- Description: `Plan Básico - 3 usuarios, 200 ventas/mes`
- Pricing: `$29.00 USD / month`
- Recurring: Monthly
- Copiar `Price ID`: `price_1ABC...`

**Plan PRO**:
- Name: `TravelHub Pro`
- Description: `Plan Profesional - 10 usuarios, 1000 ventas/mes`
- Pricing: `$99.00 USD / month`
- Recurring: Monthly
- Copiar `Price ID`: `price_1DEF...`

**Plan ENTERPRISE**:
- Name: `TravelHub Enterprise`
- Description: `Plan Enterprise - Usuarios ilimitados, ventas ilimitadas`
- Pricing: `$299.00 USD / month`
- Recurring: Monthly
- Copiar `Price ID`: `price_1GHI...`

### Opción B: Script Automático

```python
# scripts/crear_productos_stripe.py
import stripe
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Crear producto BASIC
basic_product = stripe.Product.create(
    name="TravelHub Basic",
    description="Plan Básico - 3 usuarios, 200 ventas/mes"
)
basic_price = stripe.Price.create(
    product=basic_product.id,
    unit_amount=2900,  # $29.00 en centavos
    currency="usd",
    recurring={"interval": "month"}
)
print(f"BASIC Price ID: {basic_price.id}")

# Crear producto PRO
pro_product = stripe.Product.create(
    name="TravelHub Pro",
    description="Plan Profesional - 10 usuarios, 1000 ventas/mes"
)
pro_price = stripe.Price.create(
    product=pro_product.id,
    unit_amount=9900,  # $99.00 en centavos
    currency="usd",
    recurring={"interval": "month"}
)
print(f"PRO Price ID: {pro_price.id}")

# Crear producto ENTERPRISE
enterprise_product = stripe.Product.create(
    name="TravelHub Enterprise",
    description="Plan Enterprise - Usuarios ilimitados"
)
enterprise_price = stripe.Price.create(
    product=enterprise_product.id,
    unit_amount=29900,  # $299.00 en centavos
    currency="usd",
    recurring={"interval": "month"}
)
print(f"ENTERPRISE Price ID: {enterprise_price.id}")
```

### Agregar Price IDs a .env

```env
STRIPE_PRICE_ID_BASIC=price_1ABC...
STRIPE_PRICE_ID_PRO=price_1DEF...
STRIPE_PRICE_ID_ENTERPRISE=price_1GHI...
```

---

## 🔔 Paso 4: Configurar Webhooks

Los webhooks permiten que Stripe notifique a tu backend cuando ocurren eventos (pago exitoso, suscripción cancelada, etc.)

### Desarrollo Local (ngrok/cloudflare)

1. Exponer tu servidor local:
   ```bash
   # Opción 1: ngrok
   ngrok http 8000
   
   # Opción 2: cloudflare
   cloudflared tunnel --url http://localhost:8000
   ```

2. Copiar URL pública (ej: `https://abc123.ngrok-free.app`)

3. Ir a https://dashboard.stripe.com/test/webhooks
4. Click "Add endpoint"
5. Endpoint URL: `https://abc123.ngrok-free.app/api/billing/webhook/`
6. Events to send:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

7. Copiar `Signing secret`: `whsec_...`

### Agregar a .env

```env
STRIPE_WEBHOOK_SECRET=whsec_ABC123...
```

### Producción (Railway/Render)

1. Usar URL de producción: `https://tu-app.railway.app/api/billing/webhook/`
2. Mismos eventos
3. Actualizar `STRIPE_WEBHOOK_SECRET` en variables de entorno de producción

---

## 🧪 Paso 5: Probar Integración

### Test Cards de Stripe

```
Tarjeta exitosa:     4242 4242 4242 4242
Tarjeta rechazada:   4000 0000 0000 0002
Requiere 3D Secure:  4000 0025 0000 3155

Fecha: Cualquier fecha futura
CVC: Cualquier 3 dígitos
ZIP: Cualquier 5 dígitos
```

### Flujo de Prueba

1. **Login como demo**:
   ```
   Usuario: demo
   Password: demo2025
   ```

2. **Ver planes disponibles**:
   ```bash
   curl http://localhost:8000/api/billing/plans/
   ```

3. **Crear checkout session**:
   ```bash
   curl -X POST http://localhost:8000/api/billing/checkout/ \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"plan": "PRO"}'
   ```

4. **Completar pago** en Stripe Checkout

5. **Verificar webhook** recibido en logs

6. **Verificar suscripción**:
   ```bash
   curl http://localhost:8000/api/billing/subscription/ \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

---

## 📊 Paso 6: Monitorear en Dashboard

### Stripe Dashboard

- **Payments**: https://dashboard.stripe.com/test/payments
- **Customers**: https://dashboard.stripe.com/test/customers
- **Subscriptions**: https://dashboard.stripe.com/test/subscriptions
- **Webhooks**: https://dashboard.stripe.com/test/webhooks
- **Logs**: https://dashboard.stripe.com/test/logs

### Verificar

- ✅ Checkout sessions creadas
- ✅ Customers creados con email correcto
- ✅ Subscriptions activas
- ✅ Webhooks entregados (200 OK)
- ✅ Invoices pagadas

---

## 🚀 Paso 7: Migrar a Producción

### Activar Cuenta

1. Ir a https://dashboard.stripe.com/account/onboarding
2. Completar información de negocio
3. Verificar identidad
4. Agregar cuenta bancaria

### Obtener Live Keys

1. Ir a https://dashboard.stripe.com/apikeys
2. Copiar claves de producción:
   - `pk_live_...`
   - `sk_live_...`

### Actualizar .env de Producción

```env
STRIPE_SECRET_KEY=sk_live_ABC...
STRIPE_PUBLISHABLE_KEY=pk_live_ABC...
STRIPE_WEBHOOK_SECRET=whsec_LIVE...
STRIPE_PRICE_ID_BASIC=price_LIVE_BASIC...
STRIPE_PRICE_ID_PRO=price_LIVE_PRO...
STRIPE_PRICE_ID_ENTERPRISE=price_LIVE_ENTERPRISE...
```

### Crear Productos en Live Mode

Repetir Paso 3 pero en modo LIVE (sin `/test/` en URLs)

### Configurar Webhook en Live

Repetir Paso 4 pero con URL de producción

---

## 🔒 Seguridad

### Mejores Prácticas

1. **Nunca exponer Secret Key** en frontend
2. **Validar webhooks** con signing secret
3. **Usar HTTPS** en producción
4. **Logs de auditoría** para todos los eventos
5. **Rate limiting** en endpoints de billing

### Verificación de Webhooks

El código ya implementa verificación:

```python
# core/views/billing_views.py
sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
event = stripe.Webhook.construct_event(
    payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
)
```

---

## 📝 Checklist de Configuración

### Desarrollo

- [ ] Cuenta Stripe creada
- [ ] Test API keys en .env
- [ ] Productos creados en test mode
- [ ] Price IDs en .env
- [ ] ngrok/cloudflare ejecutándose
- [ ] Webhook configurado con URL pública
- [ ] Webhook secret en .env
- [ ] Test con tarjeta 4242...
- [ ] Webhook recibido correctamente

### Producción

- [ ] Cuenta Stripe activada
- [ ] Live API keys en .env producción
- [ ] Productos creados en live mode
- [ ] Live Price IDs en .env producción
- [ ] Webhook configurado con URL producción
- [ ] Live webhook secret en .env producción
- [ ] Test con tarjeta real
- [ ] Monitoreo activo en dashboard

---

## 🆘 Troubleshooting

### Error: "No such price"

- Verificar que `STRIPE_PRICE_ID_*` sean correctos
- Verificar que estés en el modo correcto (test/live)

### Error: "Invalid API Key"

- Verificar que `STRIPE_SECRET_KEY` sea correcto
- Verificar que no tenga espacios al inicio/final

### Webhook no recibe eventos

- Verificar que ngrok/cloudflare esté ejecutándose
- Verificar URL en Stripe dashboard
- Verificar que Django esté ejecutándose
- Ver logs en Stripe dashboard > Webhooks > Attempts

### Error: "Signature verification failed"

- Verificar que `STRIPE_WEBHOOK_SECRET` sea correcto
- Verificar que el endpoint sea `/api/billing/webhook/` exacto

---

## 📚 Recursos

- **Stripe Docs**: https://stripe.com/docs
- **API Reference**: https://stripe.com/docs/api
- **Testing**: https://stripe.com/docs/testing
- **Webhooks**: https://stripe.com/docs/webhooks
- **Dashboard**: https://dashboard.stripe.com

---

**Última actualización**: 21 de Enero de 2025  
**Estado**: Guía completa para desarrollo y producción  
**Autor**: Amazon Q Developer
