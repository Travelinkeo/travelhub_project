from django.core.management.base import BaseCommand
from apps.common.models import Moneda


class Command(BaseCommand):
    help = "Registra monedas de Latinoamérica (COP, MXN, PEN, ARS, BRL)"

    MONEDAS = [
        {"codigo_iso": "COP", "nombre": "Peso Colombiano", "simbolo": "$", "es_moneda_local": False},
        {"codigo_iso": "MXN", "nombre": "Peso Mexicano", "simbolo": "$", "es_moneda_local": False},
        {"codigo_iso": "PEN", "nombre": "Sol Peruano", "simbolo": "S/", "es_moneda_local": False},
        {"codigo_iso": "ARS", "nombre": "Peso Argentino", "simbolo": "$", "es_moneda_local": False},
        {"codigo_iso": "BRL", "nombre": "Real Brasileño", "simbolo": "R$", "es_moneda_local": False},
    ]

    def handle(self, *args, **options):
        creadas = 0
        for data in self.MONEDAS:
            _, created = Moneda.objects.get_or_create(
                codigo_iso=data["codigo_iso"],
                defaults=data,
            )
            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f'  ✅ {data["codigo_iso"]} — {data["nombre"]}'))
            else:
                self.stdout.write(f'  ℹ️  {data["codigo_iso"]} ya existe')

        self.stdout.write(self.style.SUCCESS(f"\n✅ {creadas} monedas creadas, {len(self.MONEDAS) - creadas} ya existían"))
