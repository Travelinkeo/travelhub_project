"""Vistas (views) de la aplicación crm.
"""

import json
import logging
import os
import uuid

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from core.api import SaaSMixin, get_user_active_agency

from ..models import Cliente

logger = logging.getLogger(__name__)

CAMPOS_CLIENTE = [
    {"value": "nombres", "label": "Nombres", "required": True},
    {"value": "apellidos", "label": "Apellidos", "required": False},
    {"value": "email", "label": "Email", "required": False},
    {"value": "telefono_principal", "label": "Teléfono Principal", "required": False},
    {"value": "telefono_secundario", "label": "Teléfono Secundario", "required": False},
    {"value": "cedula_identidad", "label": "Cédula de Identidad", "required": False},
    {"value": "numero_pasaporte", "label": "Número de Pasaporte", "required": False},
    {"value": "direccion", "label": "Dirección", "required": False},
    {"value": "nombre_empresa", "label": "Empresa", "required": False},
    {"value": "tipo_cliente", "label": "Tipo de Cliente (IND/COR/FRE/MAY)", "required": False},
    {"value": "fecha_nacimiento", "label": "Fecha de Nacimiento", "required": False},
    {"value": "notas_cliente", "label": "Notas", "required": False},
]


class ImportarClientesView(SaaSMixin, LoginRequiredMixin, View):
    """Paso 1: Subir archivo Excel/CSV y mostrar preview."""

    template_name = "crm/importar_clientes.html"

    def get(self, request):
        # get: Get. Args: según implementación. Returns: según implementación.
        return render(request, self.template_name, {"campos": CAMPOS_CLIENTE})

    def post(self, request):
        # post: Post. Args: según implementación. Returns: según implementación.
        agencia = get_user_active_agency(request.user)
        if not agencia:
            messages.error(request, "No hay agencia activa")
            return redirect("crm:cliente_list")

        archivo = request.FILES.get("archivo")
        if not archivo:
            messages.error(request, "Debes seleccionar un archivo")
            return redirect("crm:importar_clientes")

        ext = os.path.splitext(archivo.name)[1].lower()
        if ext not in (".xlsx", ".xls", ".csv"):
            messages.error(request, "Formato no soportado. Usa .xlsx, .xls o .csv")
            return redirect("crm:importar_clientes")

        # Guardar archivo temporal
        session_id = str(uuid.uuid4())
        temp_path = f"imports/{session_id}{ext}"
        saved_path = default_storage.save(temp_path, archivo)

        try:
            full_path = os.path.join(settings.MEDIA_ROOT, saved_path)
            if ext == ".csv":
                df = pd.read_csv(full_path)
            else:
                df = pd.read_excel(full_path)

            columnas_origen = list(df.columns)
            preview_rows = json.loads(df.head(10).to_json(orient="records"))

            # Almacenar info en sesión
            request.session["import_session_id"] = session_id
            request.session["import_file_path"] = saved_path
            request.session["import_columnas"] = columnas_origen
            request.session["import_filas"] = len(df)

            return render(request, "crm/mapeo_columnas.html", {
                "campos": CAMPOS_CLIENTE,
                "campos_json": json.dumps(CAMPOS_CLIENTE),
                "columnas_origen": columnas_origen,
                "preview_rows": preview_rows,
                "preview_rows_json": json.dumps(preview_rows),
                "total_filas": len(df),
                "session_id": session_id,
            })

        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            default_storage.delete(saved_path)
            messages.error(request, f"Error al leer el archivo: {str(e)}")
            return redirect("crm:importar_clientes")


    def delete(self, request):
        """Limpiar sesión de importación."""
        for key in ["import_session_id", "import_file_path", "import_columnas", "import_filas"]:
            request.session.pop(key, None)
        return JsonResponse({"ok": True})


class MapeoColumnasView(SaaSMixin, LoginRequiredMixin, View):
    """Paso 2: Confirmar mapeo de columnas y disparar importación."""

    template_result = "crm/importar_resultados.html"

    def post(self, request):
        # post: Post. Args: según implementación. Returns: según implementación.
        agencia = get_user_active_agency(request.user)
        if not agencia:
            return JsonResponse({"error": "No hay agencia activa"}, status=400)

        # Verificar sesión
        session_id = request.session.get("import_session_id")
        file_path = request.session.get("import_file_path")
        if not session_id or not file_path:
            return JsonResponse({"error": "Sesión de importación expirada. Vuelve a subir el archivo."}, status=400)

        # Obtener mapeo del formulario
        mapping_raw = request.POST.get("mapping", "{}")
        try:
            column_mapping = json.loads(mapping_raw)
        except json.JSONDecodeError:
            column_mapping = {}

        # Validar que nombres esté mapeado
        if "nombres" not in [v for v in column_mapping.values()]:
            return JsonResponse({"error": "El campo 'Nombres' es obligatorio"}, status=400)

        # Invertir mapping: {col_excel: campo_destino}
        mapping = {}
        for col_excel, campo_destino in column_mapping.items():
            mapping[campo_destino] = col_excel

        # Disparar tarea asíncrona
        from .tasks.import_tasks import importar_clientes_excel_task

        task = importar_clientes_excel_task.delay(
            agencia_id=agencia.id,
            file_path=file_path,
            column_mapping=mapping,
            user_id=request.user.id,
        )

        # Limpiar sesión
        for key in ["import_session_id", "import_file_path", "import_columnas", "import_filas"]:
            request.session.pop(key, None)

        return render(request, self.template_result, {
            "task_id": task.id,
            "total_filas": request.session.get("import_filas", 0),
        })


class ImportarClientesProgressView(View):
    """Verificar estado de una importación en progreso."""

    def get(self, request, task_id):
        # get: Get. Args: según implementación. Returns: según implementación.
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        if result.ready():
            data = result.result or {}
            return JsonResponse({
                "ready": True,
                "success": result.successful(),
                "creados": data.get("creados", 0),
                "duplicados": data.get("duplicados", 0),
                "errores": data.get("errores", []),
                "total": data.get("total", 0),
            })
        return JsonResponse({"ready": False})
