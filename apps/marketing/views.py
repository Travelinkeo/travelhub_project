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

class MarketingDashboardView(TemplateView):
    template_name = 'marketing/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campanias'] = Campania.objects.all().order_by('-id')[:5]
        context['hoteles'] = HotelTarifario.objects.all()
        context['activos_recientes'] = ActivoMarketing.objects.all().order_by('-fecha_creacion')[:10]
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
