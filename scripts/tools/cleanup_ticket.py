import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

def delete_ticket(pk):
    try:
        boleto = BoletoImportado.objects.get(pk=pk)
        boleto.delete()
        print(f"Boleto #{pk} eliminado exitosamente.")
    except BoletoImportado.DoesNotExist:
        print(f"Boleto #{pk} no existe.")
    except Exception as e:
        print(f"Error al eliminar boleto #{pk}: {e}")

if __name__ == "__main__":
    delete_ticket(1189)
