"""Servicio para generar vouchers de servicios adicionales y alojamientos en PDF."""

from django.template.loader import render_to_string
from weasyprint import HTML
from datetime import datetime
import locale

# Configurar locale para español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    except:
        pass


def generar_voucher_servicio(servicio_adicional):
    """
    Genera un PDF de voucher para un servicio adicional.
    
    Args:
        servicio_adicional: Instancia de ServicioAdicionalDetalle
        
    Returns:
        tuple: (pdf_bytes, filename)
    """
    # Preparar datos del contexto
    venta = servicio_adicional.venta
    cliente = venta.cliente if venta else None
    
    # Si es un seguro, usar plantilla específica
    if servicio_adicional.tipo_servicio == 'SEG':
        metadata = servicio_adicional.metadata_json or {}
        
        context = {
            'numero_poliza': servicio_adicional.codigo_referencia or f"SEG-{servicio_adicional.id_servicio_adicional}",
            'nombre_asegurado': servicio_adicional.nombre_pasajero or (cliente.get_nombre_completo if cliente else 'N/A'),
            'pasaporte': servicio_adicional.pasaporte_pasajero or 'N/A',
            'fecha_emision': datetime.now().strftime('%d de %B, %Y'),
            'plan': servicio_adicional.descripcion or 'Plan Estándar',
            'proveedor': servicio_adicional.proveedor.nombre if servicio_adicional.proveedor else 'N/A',
            'fecha_inicio': servicio_adicional.fecha_inicio.strftime('%d%b%y').upper() if servicio_adicional.fecha_inicio else 'N/A',
            'fecha_fin': servicio_adicional.fecha_fin.strftime('%d%b%y').upper() if servicio_adicional.fecha_fin else 'N/A',
            'cobertura': servicio_adicional.detalles_cobertura or 'N/A',
            'contacto_emergencia': servicio_adicional.contacto_emergencia or 'Contactar a la aseguradora',
            'notas': servicio_adicional.notas,
        }
        
        html_string = render_to_string('core/vouchers/voucher_seguro.html', context)
        pdf_bytes = HTML(string=html_string).write_pdf()
        filename = f"Voucher_Seguro_{context['numero_poliza']}.pdf"
        
        return pdf_bytes, filename
    
    # Para otros servicios, usar plantilla genérica
    # Obtener metadata_json para datos adicionales
    metadata = servicio_adicional.metadata_json or {}
    destino = metadata.get('destino', '')
    
    # Calcular duración en días si hay fecha_inicio y fecha_fin
    duracion = None
    if servicio_adicional.fecha_inicio and servicio_adicional.fecha_fin:
        delta = servicio_adicional.fecha_fin - servicio_adicional.fecha_inicio
        duracion = f"{delta.days} días"
    elif servicio_adicional.duracion_estimada:
        duracion = servicio_adicional.duracion_estimada
    
    # Formato de fecha: DDMMMAA (ej: 05NOV25)
    fecha_servicio = None
    if servicio_adicional.fecha_inicio:
        try:
            fecha_servicio = servicio_adicional.fecha_inicio.strftime('%d%b%y').upper().replace('.', '')
        except:
            fecha_servicio = servicio_adicional.fecha_inicio.strftime('%d/%m/%Y')
    
    # Lugar: usar destino si existe, sino hora_lugar_encuentro
    hora_lugar = destino if destino else (servicio_adicional.hora_lugar_encuentro or None)
    
    # Preparar recomendaciones como lista
    recomendaciones = []
    if servicio_adicional.recomendaciones:
        recomendaciones = [r.strip() for r in servicio_adicional.recomendaciones.split('\n') if r.strip()]
    
    # Contexto para la plantilla
    context = {
        'numero_confirmacion': servicio_adicional.codigo_referencia or f"SRV-{servicio_adicional.id_servicio_adicional}",
        'nombre_pasajero': servicio_adicional.nombre_pasajero or (cliente.get_nombre_completo if cliente else 'N/A'),
        'participantes': servicio_adicional.participantes or '1 Adulto',
        'codigo_referencia': servicio_adicional.codigo_referencia or f"SRV-{servicio_adicional.id_servicio_adicional}",
        'fecha_emision': datetime.now().strftime('%d de %B, %Y'),
        'descripcion_servicio': servicio_adicional.descripcion or servicio_adicional.get_tipo_servicio_display(),
        'proveedor': servicio_adicional.proveedor.nombre if servicio_adicional.proveedor else 'N/A',
        'fecha_servicio': fecha_servicio,
        'hora_lugar': hora_lugar,
        'duracion': duracion,
        'inclusiones': servicio_adicional.inclusiones_servicio or None,
        'recomendaciones': recomendaciones if recomendaciones else None,
        'notas': servicio_adicional.detalles_cobertura or None,
    }
    
    # Renderizar HTML
    html_string = render_to_string('core/vouchers/voucher_servicio_adicional.html', context)
    
    # Generar PDF
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    # Nombre del archivo
    filename = f"Voucher_{context['numero_confirmacion']}.pdf"
    
    return pdf_bytes, filename



def generar_voucher_alojamiento(alojamiento):
    """
    Genera un PDF de voucher para un alojamiento.
    
    Args:
        alojamiento: Instancia de AlojamientoReserva
        
    Returns:
        tuple: (pdf_bytes, filename)
    """
    from datetime import datetime
    
    # Preparar datos del contexto
    venta = alojamiento.venta
    cliente = venta.cliente if venta else None
    
    # Calcular duración en noches
    duracion = None
    if alojamiento.check_in and alojamiento.check_out:
        delta = alojamiento.check_out - alojamiento.check_in
        duracion = f"{delta.days} Noche{'s' if delta.days > 1 else ''}"
    
    # Formato de fechas
    check_in_formatted = None
    check_out_formatted = None
    if alojamiento.check_in:
        try:
            check_in_formatted = alojamiento.check_in.strftime('%d%b%y').upper().replace('.', '')
        except:
            check_in_formatted = alojamiento.check_in.strftime('%d/%m/%Y')
    
    if alojamiento.check_out:
        try:
            check_out_formatted = alojamiento.check_out.strftime('%d%b%y').upper().replace('.', '')
        except:
            check_out_formatted = alojamiento.check_out.strftime('%d/%m/%Y')
    
    # Contexto para la plantilla
    context = {
        'numero_confirmacion': f"HTL-{alojamiento.id_alojamiento_reserva}",
        'nombre_huesped': alojamiento.nombre_pasajero or (cliente.get_nombre_completo if cliente else 'N/A'),
        'ocupantes': '2 Adultos',  # Por defecto, se puede mejorar
        'fecha_emision': datetime.now().strftime('%d de %B, %Y'),
        'nombre_establecimiento': alojamiento.nombre_establecimiento,
        'ciudad': alojamiento.ciudad.nombre if alojamiento.ciudad else 'N/A',
        'check_in': check_in_formatted,
        'check_out': check_out_formatted,
        'duracion': duracion,
        'regimen_alimentacion': alojamiento.regimen_alimentacion,
        'habitaciones': alojamiento.habitaciones,
        'localizador_proveedor': alojamiento.localizador_proveedor,
        'notas': alojamiento.notas,
    }
    
    # Renderizar HTML
    html_string = render_to_string('core/vouchers/voucher_alojamiento.html', context)
    
    # Generar PDF
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    # Nombre del archivo
    filename = f"Voucher_Alojamiento_{context['numero_confirmacion']}.pdf"
    
    return pdf_bytes, filename


def generar_voucher_alquiler_auto(alquiler):
    from datetime import datetime
    
    venta = alquiler.venta
    cliente = venta.cliente if venta else None
    
    duracion = None
    if alquiler.fecha_hora_retiro and alquiler.fecha_hora_devolucion:
        delta = alquiler.fecha_hora_devolucion - alquiler.fecha_hora_retiro
        duracion = f"{delta.days} Días"
    
    context = {
        'numero_confirmacion': alquiler.numero_confirmacion or f"AUTO-{alquiler.id_alquiler_auto}",
        'nombre_conductor': alquiler.nombre_conductor or (cliente.get_nombre_completo if cliente else 'N/A'),
        'fecha_emision': datetime.now().strftime('%d de %B, %Y'),
        'compania': alquiler.compania_rentadora,
        'categoria_vehiculo': alquiler.categoria_auto,
        'ciudad_retiro': alquiler.ciudad_retiro.nombre if alquiler.ciudad_retiro else 'N/A',
        'ciudad_devolucion': alquiler.ciudad_devolucion.nombre if alquiler.ciudad_devolucion else 'N/A',
        'fecha_retiro': alquiler.fecha_hora_retiro.strftime('%d%b%y %H:%M').upper() if alquiler.fecha_hora_retiro else 'N/A',
        'fecha_devolucion': alquiler.fecha_hora_devolucion.strftime('%d%b%y %H:%M').upper() if alquiler.fecha_hora_devolucion else 'N/A',
        'duracion': duracion,
        'incluye_seguro': 'Sí' if alquiler.incluye_seguro else 'No',
        'notas': alquiler.notas,
    }
    
    html_string = render_to_string('core/vouchers/voucher_alquiler_auto.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    filename = f"Voucher_AlquilerAuto_{context['numero_confirmacion']}.pdf"
    
    return pdf_bytes, filename


def generar_voucher_traslado(traslado):
    from datetime import datetime
    from django.utils import timezone
    
    venta = traslado.venta
    cliente = venta.cliente if venta else None
    
    # Convertir fecha_hora a zona horaria local si existe
    fecha_hora_str = 'N/A'
    if traslado.fecha_hora:
        # Si es aware (tiene timezone), convertir a local
        if timezone.is_aware(traslado.fecha_hora):
            fecha_hora_local = timezone.localtime(traslado.fecha_hora)
            fecha_hora_str = fecha_hora_local.strftime('%d%b%y %H:%M').upper()
        else:
            fecha_hora_str = traslado.fecha_hora.strftime('%d%b%y %H:%M').upper()
    
    context = {
        'numero_confirmacion': f"TRS-{traslado.id_traslado_servicio}",
        'nombre_pasajero': cliente.get_nombre_completo if cliente else 'N/A',
        'fecha_emision': datetime.now().strftime('%d de %B, %Y'),
        'tipo_traslado': traslado.get_tipo_traslado_display(),
        'origen': traslado.origen or 'N/A',
        'destino': traslado.destino or 'N/A',
        'fecha_hora': fecha_hora_str,
        'pasajeros': traslado.pasajeros,
        'proveedor': traslado.proveedor.nombre if traslado.proveedor else 'N/A',
        'notas': traslado.notas,
    }
    
    html_string = render_to_string('core/vouchers/voucher_traslado.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    filename = f"Voucher_Traslado_{context['numero_confirmacion']}.pdf"
    
    return pdf_bytes, filename


def generar_voucher_actividad(actividad):
    from datetime import datetime
    
    venta = actividad.venta
    cliente = venta.cliente if venta else None
    
    context = {
        'numero_confirmacion': f"ACT-{actividad.id_actividad_servicio}",
        'nombre_pasajero': actividad.nombre_pasajero or (cliente.get_nombre_completo if cliente else 'N/A'),
        'fecha_emision': datetime.now().strftime('%d de %B, %Y'),
        'nombre_actividad': actividad.nombre,
        'fecha': actividad.fecha.strftime('%d%b%y').upper() if actividad.fecha else 'N/A',
        'duracion': f"{actividad.duracion_horas} horas" if actividad.duracion_horas else 'N/A',
        'incluye': actividad.incluye,
        'no_incluye': actividad.no_incluye,
        'proveedor': actividad.proveedor.nombre if actividad.proveedor else 'N/A',
        'localizador_proveedor': actividad.localizador_proveedor,
        'notas': actividad.notas,
    }
    
    html_string = render_to_string('core/vouchers/voucher_actividad.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    filename = f"Voucher_Actividad_{context['numero_confirmacion']}.pdf"
    
    return pdf_bytes, filename
