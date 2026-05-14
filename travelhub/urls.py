from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from core.views import dashboard

urlpatterns = [
    # Administración
    path('admin/', admin.site.urls),
    
    # Dashboard CEO (Global)
    path('dashboard/ceo/', dashboard.CEODashboardView.as_view(), name='ceo_dashboard'),
    path('dashboard/ia-insight/', dashboard.AIBusinessAdvisorView.as_view(), name='bi_ia_insight'),
    
    # Red de Aplicaciones y Núcleo (Dispatcher Centralizado)
    path('', include('core.urls')),
    
    # 🗂️ PWA ROOT FILES
    path('manifest.json', TemplateView.as_view(template_name='manifest.json', content_type='application/json')),
    path('service-worker.js', TemplateView.as_view(template_name='service-worker.js', content_type='application/javascript')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = _("Administración de TravelHub")
admin.site.site_title = _("Portal de Administración TravelHub")
admin.site.index_title = _("Bienvenido al Portal de Administración de TravelHub")