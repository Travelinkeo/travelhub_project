import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.template.loader import render_to_string
from core.models.cotizaciones import Cotizacion

def test_render():
    context = {'cotizacion': Cotizacion.objects.last()}
    
    print("\n--- TEST 1: Minimal File ---")
    try:
        r1 = render_to_string('cotizaciones/test_simple.html', context)
        print(f"Result: {r1.strip()}")
        if '{{' in r1: print("FAIL")
        else: print("SUCCESS")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- TEST 2: Real File Snippet ---")
    # I will read the real file and render it as a string instead of file path to check content validity
    with open('cotizaciones/templates/cotizaciones/plantilla_cotizacion.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    from django.template import Template, Context
    try:
        t = Template(content)
        r2 = t.render(Context(context))
        idx = r2.find("Estimado/a")
        print(f"Result Snippet: ...{r2[idx:idx+150]}...")
    except Exception as e:
        print(f"Template Object Error: {e}")

if __name__ == "__main__":
    test_render()
