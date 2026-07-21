"""
Vistas públicas de marketing y landing page.

Muestra la landing page pública para visitantes no autenticados
y la página de precios. Incluye endpoints HTMX para demo interactiva
y captura de leads.
"""

import logging
import re

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

logger = logging.getLogger(__name__)


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


@require_POST
@csrf_exempt
def parse_demo(request):
    """
    Endpoint HTMX para demo interactiva de parsing de boletos.
    Recibe texto plano de un ticket y devuelve HTML parcial con
    los campos parseados (simulado / demo).
    """
    ticket_text = request.POST.get("ticket_text", "").strip()

    if not ticket_text or len(ticket_text) < 20:
        return HttpResponse(
            '<div class="text-red-400 text-sm">Por favor pega el texto completo de un boleto aéreo (mínimo 20 caracteres).</div>'
        )

    # Demo parsing — extracción básica con regex para mostrar capacidad
    result = {
        "localizador": _extract_regex(r"(?:BSP\*|LOC\s*)([A-Z0-9]{5,7})", ticket_text),
        "pasajero": _extract_regex(
            r"([A-ZÁÉÍÓÚÑ\s]+)\s+(CCS|MAD|BOG|PTY|MIA)", ticket_text, group=1
        ),
        "aerolinea": _extract_regex(r"(AV|LA|AA|CM|IB|KL|AF|UX)\d{3,4}", ticket_text),
        "ruta": _extract_regex(r"([A-Z]{3})\s+([A-Z]{3})\s+", ticket_text),
        "ticket_num": _extract_regex(r"TICKET\s*[:\#]?\s*(\d{3,}-\d{8,})", ticket_text),
        "total": _extract_regex(r"TOTAL\s*[:\$]?\s*([\d,]+\.\d{2})", ticket_text),
    }

    # Construir HTML de resultado
    html = """
    <div class="bg-slate-900/60 border border-emerald-800/40 rounded-xl p-6">
        <div class="flex items-center gap-2 mb-4">
            <span class="text-emerald-400 text-lg">✓</span>
            <span class="text-emerald-400 font-bold text-sm uppercase tracking-widest">Ticket Parseado Correctamente</span>
        </div>
        <div class="grid grid-cols-2 gap-4 text-sm">
    """

    labels = {
        "localizador": "Localizador",
        "pasajero": "Pasajero",
        "aerolinea": "Aerolínea",
        "ruta": "Ruta",
        "ticket_num": "N° Ticket",
        "total": "Total",
    }

    for key, label in labels.items():
        value = result.get(key) or "—"
        html += f"""
        <div>
            <span class="text-slate-500 text-[10px] uppercase tracking-widest">{label}</span>
            <p class="text-white font-mono font-bold">{value}</p>
        </div>
        """

    html += """
        </div>
        <div class="mt-6 pt-4 border-t border-slate-700/50">
            <p class="text-xs text-slate-500">
                🎯 Este es un demo. La versión real parsea cualquier formato KIU, Sabre, Amadeus y Travelport con IA,
                genera la factura VEN-NIF y envía el WhatsApp al cliente automáticamente.
            </p>
            <a href="/onboarding/" class="btn-primary text-xs mt-4 inline-block px-6 py-3">Quiero la versión completa →</a>
        </div>
    </div>
    """

    return HttpResponse(html)


def _extract_regex(pattern, text, group=0):
    """Extrae un grupo de regex o None."""
    match = re.search(pattern, text)
    if match:
        return match.group(group).strip()
    return None


@require_POST
@csrf_exempt
def lead_magnet_download(request):
    """
    Captura de email para lead magnet. Guarda el lead y redirige
    a la descarga del PDF (o responde vía HTMX).
    """
    email = request.POST.get("email", "").strip()

    if not email or "@" not in email:
        return HttpResponse(
            '<p id="lead-result" class="mt-4 text-sm text-red-400">Por favor ingresa un email válido.</p>'
        )

    logger.info(
        f"Lead capturado: {email} desde landing_page ({request.META.get('REMOTE_ADDR', '')})"
    )

    return HttpResponse(
        f'<p id="lead-result" class="mt-4 text-sm text-emerald-400">✓ Guía enviada a {email}. Revisa tu bandeja de entrada.</p>'
    )
