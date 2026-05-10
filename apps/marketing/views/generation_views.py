import base64
from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.shortcuts import render
from apps.bookings.models import HotelTarifario
from apps.marketing.models import Campania, ActivoMarketing
from apps.marketing.services.flyer_service import FlyerService
from apps.marketing.services.copywriter_service import CopywriterService
from apps.marketing.services.forecast_service import AIForecastService
import logging

logger = logging.getLogger(__name__)


class GenerarFlyerView(View):
    def post(self, request, *args, **kwargs):
        hotel_id = request.POST.get('hotel_id')
        destino = request.POST.get('destino')
        precio = request.POST.get('precio', '$0')
        aerolinea = request.POST.get('aerolinea')

        service = FlyerService()
        flyer_buffer = service.generate_flyer(
            destination=destino,
            price=precio,
            airline=aerolinea,
            hotel_id=hotel_id
        )

        if hotel_id:
            hotel = HotelTarifario.objects.filter(pk=hotel_id).first()
            if hotel:
                activo = ActivoMarketing.objects.create(
                    hotel=hotel,
                    tipo=ActivoMarketing.TipoActivo.FLYER,
                    generado_por_ia=True,
                    prompt_utilizado=f"Destino: {destino}, Precio: {precio}, Hotel ID: {hotel_id}"
                )
                from django.core.files.base import ContentFile
                activo.archivo.save(f"flyer_{activo.id}.jpg", ContentFile(flyer_buffer.getvalue()), save=True)

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

        try:
            hotel = HotelTarifario.objects.get(pk=hotel_id)
            agencia = getattr(request, 'agencia', None)

            if not agencia:
                logger.warning(f"Intento de generar activo de marketing sin contexto de agencia para hotel {hotel_id}")
                return HttpResponse("Error: Contexto de agencia no encontrado.", status=403)

            campania_feed, _ = Campania.objects.get_or_create(
                nombre="Feed Social Automático",
                agencia=agencia,
                defaults={'estado': Campania.EstadoCampania.BORRADOR}
            )

            first_caption = ""
            if isinstance(package, dict) and package.get('variants'):
                first_caption = package['variants'][0].get('text', '')
            elif hasattr(package, 'variants'):
                first_caption = package.variants[0].text
                package = package.dict()

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
            logger.error(f"Error persistiendo activo marketing: {e}")

        return render(request, 'marketing/partials/social_package_result.html', {
            'package': package,
            'hotel': HotelTarifario.objects.get(pk=hotel_id)
        })


class MarketingFeedView(TemplateView):
    template_name = 'marketing/partials/feed_gallery.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

        if isinstance(forecast_data, dict) and "error" in forecast_data:
            context['ai_error'] = forecast_data['error']
            context['forecast'] = None
        else:
            context['forecast'] = forecast_data

        return context