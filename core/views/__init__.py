# Views package - Export active views

# Import specific views to expose them under core.views
from .boleto_views import BoletoUploadAPIView
from . import flights_views, catalogos_views, inventario_views, cotizaciones_views