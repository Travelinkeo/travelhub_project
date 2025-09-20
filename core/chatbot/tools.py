from core.models.ventas import Venta  # Asumiendo la ruta correcta al modelo Venta


def consultar_estado_reserva(pnr: str) -> dict:
    """
    Implementación real de la consulta de reserva.
    Busca en la base de datos y devuelve un JSON con los detalles.
    """
    try:
        # Usamos 'iexact' para una búsqueda no sensible a mayúsculas/minúsculas
        venta = Venta.objects.get(localizador__iexact=pnr)
        
        # Formateamos una respuesta clara y estructurada para Gemini
        response_data = {
            "status": "success",
            "data": {
                "pnr": venta.localizador,
                "estado": venta.get_estado_display(), # Usamos el método para obtener el texto legible
                "cliente": str(venta.cliente),
                "fecha_creacion": venta.fecha_venta.strftime("%d de %B de %Y"),
                "total": f"{venta.total_venta} {venta.moneda.codigo_iso}",
                "saldo_pendiente": f"{venta.saldo_pendiente} {venta.moneda.codigo_iso}",
                "descripcion": venta.descripcion_general
            }
        }
        return response_data
        
    except Venta.DoesNotExist:
        return {
            "status": "error",
            "message": f"No se encontró ninguna reserva con el PNR '{pnr}'. Por favor, verifica el código e intenta de nuevo."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ocurrió un error inesperado al buscar la reserva: {str(e)}"
        }

def agregar_servicio_adicional(pnr: str, id_servicio: int) -> dict:
    """
    Implementación para agregar un servicio. (Simulada por ahora)
    """
    # Aquí iría la lógica para encontrar la Venta, encontrar el ProductoServicio,
    # crear un ItemVenta, y recalcular los totales.
    print(f"SIMULACIÓN: Agregando servicio {id_servicio} a la reserva {pnr}.")
    return {
        "status": "success",
        "message": f"El servicio con ID {id_servicio} ha sido agregado exitosamente a la reserva {pnr}. El nuevo total es de 550 USD."
    }

def buscar_paquetes_turisticos(destino: str, presupuesto: float, mes: str) -> dict:
    """
    Implementación para buscar paquetes. (Simulada por ahora)
    """
    # Aquí iría la lógica para consultar el modelo PaqueteTuristicoCMS
    print(f"SIMULACIÓN: Buscando paquetes para {destino} en {mes} con presupuesto de ${presupuesto}.")
    return {
        "status": "success",
        "data": [
            {"nombre": "París Mágico", "precio": 1200, "descripcion": "7 días en el corazón de París, incluye hotel y tour a la Torre Eiffel."},
            {"nombre": "Aventura en los Alpes", "precio": 1450, "descripcion": "8 días de senderismo y vistas espectaculares en los Alpes franceses."}
        ]
    }
