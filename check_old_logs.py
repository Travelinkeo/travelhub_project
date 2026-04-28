
import os
import django
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

old_msg = "El re-procesamiento falló. Revise el log de parseo del boleto."
count = BoletoImportado.all_objects.filter(log_parseo=old_msg).count()
print(f"Total with old msg: {count}")

last_err = BoletoImportado.all_objects.filter(estado_parseo='ERR').order_by('-fecha_subida').first()
if last_err:
    print(f"Last ERR ID: {last_err.pk}")
    print(f"Last ERR Log: {last_err.log_parseo}")
