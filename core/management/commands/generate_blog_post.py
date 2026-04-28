import json
import logging

from django.core.management.base import BaseCommand, CommandParser

from core.gemini import generate_content
from core.models.cms import ArticuloBlog

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Genera un nuevo artículo de blog sobre un tema específico usando IA.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--topic',
            type=str,
            required=True,
            help='El tema sobre el cual se generará el artículo del blog.'
        )

    def handle(self, *args, **options):
        topic = options['topic']
        self.stdout.write(self.style.SUCCESS(f'Iniciando la generación de un artículo de blog sobre: "{topic}"'))

        # 1. Diseñar el prompt para la IA
        prompt = self._create_prompt(topic)

        # 2. Llamar a la API de Gemini
        self.stdout.write("Llamando a la API de Gemini para generar el contenido...")
        try:
            response_text = generate_content(prompt)
            # La respuesta de la IA debería ser un bloque de código JSON
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            json_match = json.loads(response_text)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al comunicarse con la API de Gemini o al parsear su respuesta: {e}"))
            return

        # 3. Crear la instancia del modelo ArticuloBlog
        try:
            articulo = ArticuloBlog.objects.create(
                titulo=json_match.get('titulo'),
                contenido=json_match.get('contenido'),
                extracto=json_match.get('extracto'),
                meta_titulo=json_match.get('meta_titulo'),
                meta_descripcion=json_match.get('meta_descripcion'),
                estado=ArticuloBlog.EstadoPublicacion.BORRADOR # Guardar como borrador para revisión
            )
            self.stdout.write(self.style.SUCCESS(
                f'¡Artículo de blog creado con éxito!\n'
                f'ID: {articulo.id_articulo}\n'
                f'Título: "{articulo.titulo}"\n'
                f'Estado: {articulo.get_estado_display()}\n'
                f'Puedes revisarlo y publicarlo desde el panel de administración de Django.'
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al guardar el artículo en la base de datos: {e}"))

    def _create_prompt(self, topic: str) -> str:
        return f"""
        Actúa como un experto en SEO y un blogger de viajes apasionado. Tu tarea es generar un artículo de blog completo sobre el siguiente tema.
        El contenido debe ser original, atractivo, informativo y estar bien estructurado para la web (usa párrafos cortos, listas, etc.).
        
        Tema: "{topic}"

        Devuelve la respuesta como un único objeto JSON con la siguiente estructura y claves:
        {{
            "titulo": "Un título creativo y optimizado para SEO para el artículo.",
            "contenido": "El contenido completo del artículo en formato Markdown. Debe tener al menos 500 palabras. Usa encabezados (##), listas (*), y texto en negrita (**).",
            "extracto": "Un resumen corto y atractivo del artículo, de no más de 160 caracteres.",
            "meta_titulo": "Un meta título para SEO, de 50-60 caracteres.",
            "meta_descripcion": "Una meta descripción para SEO, de 150-160 caracteres."
        }}

        Asegúrate de que el JSON sea válido y esté bien formado.
        """