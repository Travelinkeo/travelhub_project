import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models.personas import Cliente
from core.models_catalogos import Ciudad, Moneda, Pais, ProductoServicio, Proveedor

CATALOG_FILES = {
    'paises': 'fixtures/paises.json',
    'monedas': 'fixtures/monedas.json',
    'ciudades': 'fixtures/ciudades.json',
    'proveedores': 'fixtures/proveedores.json',
    'clientes': 'fixtures/clientes.json',
    'productos_servicios': 'fixtures/productos_servicios.json',
}

class Command(BaseCommand):
    help = "Carga o actualiza catálogos base (paises, monedas, ciudades opcional, proveedores, clientes, productos_servicios) desde JSON o CSV. Idempotente."

    def add_arguments(self, parser):
        parser.add_argument('--only', nargs='*', help='Limitar a uno o varios catálogos: paises monedas ciudades proveedores clientes productos_servicios')
        parser.add_argument('--format', choices=['json', 'csv', 'auto'], default='auto', help='Formato fuente si se usan archivos CSV alternativos')
        parser.add_argument('--dir', default='.', help='Directorio base donde buscar la carpeta fixtures o CSVs')
        parser.add_argument('--dry-run', action='store_true', help='Muestra qué haría sin escribir en la base de datos')
        parser.add_argument('--upsert', action='store_true', help='Actualiza registros existentes basados en claves únicas')

    def handle(self, *args, **options):
        selected = options.get('only')
        base_dir = Path(options['dir']).resolve()
        fmt = options['format']
        dry_run = options['dry_run']
        upsert = options['upsert']

        catalogs = CATALOG_FILES.keys() if not selected else selected
        unknown = set(catalogs) - set(CATALOG_FILES.keys())
        if unknown:
            raise CommandError(f"Catálogos desconocidos: {', '.join(unknown)}")

        summary = {}
        for cat in catalogs:
            file_rel = CATALOG_FILES[cat]
            file_path = base_dir / file_rel
            if not file_path.exists():
                self.stdout.write(self.style.WARNING(f"[SKIP] {cat}: archivo no encontrado {file_path}"))
                continue
            if fmt == 'auto':
                effective_fmt = file_path.suffix.lower().lstrip('.')
            else:
                effective_fmt = fmt
            try:
                if effective_fmt == 'json':
                    data = json.loads(file_path.read_text(encoding='utf-8') or '[]')
                else:  # csv
                    data = self._read_csv(file_path)
            except Exception as e:
                raise CommandError(f"Error leyendo {file_path}: {e}") from e
            if not isinstance(data, list):
                raise CommandError(f"El archivo {file_path} debe contener una lista de objetos")
            created, updated, skipped = 0, 0, 0
            if not dry_run:
                with transaction.atomic():
                    for row in data:
                        c, u, s = self._process_row(cat, row, upsert)
                        created += c
                        updated += u
                        skipped += s
            else:
                for row in data:
                    # Simular uniqueness heurística
                    _, _, s = self._process_row(cat, row, upsert, simulate=True)
                    if s:
                        skipped += 1
                    else:
                        created += 1
            summary[cat] = {'created': created, 'updated': updated, 'skipped': skipped}
            self.stdout.write(self.style.SUCCESS(f"[{cat}] creados={created} actualizados={updated} omitidos={skipped}"))

        self.stdout.write(self.style.MIGRATE_HEADING("Resumen"))
        for cat, stats in summary.items():
            self.stdout.write(f" - {cat}: {stats}")

    def _read_csv(self, path: Path):
        rows = []
        with path.open(newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
        return rows

    def _process_row(self, catalog: str, row: dict, upsert: bool, simulate: bool=False):
        row_upper_keys = {k.lower(): v for k, v in row.items()}
        try:
            if catalog == 'paises':
                return self._upsert_model(Pais, {'codigo_iso_2': row_upper_keys.get('codigo_iso_2')}, {
                    'codigo_iso_3': row_upper_keys.get('codigo_iso_3'),
                    'nombre': row_upper_keys.get('nombre'),
                }, upsert, simulate)
            if catalog == 'monedas':
                return self._upsert_model(Moneda, {'codigo_iso': row_upper_keys.get('codigo_iso')}, {
                    'nombre': row_upper_keys.get('nombre'),
                    'simbolo': row_upper_keys.get('simbolo'),
                    'es_moneda_local': self._to_bool(row_upper_keys.get('es_moneda_local')),
                }, upsert, simulate)
            if catalog == 'ciudades':
                # Requiere relacionar el país (lookup por codigo_iso_2 o codigo_iso_3)
                pais_codigo = row_upper_keys.get('pais_codigo_iso_2') or row_upper_keys.get('pais_codigo_iso_3')
                pais_obj = None
                if pais_codigo:
                    # Intentar primero ISO2 luego ISO3
                    pais_obj = Pais.objects.filter(codigo_iso_2__iexact=pais_codigo).first() or Pais.objects.filter(codigo_iso_3__iexact=pais_codigo).first()
                if not pais_obj:
                    # Si no encontramos país y estamos simulando, marcar como skip; en ejecución real lanzar para visibilidad
                    if simulate:
                        return 0,0,1
                    raise CommandError(f"País no encontrado para ciudad '{row_upper_keys.get('nombre')}' con código '{pais_codigo}'")
                lookup = {
                    'nombre': row_upper_keys.get('nombre'),
                    'pais': pais_obj,
                    'region_estado': row_upper_keys.get('region_estado') or None,
                }
                # unique_together = nombre, pais, region_estado
                return self._upsert_model(Ciudad, lookup, {}, upsert, simulate)
            if catalog == 'proveedores':
                return self._upsert_model(Proveedor, {'nombre': row_upper_keys.get('nombre')}, {
                    'tipo_proveedor': row_upper_keys.get('tipo_proveedor') or Proveedor.TipoProveedorChoices.OTRO,
                    'nivel_proveedor': row_upper_keys.get('nivel_proveedor') or Proveedor.NivelProveedorChoices.DIRECTO,
                    'contacto_nombre': row_upper_keys.get('contacto_nombre'),
                    'contacto_email': row_upper_keys.get('contacto_email'),
                    'contacto_telefono': row_upper_keys.get('contacto_telefono'),
                    'direccion': row_upper_keys.get('direccion'),
                    'activo': self._to_bool(row_upper_keys.get('activo', True)),
                }, upsert, simulate)
            if catalog == 'clientes':
                # Para clientes requerimos email único si viene definido
                lookup = {'email': row_upper_keys.get('email')} if row_upper_keys.get('email') else {'nombres': row_upper_keys.get('nombres'), 'apellidos': row_upper_keys.get('apellidos')}
                return self._upsert_model(Cliente, lookup, {
                    'nombres': row_upper_keys.get('nombres'),
                    'apellidos': row_upper_keys.get('apellidos'),
                    'telefono_principal': row_upper_keys.get('telefono_principal'),
                }, upsert, simulate)
            if catalog == 'productos_servicios':
                return self._upsert_model(ProductoServicio, {'nombre': row_upper_keys.get('nombre')}, {
                    'tipo_producto': row_upper_keys.get('tipo_producto') or ProductoServicio.TipoProductoChoices.OTRO,
                }, upsert, simulate)
        except Exception:
            if simulate:
                return 0,0,1
            raise
        return 0,0,1

    def _upsert_model(self, model, lookup: dict, defaults: dict, upsert: bool, simulate: bool):
        if None in lookup.values():
            return 0,0,1
        if simulate:
            exists = model.objects.filter(**lookup).exists()
            return (0,0,1) if exists else (1,0,0)
        obj = model.objects.filter(**lookup).first()
        if not obj and model.__name__ == 'Moneda':
            # Evitar IntegrityError: si ya existe otra moneda con el mismo nombre pero distinto codigo_iso
            nombre = defaults.get('nombre')
            if nombre:
                obj_nombre = model.objects.filter(nombre=nombre).first()
                if obj_nombre:
                    obj = obj_nombre  # tratamos este como el registro a potencialmente actualizar
        if obj:
            if upsert:
                changed = False
                for k,v in defaults.items():
                    if v is not None and getattr(obj, k, None) != v:
                        # Nunca cambiamos la clave primaria / lookup (ej: codigo_iso) ni sustituimos su valor
                        if k in lookup.keys():
                            continue
                        setattr(obj, k, v)
                        changed = True
                if changed:
                    obj.save()
                    return 0,1,0
                return 0,0,1
            return 0,0,1
        # Crear nuevo
        model.objects.create(**lookup, **{k:v for k,v in defaults.items() if v is not None})
        return 1,0,0

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {'1','true','t','yes','y','si','sí'}
