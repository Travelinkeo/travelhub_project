# TravelHub Business Model & SaaS Tiers 💰

TravelHub es una plataforma SaaS B2B diseñada para la rentabilidad de las agencias de viajes y la escalabilidad del proveedor de software.

## 1. Modelo de Monetización
El sistema genera ingresos a través de suscripciones mensuales recurrentes (MRR) gestionadas por **Stripe**.

## 2. Niveles de Suscripción (Tiers)

### 🆓 Trial (Prueba Gratuita)
- **Costo:** $0.
- **Duración:** 30 días.
- **Límites:** 1 Usuario, 50 Ventas/mes.
- **Objetivo:** Conversión de leads y validación de valor.

### 🥉 Plan Básico (Start-up)
- **Costo:** $29/mes.
- **Límites:** 3 Usuarios, 200 Ventas/mes.
- **Incluye:** Parser de Boletos, Contabilidad básica, CRM.

### 🥈 Plan Profesional (Growth)
- **Costo:** $99/mes.
- **Límites:** 10 Usuarios, 1000 Ventas/mes.
- **Incluye:** Todo lo anterior + Marketing IA Hub (Imagen 3), Automatización de WhatsApp, Analytics Avanzados.

### 🥇 Plan Enterprise (Consolidador)
- **Costo:** $299/mes.
- **Límites:** Usuarios ilimitados, Ventas ilimitadas.
- **Incluye:** Soporte prioritario, Custom branding, API Access, Multimoneda avanzada.

## 3. Control de Cuotas (SaaS Limits)
El sistema utiliza el `SaaSLimitMiddleware` para verificar en cada acción crítica (crear venta, crear usuario) si la agencia ha excedido los límites de su plan actual.
- Al alcanzar el límite, se redirige al usuario a la página de **Upgrade**.

## 4. Estrategia de Retención
- **Incentivos IA:** Las funciones de IA actúan como "ganchos" para subir de nivel (Upgrade) a planes superiores.
- **Stickiness:** Una vez que la contabilidad y las ventas están automatizadas, el costo de cambio para la agencia es muy alto.
