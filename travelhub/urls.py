from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('asistente/', include('accounting_assistant.urls', namespace='accounting_assistant')),
    path('contabilidad/', include('contabilidad.urls', namespace='contabilidad')),
    path('api/contabilidad/', include('contabilidad.urls', namespace='contabilidad_api')),  # API de tasas
    path('api/', include('cotizaciones.urls')),
    path('finance/', include('apps.finance.urls')),
    path('marketing/', include('apps.marketing.urls')),
    path('cms/', include('apps.cms.urls')),
    path('crm/', include('apps.crm.urls', namespace='crm')),
    path('bookings/', include('apps.bookings.urls', namespace='bookings')),
    path('', include('core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = _("Administración de TravelHub")
admin.site.site_title = _("Portal de Administración TravelHub")
admin.site.index_title = _("Bienvenido al Portal de Administración de TravelHub")