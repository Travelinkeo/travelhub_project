import json
import logging
import operator
from functools import reduce
from typing import Any

# Modelos de Django
from django.db.models import Q

# Servicio de Gemini
from core.gemini import generate_content
from core.models_catalogos import ProductoServicio

logger = logging.getLogger(__name__)


def _interpret_user_request(user_request: str) -> dict[str, Any]:
    """
    Paso 1: Interpreta la petición en lenguaje natural del usuario y la convierte en un JSON estructurado.
    """
    prompt = f"""
    Eres un agente de viajes experto en interpretar las necesidades de los clientes.
    Tu tarea es analizar la siguiente solicitud de viaje y convertirla en un objeto JSON estructurado.

    **Reglas:**
    - Extrae los siguientes campos: `destino` (str), `duracion_dias` (int), `presupuesto_usd` (float, opcional),
      `tipo_viaje` (str, ej: 'aventura', 'relax', 'cultural', 'gastronómico', 'familiar'),
      `intereses` (list[str]), y `exclusiones` (list[str]).
    - Si un campo no se puede determinar, déjalo como `null`.
    - El `destino` debe ser el país o la ciudad principal.
    - `intereses` debe contener palabras clave que describan las actividades deseadas.
    - `exclusiones` debe contener actividades o características que el usuario quiere evitar.
    - Tu respuesta debe ser únicamente el objeto JSON, sin texto adicional ni explicaciones.

    **Solicitud del Usuario:**
    "{user_request}"

    **Ejemplo de Salida:**
    {{
        "destino": "Perú",
        "duracion_dias": 7,
        "presupuesto_usd": 2500.00,
        "tipo_viaje": "cultural",
        "intereses": ["historia", "arqueología", "gastronomía"],
        "exclusiones": ["caminatas largas", "zonas de mucha fiesta"]
    }}
    """
    
    try:
        response_text = generate_content(prompt)
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        
        search_params = json.loads(response_text)
        logger.info(f"Parámetros de búsqueda interpretados: {search_params}")
        return search_params
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error al interpretar la solicitud del usuario: {e}")
        return {"error": "No se pudo interpretar la solicitud."}

def _generate_narrative_itinerary(search_params: dict[str, Any]) -> str:
    """
    Paso 2: Recibe los parámetros, consulta la base de datos y genera un itinerario narrativo.
    """
    destino = search_params.get('destino')
    intereses = search_params.get('intereses', [])
    
    if not destino:
        return "Lo sentimos, no se pudo determinar un destino a partir de tu solicitud."

    # 1. Consultar la base de datos de Django con filtros dinámicos
    
    # Filtro base por destino (en el país o en la ciudad del proveedor)
    location_filter = (Q(proveedor_principal__ciudad__pais__nombre__icontains=destino) |
                       Q(proveedor_principal__ciudad__nombre__icontains=destino))

    # Filtro por intereses (en el nombre o descripción del producto)
    interest_filter = Q()
    if intereses:
        # Usamos reduce y operator.or_ para construir un Q object dinámico: Q(icontains=i1) | Q(icontains=i2) ...
        interest_queries = [Q(nombre__icontains=i) | Q(descripcion__icontains=i) for i in intereses]
        interest_filter = reduce(operator.or_, interest_queries)

    # Búsqueda de actividades
    actividades_qs = ProductoServicio.objects.filter(
        location_filter,
        interest_filter,
        tipo_producto=ProductoServicio.TipoProductoChoices.TOUR_ACTIVIDAD,
        activo=True
    ).values('nombre', 'descripcion', 'proveedor_principal__nombre')[:15] # Limitar a 15 para no saturar el prompt

    # Búsqueda de hoteles
    hoteles_qs = ProductoServicio.objects.filter(
        location_filter,
        tipo_producto=ProductoServicio.TipoProductoChoices.HOTEL,
        activo=True
    ).values('nombre', 'descripcion', 'proveedor_principal__nombre')[:10]

    db_results = {
        "actividades_disponibles": list(actividades_qs),
        "hoteles_sugeridos": list(hoteles_qs)
    }

    if not db_results["actividades_disponibles"]:
        db_results["info"] = "No se encontraron actividades específicas para los intereses mencionados, pero se pueden sugerir actividades generales del destino."

    # 2. Segunda llamada a Gemini con los datos de la BD
    prompt = f"""
    Eres un escritor de viajes creativo y apasionado para la agencia TravelHub.
    Tu misión es crear un itinerario de viaje personalizado, detallado y emocionante.

    **Preferencias del Cliente:**
    ```json
    {json.dumps(search_params, indent=2, ensure_ascii=False)}
    ```

    **Actividades y Hoteles Disponibles (Resultados de nuestra base de datos):**
    ```json
    {json.dumps(db_results, indent=2, ensure_ascii=False)}
    ```

    **Tu Tarea:**
    - Redacta un itinerario narrativo y atractivo, día por día, para la duración especificada.
    - Organiza las actividades de forma lógica y geográfica para cada día.
    - Asigna las actividades disponibles a los días que consideres más apropiados.
    - Sugiere dónde alojarse usando los hoteles de la lista.
    - No inventes actividades que no estén en la lista proporcionada.
    - El tono debe ser inspirador y vendedor, ¡haz que el cliente sueñe con este viaje!
    - Formatea la respuesta en Markdown, usando títulos para cada día (ej: `### Día 1: Llegada a...`).
    """
    
    try:
        itinerary_text = generate_content(prompt)
        logger.info("Itinerario narrativo generado con éxito.")
        return itinerary_text
    except Exception as e:
        logger.error(f"Error al generar el itinerario narrativo: {e}")
        return "Lo sentimos, no pudimos generar tu itinerario en este momento."

def create_personalized_itinerary(user_request: str) -> str:
    """
    Función principal que orquesta la creación del itinerario.
    """
    logger.info(f"Recibida nueva solicitud de itinerario: '{user_request}'")
    
    # Paso 1: Interpretar la solicitud
    search_parameters = _interpret_user_request(user_request)
    if search_parameters.get("error"):
        return search_parameters["error"]
    
    # Paso 2: Generar el itinerario
    narrative_itinerary = _generate_narrative_itinerary(search_parameters)
    
    return narrative_itinerary

# Ejemplo de cómo se podría llamar desde una vista de Django

# def mi_vista_de_itinerarios(request):
#     if request.method == 'POST':
#         user_query = request.POST.get('query')
#         itinerario_final = create_personalized_itinerary(user_query)
#         return render(request, 'template.html', {'itinerario': itinerario_final})