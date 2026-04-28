import base64
from django.views.generic import TemplateView, View
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.models import HotelTarifario
from .models import Campania, ActivoMarketing
from .services.flyer_service import FlyerService
from .services.copywriter_service import CopywriterService
from .services.promotion_service import PromotionService
from .services.forecast_service import AIForecastService

class MarketingDashboardView(TemplateView):
    template_name = 'marketing/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campanias'] = Campania.objects.all().order_by('-id')[:5]
        context['hoteles'] = HotelTarifario.objects.all()
        context['activos_recientes'] = ActivoMarketing.objects.all().order_by('-fecha_creacion')[:10]
        return context

class SocialHubView(TemplateView):
    template_name = 'marketing/social_hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoteles'] = HotelTarifario.objects.all()
        return context

class GenerarFlyerView(View):
    def post(self, request, *args, **kwargs):
        hotel_id = request.POST.get('hotel_id')
        destino = request.POST.get('destino')
        precio = request.POST.get('precio', '$0')
        aerolinea = request.POST.get('aerolinea')
        
        service = FlyerService()
        # El servicio ahora maneja hotel_id internamente para extraer datos ricos
        flyer_buffer = service.generate_flyer(
            destination=destino, 
            price=precio, 
            airline=aerolinea, 
            hotel_id=hotel_id
        )
        
        # Opcional: Guardar el activo en la DB
        if hotel_id:
             hotel = HotelTarifario.objects.filter(pk=hotel_id).first()
             if hotel:
                 activo = ActivoMarketing.objects.create(
                     hotel=hotel,
                     tipo=ActivoMarketing.TipoActivo.FLYER,
                     generado_por_ia=True,
                     prompt_utilizado=f"Destino: {destino}, Precio: {precio}, Hotel ID: {hotel_id}"
                 )
                 # Guardar el archivo físicamente
                 from django.core.files.base import ContentFile
                 activo.archivo.save(f"flyer_{activo.id}.jpg", ContentFile(flyer_buffer.getvalue()), save=True)

        # Convertir a Base64 para visualización HTMX suave
        img_str = base64.b64encode(flyer_buffer.getvalue()).decode('utf-8')
        html_response = f'<img src="data:image/jpeg;base64,{img_str}" class="max-w-md rounded-2xl shadow-2xl animate-in fade-in zoom-in duration-500">'
        
        return HttpResponse(html_response)

class GenerarCopyView(View):
    def post(self, request, *args, **kwargs):
        hotel_id = request.POST.get('hotel_id')
        tono = request.POST.get('tono', 'AVENTURERO')
        
        if not hotel_id:
            return HttpResponse("Error: Debes seleccionar un hotel.", status=400)
            
        service = CopywriterService()
        copy = service.generate_caption(hotel_id, tono)
        
        return HttpResponse(copy)

class GenerarSocialMediaAdvancedView(View):
    def post(self, request, *args, **kwargs):
        hotel_id = request.POST.get('hotel_id')
        tono = request.POST.get('tono', 'LUXURY')
        extra_prompt = request.POST.get('extra_prompt')
        
        if not hotel_id:
            return HttpResponse("Error: Debes seleccionar un hotel.", status=400)
            
        service = CopywriterService()
        package = service.generate_social_package(hotel_id, tono, extra_prompt)
        
        if "error" in package:
            return HttpResponse(f"Error: {package['error']}", status=500)
            
        # Persistencia Automática
        try:
            from core.models.agencia import Agencia
            hotel = HotelTarifario.objects.get(pk=hotel_id)
            agencia = Agencia.objects.first() # Simplificación SaaS: Usar la agencia activa
            
            campania_feed, _ = Campania.objects.get_or_create(
                nombre="Feed Social Automático",
                agencia=agencia,
                defaults={'estado': Campania.EstadoCampania.BORRADOR}
            )
            
            # Crear activo con metadatos IA
            # package es un dict (pydantic model convertido a dict si se usa .dict() o similar)
            # En CopywriterService, ai_engine devuelve el dict del package
            
            # Extraer primer texto para el campo legacy texto_caption
            first_caption = ""
            if isinstance(package, dict) and package.get('variants'):
                first_caption = package['variants'][0].get('text', '')
            elif hasattr(package, 'variants'): # Si es el objeto Pydantic
                first_caption = package.variants[0].text
                package = package.dict() # Convertir a dict para JSONField

            ActivoMarketing.objects.create(
                hotel=hotel,
                campania=campania_feed,
                tipo=ActivoMarketing.TipoActivo.COPY,
                texto_caption=first_caption,
                datos_ia=package,
                prompt_utilizado=f"Tono: {tono}. Extra: {extra_prompt or 'N/A'}",
                generado_por_ia=True
            )
        except Exception as e:
            # No bloqueamos la respuesta si falla el guardado, pero logueamos
            import logging
            logging.getLogger(__name__).error(f"Error persistiendo activo marketing: {e}")

        # Pasar los datos al template parcial para renderizar
        return render(request, 'marketing/partials/social_package_result.html', {
            'package': package,
            'hotel': HotelTarifario.objects.get(pk=hotel_id)
        })

class MarketingFeedView(TemplateView):
    template_name = 'marketing/partials/feed_gallery.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Mostrar los últimos 12 contenidos generados
        context['activos'] = ActivoMarketing.objects.filter(
            generado_por_ia=True
        ).select_related('hotel').order_by('-fecha_creacion')[:12]
        return context

class AIForecastView(TemplateView):
    template_name = 'marketing/forecast.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = AIForecastService()
        forecast_data = service.generate_forecast()
        
        # Validar si hubo error en el servicio de IA
        if isinstance(forecast_data, dict) and "error" in forecast_data:
            context['ai_error'] = forecast_data['error']
            context['forecast'] = None
        else:
            context['forecast'] = forecast_data
            
        return context
