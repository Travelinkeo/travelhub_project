import logging
import uuid
from datetime import datetime, time

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.bookings.models import Venta, VentaMensaje
from apps.bookings.services.itinerary_service import ItineraryCryptoService
from core.api import agency_context, get_agencia_from_request

logger = logging.getLogger(__name__)


def venta_messages_stream(request, pk):
    """
    Retorna el flujo de mensajes de una venta específica para streaming HTMX.
    """
    agencia = get_agencia_from_request(request)
    venta = get_object_or_404(
        Venta.all_objects.prefetch_related("mensajes_comunicacion__adjuntos"),
        pk=pk,
        agencia=agencia,
    )

    messages = venta.mensajes_comunicacion.all().order_by("created_at")
    return render(
        request,
        "bookings/partials/_message_list.html",
        {
            "venta": venta,
            "messages": messages,
        },
    )


@require_POST
def venta_message_send(request, pk):
    """
    Recibe el formulario de envío rápido desde el detalle de la venta,
    crea el mensaje y delega el despacho asíncrono a Celery.
    """
    agencia = get_agencia_from_request(request)
    venta = get_object_or_404(
        Venta.all_objects.select_related("cliente", "agencia"), pk=pk, agencia=agencia
    )

    body_text = request.POST.get("body", "").strip()
    attach_ticket = (
        request.POST.get("attach_ticket") == "on" or request.POST.get("attach_ticket") == "true"
    )
    include_itinerary = (
        request.POST.get("include_itinerary") == "on"
        or request.POST.get("include_itinerary") == "true"
    )
    canal = request.POST.get("canal", "EMAIL").upper()

    if not body_text:
        return HttpResponseBadRequest("El mensaje no puede estar vacío.")

    # 1. Determinar destinatario
    cliente_email = venta.cliente.email if venta.cliente and venta.cliente.email else ""
    cliente_telefono = (
        venta.cliente.telefono_principal
        if venta.cliente and venta.cliente.telefono_principal
        else ""
    )

    destinatario = cliente_email if canal == "EMAIL" else cliente_telefono
    if not destinatario:
        destinatario = cliente_email or cliente_telefono or "cliente@desconocido.com"

    # 2. Generar enlace a Ficha Digital si se solicita
    enlace_ficha = ""
    if include_itinerary:
        enlace_ficha = ItineraryCryptoService.generar_enlace_itinerario(venta)

    # 3. Mantener hilo RFC 2822
    last_message = (
        venta.mensajes_comunicacion.filter(message_id__isnull=False).order_by("-created_at").first()
    )
    in_reply_to_id = last_message.message_id if last_message else None

    domain = getattr(settings, "EMAIL_DOMAIN", "travelhub.cc")
    new_message_id = f"<{venta.localizador}-{uuid.uuid4().hex[:8]}@{domain}>"

    # 4. Persistir mensaje saliente
    remitente = f"{request.user.get_full_name() or request.user.username} ({agencia.nombre})"
    msg = VentaMensaje.objects.create(
        venta=venta,
        direccion="OUT",
        canal=canal,
        remitente=remitente,
        destinatario=destinatario,
        cuerpo=body_text,
        message_id=new_message_id,
        in_reply_to=in_reply_to_id,
        enlace_ficha_digital=enlace_ficha or None,
    )

    # 5. Encolar tarea Celery asíncrona
    from apps.bookings.tasks import dispatch_booking_message_task

    dispatch_booking_message_task.delay(
        message_id=msg.pk, attach_ticket=attach_ticket, include_itinerary_link=include_itinerary
    )

    # 6. Responder inmediatamente a HTMX con el parcial del mensaje
    return render(
        request,
        "bookings/partials/_single_message.html",
        {
            "msg": msg,
            "pending_attachment": attach_ticket,
            "venta": venta,
        },
    )


def generate_ical_calendar(request, token):
    """
    Genera un archivo estándar iCalendar (.ics - RFC 5545) para importar
    los vuelos y hospedajes a Google Calendar, Apple Calendar o Microsoft Outlook.
    """
    try:
        venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
            token, max_age_days=30
        )
    except (SignatureExpired, BadSignature):
        return HttpResponse("Enlace de calendario vencido o no válido", status=403)

    from core.api import Agencia

    agencia = get_object_or_404(Agencia, pk=agencia_id)

    with agency_context(agencia):
        venta = get_object_or_404(
            Venta.all_objects.prefetch_related(
                "segmentos_vuelo__origen", "segmentos_vuelo__destino", "alojamientos__ciudad"
            ),
            pk=venta_id,
            agencia_id=agencia_id,
        )

    # Construir contenido iCalendar RFC 5545
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TravelHub//Travelinkeo Itinerary Engine v3.0//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Viaje {venta.localizador} - {agencia.nombre}",
    ]

    now_stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")

    # 1. Eventos de Vuelos
    for seg in venta.segmentos_vuelo.all():
        if seg.fecha_salida:
            dt_start = seg.fecha_salida.strftime("%Y%m%dT%H%M%SZ")
            dt_end = (seg.fecha_llegada or seg.fecha_salida).strftime("%Y%m%dT%H%M%SZ")
            orig = seg.origen.codigo_iata if seg.origen else "Origen"
            dest = seg.destino.codigo_iata if seg.destino else "Destino"
            aero = f"{seg.aerolinea} {seg.numero_vuelo}".strip() or "Vuelo"
            summary = f"✈️ Vuelo {aero}: {orig} ➔ {dest}"
            desc = f"Localizador PNR: {venta.localizador}\\nAerolínea: {aero}\\nCabina: {seg.cabina or 'Turista'}\\nEquipaje: {seg.equipaje_permitido or 'Consultar franquicia'}"
            loc = f"Aeropuerto {seg.origen.nombre if seg.origen else orig}"

            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:flight-{seg.pk}-{venta.localizador}@travelhub.cc",
                    f"DTSTAMP:{now_stamp}",
                    f"DTSTART:{dt_start}",
                    f"DTEND:{dt_end}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:{desc}",
                    f"LOCATION:{loc}",
                    "STATUS:CONFIRMED",
                    "END:VEVENT",
                ]
            )

    # 2. Eventos de Hoteles
    for hotel in venta.alojamientos.all():
        if hotel.check_in and hotel.check_out:
            dt_start = datetime.combine(hotel.check_in, time(15, 0)).strftime("%Y%m%dT%H%M%SZ")
            dt_end = datetime.combine(hotel.check_out, time(11, 0)).strftime("%Y%m%dT%H%M%SZ")
            summary = f"🏨 Hotel: {hotel.nombre_establecimiento}"
            desc = f"Reserva en {hotel.nombre_establecimiento}\\nLocalizador Proveedor: {hotel.localizador_proveedor or venta.localizador}\\nRégimen: {hotel.regimen_alimentacion or 'Alojamiento'}"
            loc = f"{hotel.nombre_establecimiento}, {hotel.ciudad.nombre if hotel.ciudad else ''}"

            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:hotel-{hotel.pk}-{venta.localizador}@travelhub.cc",
                    f"DTSTAMP:{now_stamp}",
                    f"DTSTART:{dt_start}",
                    f"DTEND:{dt_end}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:{desc}",
                    f"LOCATION:{loc}",
                    "STATUS:CONFIRMED",
                    "END:VEVENT",
                ]
            )

    lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(lines)

    response = HttpResponse(ics_content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="Itinerario_{venta.localizador}.ics"'
    return response
