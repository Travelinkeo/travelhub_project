import json
import logging
import os

import pandas as pd
from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage

from apps.common.models import Moneda
from apps.crm.models import Cliente

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, time_limit=300, soft_time_limit=240)
def importar_clientes_excel_task(self, agencia_id, file_path, column_mapping, user_id=None):
    """
    Importa clientes desde un archivo Excel/CSV.

    column_mapping: dict {"campo_destino": "nombre_columna_excel"}
    """
    creados = 0
    duplicados = 0
    errores = []
    total = 0

    try:
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        if file_path.endswith(".csv"):
            df = pd.read_csv(full_path)
        else:
            df = pd.read_excel(full_path)

        total = len(df)

        for idx, row in df.iterrows():
            try:
                nombres = row.get(column_mapping.get("nombres", ""), "")
                if pd.isna(nombres) or not str(nombres).strip():
                    errores.append({"fila": int(idx) + 2, "error": "Nombres es requerido"})
                    continue

                nombres = str(nombres).strip()
                apellidos = str(row.get(column_mapping.get("apellidos", ""), "") or "").strip()
                email = str(row.get(column_mapping.get("email", ""), "") or "").strip()
                telefono = str(row.get(column_mapping.get("telefono_principal", ""), "") or "").strip()

                # Detección de duplicados
                dup_query = Cliente.objects.filter(agencia_id=agencia_id)
                if email:
                    dup_query = dup_query.filter(email=email)
                elif telefono:
                    dup_query = dup_query.filter(telefono_principal=telefono)
                else:
                    dup_query = dup_query.filter(
                        nombres__iexact=nombres, apellidos__iexact=apellidos
                    )

                if dup_query.exists():
                    duplicados += 1
                    continue

                kwargs = {
                    "agencia_id": agencia_id,
                    "nombres": nombres,
                    "apellidos": apellidos or None,
                }

                # Mapear campos opcionales
                campo_map = {
                    "email": "email",
                    "telefono_principal": "telefono_principal",
                    "telefono_secundario": "telefono_secundario",
                    "cedula_identidad": "cedula_identidad",
                    "numero_pasaporte": "numero_pasaporte",
                    "direccion": "direccion",
                    "nombre_empresa": "nombre_empresa",
                    "tipo_cliente": "tipo_cliente",
                    "notas_cliente": "notas_cliente",
                }

                for col_excel, field_name in column_mapping.items():
                    if field_name in campo_map and field_name not in ("nombres", "apellidos"):
                        val = row.get(col_excel)
                        if pd.notna(val):
                            kwargs[campo_map[field_name]] = str(val).strip()

                Cliente.objects.create(**kwargs)
                creados += 1

            except Exception as e:
                errores.append({"fila": int(idx) + 2, "error": str(e)[:200]})
                logger.warning(f"Error importando fila {idx}: {e}")

    except Exception as e:
        logger.error(f"Error en importación: {e}")
        return {"creados": creados, "duplicados": duplicados, "errores": [{"fila": 0, "error": str(e)[:500]}]}

    finally:
        # Limpiar archivo temporal
        try:
            default_storage.delete(file_path)
        except Exception:
            pass

    return {
        "creados": creados,
        "duplicados": duplicados,
        "errores": errores[:50],
        "total": total,
    }
