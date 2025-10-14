from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('asistente/', include('accounting_assistant.urls', namespace='accounting_assistant')),
    path('contabilidad/', include('contabilidad.urls', namespace='contabilidad')),
    path('api/', include('cotizaciones.urls')),
    path('', include('core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = _("Administración de TravelHub")
admin.site.site_title = _("Portal de Administración TravelHub")
admin.site.index_title = _("Bienvenido al Portal de Administración de TravelHub")