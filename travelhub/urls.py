from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views
from core.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', dashboard.CEODashboardView.as_view(), name='ceo_dashboard'),
    path('dashboard/ia-insight/', dashboard.AIBusinessAdvisorView.as_view(), name='bi_ia_insight'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # path('asistente/', include('apps.accounting_assistant.urls', namespace='accounting_assistant')),
    path('contabilidad/', include('apps.contabilidad.urls', namespace='contabilidad')),
    path('api/contabilidad/', include('apps.contabilidad.urls', namespace='contabilidad_api')),  # API de tasas
    path('api/', include('apps.cotizaciones.urls')),
    path('finance/', include('apps.finance.urls')),
    path('marketing/', include('apps.marketing.urls')),
    path('cms/', include('apps.cms.urls')),
    path('crm/', include('apps.crm.urls', namespace='crm')),
    path('bookings/', include('apps.bookings.urls', namespace='bookings')),
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
# URL reload trigger