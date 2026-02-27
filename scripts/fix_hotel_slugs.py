import os
import sys
import django
from django.utils.text import slugify

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models import HotelTarifario

def fix_slugs():
    hoteles = HotelTarifario.objects.all()
    print(f"Fixing slugs for {hoteles.count()} hotels...")
    for h in hoteles:
        if not h.slug:
            base_slug = slugify(f"{h.nombre}-{h.destino}")
            slug = base_slug
            counter = 1
            while HotelTarifario.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            h.slug = slug
            h.save()
            print(f"Slug set for {h.nombre}: {slug}")

if __name__ == "__main__":
    fix_slugs()
