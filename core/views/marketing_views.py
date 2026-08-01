"""
Vistas públicas de marketing y landing page.

Muestra la landing page pública para visitantes no autenticados
y la página de precios. Incluye endpoints HTMX para demo interactiva
y captura de leads.
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from apps.automation.parsers.ticket_parser import extract_data_from_text

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
def parse_demo(request):
    """
    Endpoint HTMX para demo interactiva de parsing de boletos.
    Usa el motor real de parsing (extract_data_from_text) para mostrar
    resultados auténticos con cualquier texto de boleto KIU/Sabre/Amadeus.
    """
    ticket_text = request.POST.get("ticket_text", "").strip()

    if not ticket_text or len(ticket_text) < 20:
        return HttpResponse(
            '<div class="text-red-400 text-sm">Por favor pega el texto completo de un boleto aéreo (mínimo 20 caracteres).</div>'
        )

    result = extract_data_from_text(ticket_text)

    if not result or result.get("error"):
        return HttpResponse(
            '<div class="bg-slate-900/60 border border-amber-700/40 rounded-xl p-6">'
            '<p class="text-amber-400 text-sm">No se pudieron extraer campos del texto proporcionado. '
            "Prueba con un boleto en formato KIU, Sabre o Amadeus.</p>"
            "</div>"
        )

    # Mapear claves del parser real a las etiquetas del demo
    field_map = {
        "codigo_reserva": ("Localizador", result.get("codigo_reserva")),
        "nombre_pasajero": (
            "Pasajero",
            result.get("nombre_pasajero") or result.get("passenger_name"),
        ),
        "aerolinea": ("Aerolínea", result.get("aerolinea") or result.get("airline")),
        "ruta": ("Ruta", result.get("ruta") or result.get("route")),
        "numero_ticket": ("N° Ticket", result.get("numero_ticket") or result.get("ticket_number")),
        "total": ("Total", result.get("total") or result.get("total_amount")),
    }

    gds = result.get("gds", "desconocido").upper()
    gds_badge = f'<span class="text-[10px] bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded-full">{gds}</span>'

    html = f"""
    <div class="bg-slate-900/60 border border-emerald-800/40 rounded-xl p-6">
        <div class="flex items-center gap-2 mb-4">
            <span class="text-emerald-400 text-lg">✓</span>
            <span class="text-emerald-400 font-bold text-sm uppercase tracking-widest">Ticket Parseado Correctamente {gds_badge}</span>
        </div>
        <div class="grid grid-cols-2 gap-4 text-sm">
    """

    for _, (label, value) in field_map.items():
        display = str(value).strip() if value and str(value).strip() else "—"
        html += f"""
        <div>
            <span class="text-slate-500 text-[10px] uppercase tracking-widest">{label}</span>
            <p class="text-white font-mono font-bold">{display}</p>
        </div>
        """

    html += """
        </div>
        <div class="mt-6 pt-4 border-t border-slate-700/50">
            <p class="text-xs text-slate-500">
                🎯 Este es el motor real que usan todas las agencias. Sin simulación.
                Sube tu boleto completo y recibe la factura VEN-NIF + WhatsApp al instante.
            </p>
            <a href="/onboarding/" class="btn-primary text-xs mt-4 inline-block px-6 py-3">Quiero la versión completa →</a>
        </div>
    </div>
    """

    return HttpResponse(html)


@require_GET
def demo_page(request):
    """Página pública de agendamiento de demo."""
    return render(request, "marketing/demo.html")


@require_POST
def demo_request(request):
    """
    Endpoint HTMX para solicitar una demo.
    Guarda la solicitud en DemoRequest y notifica al equipo.
    """
    from apps.communications.models import DemoRequest
    from apps.communications.services.email_unified import send_custom_email

    nombre = request.POST.get("nombre", "").strip()
    email = request.POST.get("email", "").strip()
    telefono = request.POST.get("telefono", "").strip()
    agencia_nombre = request.POST.get("agencia_nombre", "").strip()
    volumen = request.POST.get("volumen", "").strip()
    mensaje = request.POST.get("mensaje", "").strip()

    if not nombre or not email or "@" not in email:
        return HttpResponse(
            '<div class="text-red-400 text-sm">Completa tu nombre y un email válido.</div>'
        )

    demo = DemoRequest.objects.create(
        nombre=nombre,
        email=email,
        telefono=telefono,
        agencia_nombre=agencia_nombre,
        volumen=volumen,
        mensaje=mensaje,
    )

    # Notificar al equipo
    try:
        send_custom_email(
            subject=f"🎯 Nueva solicitud de demo: {nombre} — {agencia_nombre or 'Sin agencia'}",
            recipient=settings.DEMO_NOTIFY_EMAIL or "ventas@travelhub.app",
            template_name="emails/demo_notification.html",
            context={
                "nombre": nombre,
                "email": email,
                "telefono": telefono,
                "agencia": agencia_nombre,
                "volumen": volumen,
                "mensaje": mensaje,
                "admin_url": f"{settings.SITE_URL}/admin/communications/demorequest/{demo.id}/change/",
            },
        )
    except Exception as e:
        logger.warning(f"No se pudo notificar demo: {e}")

    logger.info(f"Demo solicitado: {nombre} <{email}> (agencia: {agencia_nombre})")

    return HttpResponse(
        '<div class="bg-emerald-900/40 border border-emerald-700/50 rounded-xl p-6 text-center">'
        '<div class="text-4xl mb-3">🎉</div>'
        '<p class="text-emerald-300 font-bold text-lg mb-2">¡Solicitud recibida!</p>'
        '<p class="text-sm text-slate-300">Te contactaremos en menos de 24 horas para coordinar tu demo personalizada.</p>'
        "</div>"
    )


@require_POST
def lead_magnet_download(request):
    """
    Captura de email para lead magnet. Guarda el lead en BD,
    envía el email de bienvenida con la guía y responde vía HTMX.
    """
    from apps.communications.models import Lead
    from apps.communications.services.email_unified import send_custom_email

    email = request.POST.get("email", "").strip()
    nombre = request.POST.get("nombre", "").strip()

    if not email or "@" not in email:
        return HttpResponse(
            '<p id="lead-result" class="mt-4 text-sm text-red-400">Por favor ingresa un email válido.</p>'
        )

    lead, created = Lead.objects.get_or_create(
        email=email,
        defaults={
            "nombre": nombre,
            "fuente": "landing_page",
            "ip_origen": request.META.get("REMOTE_ADDR", ""),
        },
    )

    if created or not lead.email_enviado:
        sent = send_custom_email(
            subject="🎫 Guía completa: Cómo digitalizar tu agencia de viajes en 2026",
            recipient=email,
            template_name="emails/lead_welcome.html",
            context={
                "email": email,
                "nombre": nombre or "Agente",
                "year": 2026,
            },
        )
        lead.email_enviado = sent
        lead.guia_descargada = True
        lead.save(update_fields=["email_enviado", "guia_descargada"])
        logger.info(f"Lead {'nuevo' if created else 'reenviado'}: {email} — email enviado: {sent}")
    else:
        logger.info(f"Lead ya existente con email previo: {email}")

    return HttpResponse(
        f'<p id="lead-result" class="mt-4 text-sm text-emerald-400">✓ Guía enviada a {email}. Revisa tu bandeja de entrada.</p>'
    )
