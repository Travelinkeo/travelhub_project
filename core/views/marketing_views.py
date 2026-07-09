"""
Vistas públicas de marketing y landing page.

Muestra la landing page pública para visitantes no autenticados
y la página de precios.
"""

from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def public_landing(request):
    """Landing page pública para visitantes no autenticados."""
    # Usuarios autenticados → dashboard
    if request.user.is_authenticated:
        from django.shortcuts import redirect

        return redirect("bookings:modern_dashboard")

    return render(
        request,
        "marketing/public_landing.html",
        {
            "plans": [
                {
                    "name": "Básico",
                    "price": 29,
                    "currency": "USD",
                    "period": "mes",
                    "description": "Para agencias pequeñas o freelancers",
                    "features": [
                        "Hasta 3 usuarios",
                        "Gestión de boletos aéreos",
                        "CRM con IA básico",
                        "Facturación VEN-NIF",
                        "Soporte por email",
                    ],
                    "cta": "Probar gratis",
                    "highlight": False,
                },
                {
                    "name": "Pro",
                    "price": 99,
                    "currency": "USD",
                    "period": "mes",
                    "description": "Para agencias en crecimiento",
                    "features": [
                        "Hasta 15 usuarios",
                        "Todo lo de Básico +",
                        "API pública + Webhooks",
                        "Integración Xero contable",
                        "WhatsApp Bot automation",
                        "Reportes exportables",
                        "Soporte prioritario",
                    ],
                    "cta": "Probar gratis",
                    "highlight": True,
                },
                {
                    "name": "Enterprise",
                    "price": 399,
                    "currency": "USD",
                    "period": "mes",
                    "description": "Para agencias con operaciones grandes",
                    "features": [
                        "Usuarios ilimitados",
                        "Todo lo de Pro +",
                        "SSO / SAML",
                        "SLA personalizado",
                        "AI Agent conversacional",
                        "App móvil nativa",
                        "Soporte 24/7 dedicado",
                        "On-premise disponible",
                    ],
                    "cta": "Contactar ventas",
                    "highlight": False,
                },
            ],
            "features_list": [
                {
                    "icon": "🎫",
                    "title": "Parsing IA de Boletos",
                    "desc": "Escanea y parsea boletos KIU, Amadeus, Sabre y Travelport con inteligencia artificial. Sin entrada manual.",
                },
                {
                    "icon": "📊",
                    "title": "Dashboard Inteligente",
                    "desc": "Métricas en tiempo real, alertas de fugas, conciliación automática y KPIs personalizados.",
                },
                {
                    "icon": "💬",
                    "title": "WhatsApp Automation",
                    "desc": "Bot integrado que envía confirmaciones, itinerarios y notificaciones a tus clientes automáticamente.",
                },
                {
                    "icon": "💰",
                    "title": "Facturación VEN-NIF",
                    "desc": "Facturación electrónica con doble moneda, IVA, IGTF y retenciones IVA/ISLR conforme a la legislación venezolana.",
                },
                {
                    "icon": "🔗",
                    "title": "API + Webhooks",
                    "desc": "API REST documentada con rate limits por plan. Webhooks para eventos en tiempo real.",
                },
                {
                    "icon": "📱",
                    "title": "PWA Offline-First",
                    "desc": "Progressive Web App instalable con soporte offline. Accede desde cualquier dispositivo.",
                },
            ],
        },
    )


@require_GET
def public_pricing(request):
    """Página pública de precios."""
    return render(
        request,
        "marketing/public_landing.html",
        {
            "show_pricing_only": True,
            "plans": [
                {
                    "name": "Básico",
                    "price": 29,
                    "currency": "USD",
                    "period": "mes",
                    "description": "Para agencias pequeñas o freelancers",
                    "features": [
                        "Hasta 3 usuarios",
                        "Gestión de boletos aéreos",
                        "CRM con IA básico",
                        "Facturación VEN-NIF",
                        "Soporte por email",
                    ],
                    "cta": "Probar gratis →",
                    "highlight": False,
                },
                {
                    "name": "Pro",
                    "price": 99,
                    "currency": "USD",
                    "period": "mes",
                    "description": "Para agencias en crecimiento",
                    "features": [
                        "Hasta 15 usuarios",
                        "Todo lo de Básico +",
                        "API pública + Webhooks",
                        "Integración Xero contable",
                        "WhatsApp Bot automation",
                        "Reportes exportables",
                        "Soporte prioritario",
                    ],
                    "cta": "Probar gratis →",
                    "highlight": True,
                },
                {
                    "name": "Enterprise",
                    "price": 399,
                    "currency": "USD",
                    "period": "mes",
                    "description": "Para agencias con operaciones grandes",
                    "features": [
                        "Usuarios ilimitados",
                        "Todo lo de Pro +",
                        "SSO / SAML",
                        "SLA personalizado",
                        "AI Agent conversacional",
                        "App móvil nativa",
                        "Soporte 24/7 dedicado",
                        "On-premise disponible",
                    ],
                    "cta": "Contactar ventas →",
                    "highlight": False,
                },
            ],
        },
    )
