import logging
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db.models import Count
from django.utils import timezone

from apps.automation.services.ai_engine import ai_engine
from apps.bookings.models import BoletoImportado
from apps.marketing.models import ActivoMarketing, Campania
from apps.marketing.services.flash_marketing_service import FlashMarketingService
from core.models.agencia import Agencia

logger = logging.getLogger(__name__)

class MarketingIntelligenceService:
    """
    Marketing Intelligence Hub.
    Automates content generation based on actual booking data.
    """

    @classmethod
    def run_automated_marketing_engine(cls, agency_id=None):
        """
        Processes agencies to find trends and generate content.
        """
        agencies = Agencia.objects.filter(activa=True)
        if agency_id:
            agencies = agencies.filter(id=agency_id)
            
        results = []
        for agencia in agencies:
            try:
                # 1. Discover Trend
                trend = cls._discover_trending_destination(agencia)
                if not trend:
                    logger.info(f"No trends found for {agencia.nombre}. Skipping.")
                    continue
                
                # 2. Create Campaign
                campania = Campania.objects.create(
                    nombre=f"Tendencia: {trend['destino']} - {timezone.now().strftime('%b %Y')}",
                    descripcion=f"Campaña automática basada en el destino más vendido ({trend['count']} boletos recientemente).",
                    agencia=agencia,
                    estado='BORRADOR'
                )
                
                # 3. Generate Assets
                # 3.1. Copywriting
                copy_text = cls._generate_marketing_copy(agencia, trend['destino'])
                ActivoMarketing.objects.create(
                    campania=campania,
                    tipo='COPY',
                    texto_caption=copy_text,
                    generado_por_ia=True
                )
                
                # 3.2. Flyer (Image)
                flyer_buffer = FlashMarketingService().generate_flyer(
                    destination=trend['destino'],
                    price="Consultar", # We could improve this by finding the average price in bookings
                    agency_logo_path=agencia.logo.path if agencia.logo else None
                )
                
                flyer_activo = ActivoMarketing.objects.create(
                    campania=campania,
                    tipo='FLYER',
                    generado_por_ia=True
                )
                flyer_activo.archivo.save(
                    f"flyer_{trend['destino'].lower()}.jpg",
                    ContentFile(flyer_buffer.read()),
                    save=True
                )
                
                results.append({
                    'agencia': agencia.nombre,
                    'trend': trend['destino'],
                    'campaign_id': campania.id
                })
                
            except Exception as e:
                logger.error(f"Error in marketing engine for {agencia.nombre}: {e}")
        
        return results

    @classmethod
    def _discover_trending_destination(cls, agencia):
        """
        Finds the destination with most bookings in the last 30 days.
        """
        last_30_days = timezone.now() - timedelta(days=30)
        
        # Aggregate bookings by destination
        # Note: BoletoImportado has 'itinerario' text, we need destination. 
        # For simplicity in this demo, let's assume we have a way to get it or use the most common word in itinerario that is a city.
        # REAL IMPLEMENTATION: We'll look at the first flight segment's arrival city.
        
        trends = BoletoImportado.all_objects.filter(
            agencia=agencia,
            fecha_subida__gte=last_30_days
        ).values('ciudad_destino').annotate(count=Count('id')).order_by('-count')
        
        if trends.exists() and trends[0]['ciudad_destino']:
            return {
                'destino': trends[0]['ciudad_destino'],
                'count': trends[0]['count']
            }
            
        return None

    @classmethod
    def _generate_marketing_copy(cls, agencia, destino):
        """
        Uses Gemini to generate persuasive copy.
        """
        prompt = f"""
        Actúa como un experto en Marketing Turístico. 
        Escribe un post de Instagram altamente persuasivo para la agencia "{agencia.nombre}".
        El destino a promocionar es "{destino}".
        
        CONTEXTO:
        - Hemos notado que muchos de nuestros clientes están viajando a este destino recientemente.
        - Queremos animar a otros a reservar ahora.
        
        ESTILO:
        - Emocional, aventurero y profesional.
        - Usa ganchos (hooks) al inicio.
        - Incluye emojis de viajes.
        - Incluye un Call to Action (CTA) para contactar a la agencia.
        - Agrega 5 hashtags relevantes.
        
        IMPORTANTE: Solo devuelve el texto del post, sin explicaciones.
        """
        
        response = ai_engine.call_gemini(
            prompt=prompt,
            feature="marketing_intelligence"
        )
        
        return response.get('content', f"¡Descubre {destino} con {agencia.nombre}! Reserva hoy tu próxima aventura.")
    
    @classmethod
    def generate_newsletter_html(cls, agencia, destination_trends):
        """
        Generates a full HTML newsletter based on multiple trends.
        """
        destinations_str = ", ".join([t['destino'] for t in destination_trends])
        
        prompt = f"""
        Genera el código HTML para una Newsletter de viajes profesional y moderna para la agencia "{agencia.nombre}".
        Los destinos destacados de este mes son: {destinations_str}.
        
        REQUISITOS:
        - Diseño responsive (usar tablas y estilos inline para compatibilidad con email).
        - Estética premium, colores elegantes.
        - Secciones: Header con logo (placeholder), Hero image (placeholder), cuadrícula de destinos con descripciones cortas y tentadoras, Footer con contacto.
        - El texto debe ser en español.
        
        IMPORTANTE: Solo devuelve el código HTML completo. No agregues bloques de código markdown (```html). Solo el código crudo.
        """
        
        response = ai_engine.call_gemini(
            prompt=prompt,
            feature="newsletter_generation"
        )
        
        return response.get('content', "<html><body>Newsletter content placeholder</body></html>")
