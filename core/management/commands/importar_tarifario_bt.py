"""
Comando para importar el tarifario de Grupo BT Travel desde JSON.
Uso: python manage.py importar_tarifario_bt scripts/tarifario_bt_parsed.json
"""

import json
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bookings.models import (
    HotelTarifario,
    Proveedor,
    TarifaHabitacion,
    TarifarioProveedor,
    TipoHabitacion,
)


class Command(BaseCommand):
    help = "Importa tarifario de hoteles desde JSON parseado del PDF de BT Travel"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Ruta al archivo JSON del tarifario")
        parser.add_argument(
            "--proveedor-id", type=int, default=1, help="ID del proveedor (default: 1)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la importación sin guardar en la DB",
        )
        parser.add_argument(
            "--agencia-id", type=int, required=True, help="ID de la agencia (requerido)"
        )

    def handle(self, *args, **options):
        json_path = options["json_path"]
        proveedor_id = options["proveedor_id"]
        dry_run = options["dry_run"]
        agencia_id = options.get("agencia_id")

        # Cargar JSON
        self.stdout.write(f"Cargando JSON: {json_path}")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        hoteles_data = data.get("hoteles", [])
        self.stdout.write(f"Hoteles en JSON: {len(hoteles_data)}")

        if not hoteles_data:
            self.stdout.write(self.style.WARNING("No hay hoteles en el JSON"))
            return

        # Obtener proveedor (opcional - no bloquea importacion)
        proveedor = None
        try:
            proveedor = Proveedor.objects.get(id_proveedor=proveedor_id)
            self.stdout.write(f"Proveedor: {proveedor.nombre}")
        except (Proveedor.DoesNotExist, Exception):
            self.stdout.write(
                self.style.WARNING(
                    f"Proveedor {proveedor_id} no encontrado. Importando sin proveedor."
                )
            )

        # Crear tarifario
        if not dry_run:
            tarifario = TarifarioProveedor.objects.create(
                agencia_id=agencia_id,
                proveedor=proveedor,
                nombre="Tarifario Nacional Junio 2026 - Grupo BT Travel",
                fecha_vigencia_inicio=datetime.now().date(),
                fecha_vigencia_fin=datetime(2026, 12, 31).date(),
                comision_estandar=15.00,
                notas="Importado desde PDF de Grupo BT Travel",
            )
            self.stdout.write(self.style.SUCCESS(f"Tarifario creado: ID {tarifario.id}"))
        else:
            tarifario = None
            self.stdout.write(self.style.WARNING("MODO DRY RUN - No se guardara nada"))

        # Importar hoteles
        hoteles_creados = 0
        tipos_hab_creados = 0
        tarifas_creadas = 0
        hoteles_vistos = set()

        for hotel_data in hoteles_data:
            nombre = hotel_data["nombre"]
            regimen = hotel_data.get("regimen", "SD")

            # Evitar duplicados (mismo nombre + regimen)
            hotel_key = f"{nombre}_{regimen}"
            if hotel_key in hoteles_vistos:
                continue
            hoteles_vistos.add(hotel_key)

            try:
                if dry_run:
                    # Dry run: just print, no DB access
                    self.stdout.write(
                        f"  [DRY] {nombre} ({regimen}) - "
                        f"{len(hotel_data.get('tarifas', []))} tarifas"
                    )
                    hoteles_creados += 1
                    tipos_hab_creados += len(
                        set(
                            t.get("tipo_habitacion", "ESTANDAR")
                            for t in hotel_data.get("tarifas", [])
                        )
                    )
                    tarifas_creadas += len(hotel_data.get("tarifas", []))
                    continue

                with transaction.atomic():
                    # Crear hotel
                    if not dry_run:
                        hotel = HotelTarifario.objects.create(
                            tarifario=tarifario,
                            agencia_id=agencia_id,
                            nombre=nombre,
                            destino=hotel_data.get("destino", "Sin destino"),
                            regimen_default=regimen,
                            comision=hotel_data.get("comision", 15.0),
                            check_in=hotel_data.get("check_in", "15:00"),
                            check_out=hotel_data.get("check_out", "12:00"),
                            descripcion_corta=hotel_data.get("descripcion", "")[:300],
                            descripcion_larga=hotel_data.get("politicas", "")[:500],
                            activo=True,
                        )
                        hoteles_creados += 1
                    else:
                        hotel = None

                    # Agrupar tarifas por tipo de habitacion
                    tipos_habitacion = {}
                    for tarifa_data in hotel_data.get("tarifas", []):
                        tipo_hab_nombre = tarifa_data.get("tipo_habitacion", "ESTANDAR")

                        # Crear tipo de habitacion si no existe
                        if tipo_hab_nombre not in tipos_habitacion:
                            if not dry_run:
                                tipo_hab = TipoHabitacion.objects.create(
                                    hotel=hotel,
                                    nombre=tipo_hab_nombre,
                                    capacidad_adultos=2,
                                    capacidad_ninos=1,
                                    capacidad_total=3,
                                )
                                tipos_habitacion[tipo_hab_nombre] = tipo_hab
                                tipos_hab_creados += 1
                            else:
                                tipos_habitacion[tipo_hab_nombre] = None
                        else:
                            tipo_hab = tipos_habitacion[tipo_hab_nombre]

                        # Crear tarifa
                        if not dry_run and tipo_hab:
                            TarifaHabitacion.objects.create(
                                tipo_habitacion=tipo_hab,
                                fecha_inicio=tarifa_data.get("fecha_inicio"),
                                fecha_fin=tarifa_data.get("fecha_fin"),
                                nombre_temporada=tarifa_data.get("nombre_temporada", ""),
                                moneda=tarifa_data.get("moneda", "EUR"),
                                tarifa_sgl=tarifa_data.get("tarifa_sgl"),
                                tarifa_dbl=tarifa_data.get("tarifa_dbl"),
                                tarifa_tpl=tarifa_data.get("tarifa_tpl"),
                                tarifa_cpl=tarifa_data.get("tarifa_cpl"),
                                tarifa_nino=tarifa_data.get("tarifa_nino"),
                            )
                            tarifas_creadas += 1

                    self.stdout.write(
                        f"  {'[DRY] ' if dry_run else ''}[OK] {nombre} "
                        f"({regimen}) - {len(hotel_data.get('tarifas', []))} tarifas"
                    )

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  [ERROR] {nombre}: {str(e)[:100]}"))
                continue

        # Resumen
        self.stdout.write(self.style.SUCCESS("\n=== IMPORTACION COMPLETADA ==="))
        self.stdout.write(f"Hoteles creados: {hoteles_creados}")
        self.stdout.write(f"Tipos de habitacion: {tipos_hab_creados}")
        self.stdout.write(f"Tarifas creadas: {tarifas_creadas}")
        if dry_run:
            self.stdout.write(self.style.WARNING("(Modo DRY RUN - no se guardo nada)"))
