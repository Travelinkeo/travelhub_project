from django.views.generic import ListView, DetailView
from django.db.models import Q
from core.models import HotelTarifario, Amenity

class HotelListView(ListView):
    model = HotelTarifario
    template_name = 'core/hotels/search.html'
    context_object_name = 'hoteles'
    paginate_by = 12

    def get_queryset(self):
        qs = HotelTarifario.objects.filter(activo=True).prefetch_related('amenidades')
        
        # Filtro de Búsqueda General
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q) | 
                Q(destino__icontains=q) |
                Q(descripcion_larga__icontains=q)
            )
            
        # Filtros Específicos
        destino = self.request.GET.get('destino')
        if destino:
            qs = qs.filter(destino__iexact=destino)
            
        categoria = self.request.GET.get('categoria')
        if categoria:
            qs = qs.filter(categoria=categoria)
            
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Datos para filtros laterales
        ctx['destinos'] = HotelTarifario.objects.filter(activo=True).values_list('destino', flat=True).distinct().order_by('destino')
        ctx['categorias'] = HotelTarifario.CATEGORIA_CHOICES
        ctx['amenidades'] = Amenity.objects.all().order_by('nombre')
        return ctx

class HotelDetailView(DetailView):
    model = HotelTarifario
    template_name = 'core/hotels/detail.html'
    context_object_name = 'hotel'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('imagenes', 'tipos_habitacion', 'amenidades', 'tipos_habitacion__tarifas')

from django.http import HttpResponse
from core.services.marketing_service import MarketingService

def download_story_view(request, slug):
    """Genera y descarga la Story de Instagram"""
    hotel = HotelTarifario.objects.get(slug=slug)
    
    # Intentar obtener agencia del usuario logueado (si es Vendedor)
    agencia_id = None
    if request.user.is_authenticated:
        # Check if user belongs to an agency (via UsuarioAgencia or simple field)
        # Assuming simple linkage or just pass None to use default fallback in service
        pass

    img_io = MarketingService.generate_instagram_story(hotel.pk, agencia_id)
    
    response = HttpResponse(img_io.read(), content_type="image/jpeg")
    response['Content-Disposition'] = f'attachment; filename="story_{hotel.slug}.jpg"'
    return response

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.services.ai_copywriter import AICopywriter

class GenerateCopyAPI(APIView):
    """Genera textos de venta para redes sociales con IA."""
    
    def post(self, request):
        hotel_id = request.data.get('hotel_id')
        tone = request.data.get('tone', 'AVENTURERO')
        
        if not hotel_id:
            return Response({'error': 'Falta hotel_id'}, status=status.HTTP_400_BAD_REQUEST)
            
        service = AICopywriter()
        caption = service.generate_caption(hotel_id, tone)
        
        return Response({'caption': caption})
