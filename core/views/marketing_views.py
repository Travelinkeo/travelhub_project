from django.shortcuts import render
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from core.services.marketing_service import MarketingService
import json

class MarketingHubView(LoginRequiredMixin, View):
    """
    Vista principal del Centro de Marketing IA.
    """
    template_name = "marketing/marketing_hub.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        """Maneja las peticiones AJAX/HTMX para generación de contenido."""
        action = request.POST.get('action')
        
        if action == 'generate_caption':
            producto = request.POST.get('producto')
            destino = request.POST.get('destino')
            detalles = request.POST.get('detalles')
            tono = request.POST.get('tono', 'AVENTURERO')
            
            caption = MarketingService.generate_social_caption(producto, destino, detalles, tono)
            return JsonResponse({'caption': caption})

        elif action == 'generate_newsletter':
            # Simulación de ofertas para el ejemplo o recibir desde form
            ofertas_json = request.POST.get('ofertas_json')
            if ofertas_json:
                ofertas = json.loads(ofertas_json)
            else:
                ofertas = [
                    {'titulo': 'Cancún Todo Incluido', 'precio': '$499'},
                    {'titulo': 'Crucero por el Caribe', 'precio': '$850'}
                ]
            
            html_content = MarketingService.generate_email_newsletter(ofertas)
            return JsonResponse({'html_content': html_content})

        return JsonResponse({'error': 'Acción no válida'}, status=400)

class GenerateAIImageView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        """
        Endpoint to generate an AI image for marketing.
        """
        try:
            data = request.POST
            hotel_name = data.get('hotel_name')
            price = data.get('price')
            style = data.get('style', 'Luxurious')
            custom_text = data.get('custom_text')
            
            if not hotel_name or not price:
                 return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

            result = MarketingService.generate_ai_promo_image(
                hotel_name=hotel_name,
                price=price,
                style=style,
                custom_text=custom_text
            )
            
            if result and result.get('image'):
                return JsonResponse({'image_b64': result['image'], 'status': 'success'})
            else:
                return JsonResponse({'error': result.get('error', 'Error en generación'), 'status': 'error'}, status=500)
                
        except Exception as e:
            return JsonResponse({'error': str(e), 'status': 'error'}, status=500)
