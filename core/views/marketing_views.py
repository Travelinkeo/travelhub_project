from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from core.services.marketing_service import MarketingService
import json

class GenerateAIImageView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        """
        Endpoint to generate an AI image for marketing.
        Expects: hotel_name, price, style, custom_text
        Returns: JSON with base64 image or error
        """
        try:
            # Handle both JSON and Form data (HTMX usually sends Form data)
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            hotel_name = data.get('hotel_name')
            price = data.get('price')
            style = data.get('style', 'Luxurious')
            custom_text = data.get('custom_text')
            
            if not hotel_name or not price:
                 return JsonResponse({'error': 'Missing required fields: hotel_name, price'}, status=400)

            # Call Service
            result = MarketingService.generate_ai_promo_image(
                hotel_name=hotel_name,
                price=price,
                style=style,
                custom_text=custom_text
            )
            
            if result and result.get('image'):
                return JsonResponse({'image_b64': result['image'], 'status': 'success'})
            else:
                error_msg = result.get('error') if result else 'Failed to generate image'
                return JsonResponse({'error': error_msg, 'status': 'error'}, status=500)
                
        except Exception as e:
            return JsonResponse({'error': str(e), 'status': 'error'}, status=500)
