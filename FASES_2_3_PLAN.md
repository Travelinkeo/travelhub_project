# FASES 2 Y 3: MEJORAS TRAVELHUB SAAS

## 🟡 FASE 2: MEDIA (Meses 3-6)
Objetivo: Testing (85% → 95%), Seguridad (85% → 95%), Refactorización Frontend (HTMX + Alpine.js)

### 2.1 TESTING (85% → 95%)
#### Acción 2.1.1: Tests de Integración para Parsers GDS
```python
# tests/parsers/test_sabre_parser_enhanced.py
@pytest.fixture
def sabre_ticket_content():
    with open('tests/fixtures/sabre_ticket_sample.txt', 'r') as f:
        return f.read()

def test_sabre_parser_integration(sabre_ticket_content):
    parser = SabreParser(sabre_ticket_content)
    result = parser.parse()
    assert 'boleto_id' in result
    assert result['total'] > 0
```

### 2.2 SEGURIDAD (85% → 95%)
#### Acción 2.2.1: Auditoría Automática de Dependencias
Problema: requirements.txt tiene 58 dependencias que pueden quedar obsoletas o presentar vulnerabilidades.
Acción: Integrar safety en el pipeline de GitHub Actions.
```yaml
# .github/workflows/security.yml
name: Security Audit
steps:
  - uses: actions/checkout@v3
  - name: Run Safety Check
    run: |
      pip install safety
      safety check -r requirements.txt
```

#### Acción 2.2.2: Rate Limiting para Endpoints de IA y Parsers
Problema: Los endpoints que consumen la API de Gemini o Vertex AI son costosos computacionalmente y pueden ser víctimas de abuso.
Acción: Implementar Throttling nativo de Django REST Framework respaldado por Redis.
```python
# core/api/throttling.py
from rest_framework.throttling import UserRateThrottle

class IAParserRateThrottle(UserRateThrottle):
    scope = 'ia_parsers'

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'ia_parsers': '100/day', # Límite por usuario/agencia
    }
}
```

### 2.3 REFACTORIZACIÓN FRONTEND (HTMX + Alpine.js)
#### Acción 2.3.1: Implementar HtmxResponseMixin (Reemplazo del BootstrapMixin)
Objetivo: Eliminar recargas de página completa y servir HTML parcial para que la interfaz sea reactiva.
Archivo a crear: `core/mixins/htmx_mixins.py`
```python
class HtmxResponseMixin:
    """Devuelve un template parcial si la petición viene de HTMX"""
    htmx_template_name = None

    def get_template_names(self):
        if self.request.headers.get('HX-Request') and self.htmx_template_name:
            return [self.htmx_template_name]
        return super().get_template_names()
```

#### Acción 2.3.2: Delegar estados efímeros a Alpine.js
Objetivo: Limpiar el código JavaScript disperso y centralizar la lógica de modales y tabs.
```html
<!-- Ejemplo en templates/ventas/dashboard.html -->
<div x-data="{ tabActivo: 'boletos', modalAbierto: false }">
    <!-- Navegación reactiva -->
    <button @click="tabActivo = 'boletos'">Boletos</button>
    <button @click="tabActivo = 'facturas'">Facturas</button>

    <!-- Carga de datos asíncrona con HTMX disparada por Alpine -->
    <div x-show="tabActivo === 'boletos'" 
         hx-get="/api/boletos/recientes/" 
         hx-trigger="load, refreshBoletos from:body">
         Cargando boletos...
    </div>
</div>
```

---

## 🟢 FASE 3: BAJA (Meses 6+)
Objetivo: Escalar operaciones, automatizar monitoreo y documentar para terceros.

### 3.1 COMPLETAR INTEGRACIÓN IA
#### Acción 3.1.1: Finalizar Soporte Amadeus GDS
Integrar las reglas de parsing específicas de Amadeus.
Diseñar un sistema de "Fallback a Gemini": Si las expresiones regulares (Regex) fallan al leer un boleto de Amadeus debido a un formato anómalo, enviar el texto crudo al SDK de Google AI para que extraiga el JSON como último recurso.

### 3.2 DEVOPS Y MONITOREO
#### Acción 3.2.1: Monitoreo Avanzado de Tareas Asíncronas
Problema: Actualmente es difícil rastrear si una tarea de Celery (ej. envío de correos masivos o consolidación nocturna) falla en silencio.
Acción: Integrar el SDK de Sentry para Celery en settings.py para capturar excepciones en tiempo real y trazar cuellos de botella en la base de datos.

### 3.3 DOCUMENTACIÓN Y API
#### Acción 3.3.1: Documentación OpenAPI Automatizada
Objetivo: Dado que ya hay 61 endpoints RESTful construidos con ViewSets, se debe automatizar su documentación para facilitar la integración de las agencias cliente.
Acción: Instalar y configurar drf-spectacular para autogenerar una interfaz Swagger UI basándose en los serializers de Django existentes.
