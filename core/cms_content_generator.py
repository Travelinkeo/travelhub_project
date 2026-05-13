
import json
from typing import Any

from apps.automation.services.ai_engine import generate_content


def generate_promotional_content(promotion_data: dict[str, Any]) -> dict[str, Any]:
    """
    Recibe un JSON con datos de una promoción, construye un prompt creativo
    y llama a la API de Gemini para generar contenido para redes sociales.

    Args:
        promotion_data: Un diccionario con los detalles de la promoción extraídos por la IA.
                        Ej: {"destino": "Tokio, Japón", "precio": "1200 USD", "fechas": "15-30 de Octubre"}

    Returns:
        Un diccionario con el contenido generado para cada plataforma,
        o un diccionario de error si la respuesta no pudo ser procesada.
    """
    # Convertir el diccionario de datos de la promoción a un string JSON formateado
    promotion_json_str = json.dumps(promotion_data, indent=2, ensure_ascii=False)

    # 2. Diseño del prompt detallado para la segunda llamada a Gemini
    prompt = f"""
    Eres un experto en marketing digital y social media manager para una agencia de viajes de primer nivel.
    Tu tarea es tomar los siguientes datos de una promoción y convertirlos en contenido atractivo y viral.

    **Datos de la Promoción:**
    ```json
    {promotion_json_str}
    ```

    **Instrucciones:**
    A partir de los datos proporcionados, genera tres piezas de contenido distintas.
    Tu respuesta DEBE ser un único objeto JSON válido, sin texto introductorio ni explicaciones adicionales,
    con las siguientes tres claves: "whatsapp_status", "instagram_post", "instagram_reel_idea".

    1.  **whatsapp_status**: Crea un texto muy corto, llamativo y emocionante para un estado de WhatsApp. Debe generar curiosidad y urgencia. Máximo 25 palabras.
    2.  **instagram_post**: Escribe una descripción atractiva para un post de Instagram. Debe ser inspiradora, incluir un llamado a la acción claro (ej: "¡Reserva ahora en el link de nuestra bio!") y finalizar con exactamente 5 hashtags relevantes y populares.
    3.  **instagram_reel_idea**: Propón un guion simple o una idea conceptual para un Reel de Instagram de 15 segundos. Describe las escenas rápidas, el texto que aparecería en pantalla y sugiere un tipo de música o audio en tendencia.

    **Ejemplo de formato de respuesta JSON esperado:**
    {{
        "whatsapp_status": "¡No te lo vas a creer! 😱 Prepara tus maletas para [Destino] a un precio de locura. ¡Oferta por tiempo limitado!",
        "instagram_post": "El viaje de tus sueños a [Destino] te está esperando. ✨ Imagina caminar por sus calles, probar su comida y vivir una aventura inolvidable. ¡Todo por solo [Precio]! ✈️ ¿Estás listo? ¡Reserva ahora en el link de nuestra bio! #Viajes #Promocion #OfertaDeViaje #[Destino] #Aventura",
        "instagram_reel_idea": {{
            "concepto": "Montaje rápido de 3 clips de video del destino.",
            "escena_1": "Video aéreo de [Destino] (2 seg). Texto en pantalla: '¿Sueñas con...'",
            "escena_2": "Clip de comida local o actividad cultural (3 seg). Texto: '...esto?'",
            "escena_3": "Clip de un paisaje icónico al atardecer (3 seg). Texto: '¡Hazlo realidad!'",
            "escena_final": "Plano con el logo de la agencia (2 seg). Texto: '[Destino] desde [Precio]. Link en la bio.'",
            "audio_sugerido": "Una canción pop en tendencia, ritmo rápido y alegre."
        }}
    }}
    """

    try:
        # 3. Llamada a la API de Gemini
        response_text = generate_content(prompt)

        # Limpiar la respuesta para asegurar que sea un JSON válido
        # A veces, la API puede devolver el JSON envuelto en ```json ... ```
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()

        # 4. Parsear la respuesta y devolverla
        generated_content = json.loads(response_text)
        return generated_content

    except json.JSONDecodeError:
        return {
            "error": "Error al decodificar la respuesta JSON de la API.",
            "raw_response": response_text
        }
    except Exception as e:
        return {
            "error": f"Ocurrió un error inesperado: {str(e)}"
        }

# Ejemplo de uso (para pruebas)
if __name__ == '__main__':
    # 1. Datos de ejemplo que simulan la primera extracción de Gemini
    sample_promotion = {
        "destino": "Kioto, Japón",
        "aerolinea": "Japan Airlines",
        "precio": "950 USD",
        "fechas_vuelo": "del 10 al 25 de noviembre, 2025",
        "hotel_incluido": "Ryokan con vistas al jardín Zen",
        "oferta_especial": "Incluye tour guiado al Templo Fushimi Inari"
    }

    # Llamar a la función para generar el contenido creativo
    creative_content = generate_promotional_content(sample_promotion)

    # Imprimir el resultado de forma legible
    print(json.dumps(creative_content, indent=4, ensure_ascii=False))
