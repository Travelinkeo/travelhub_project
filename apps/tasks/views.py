import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from core.security import get_agencia_from_request

from .models import ComentarioTarea, Tarea

logger = logging.getLogger(__name__)


class TaskBoardView(LoginRequiredMixin, View):
    """Kanban board con columnas por estado."""

    template_name = "tasks/board.html"

    def get(self, request):
        agencia = get_agencia_from_request(request)
        if not agencia:
            return render(request, self.template_name, {"sin_agencia": True})

        columnas = {}
        for estado, label in Tarea.ESTADOS:
            columnas[estado] = {
                "label": label,
                "tareas": Tarea.objects.filter(agencia=agencia, estado=estado).select_related(
                    "asignado_a", "creado_por"
                ),
            }

        ctx = {
            "columnas": columnas,
            "total": Tarea.objects.filter(agencia=agencia).count(),
            "current_agency": agencia,
        }
        return render(request, self.template_name, ctx)


class TaskCreateView(LoginRequiredMixin, View):
    """Crear nueva tarea."""

    template_name = "tasks/form.html"

    def get(self, request):
        return render(request, self.template_name, {"current_agency": get_agencia_from_request(request)})

    def post(self, request):
        agencia = get_agencia_from_request(request)
        if not agencia:
            return HttpResponse("No agency", status=400)

        tarea = Tarea.objects.create(
            agencia=agencia,
            titulo=request.POST.get("titulo", ""),
            descripcion=request.POST.get("descripcion", ""),
            prioridad=request.POST.get("prioridad", "media"),
            creado_por=request.user,
            asignado_a_id=request.POST.get("asignado_a") or None,
            fecha_vencimiento=request.POST.get("fecha_vencimiento") or None,
        )
        messages.success(request, "Tarea creada")
        if request.headers.get("HX-Request"):
            return redirect(reverse("tasks:board") + f"?highlight={tarea.id}")
        return redirect("tasks:board")


class TaskUpdateView(LoginRequiredMixin, View):
    """Editar tarea existente (HTMX partial)."""

    template_name = "tasks/form.html"

    def get(self, request, pk):
        tarea = get_object_or_404(Tarea, pk=pk, agencia=get_agencia_from_request(request))
        return render(request, "tasks/form.html", {"tarea": tarea, "editing": True})

    def post(self, request, pk):
        tarea = get_object_or_404(Tarea, pk=pk, agencia=get_agencia_from_request(request))
        tarea.titulo = request.POST.get("titulo", tarea.titulo)
        tarea.descripcion = request.POST.get("descripcion", tarea.descripcion)
        tarea.prioridad = request.POST.get("prioridad", tarea.prioridad)
        tarea.asignado_a_id = request.POST.get("asignado_a") or None
        tarea.fecha_vencimiento = request.POST.get("fecha_vencimiento") or None
        tarea.save()

        if estado := request.POST.get("estado"):
            tarea.estado = estado
            tarea.save()

        messages.success(request, "Tarea actualizada")
        if request.headers.get("HX-Request"):
            return redirect(reverse("tasks:board"))
        return redirect("tasks:board")


class TaskDetailView(LoginRequiredMixin, View):
    """Detalle de tarea con comentarios (HTMX modal/drawer)."""

    template_name = "tasks/detail.html"

    def get(self, request, pk):
        agencia = get_agencia_from_request(request)
        tarea = get_object_or_404(Tarea, pk=pk, agencia=agencia)
        comentarios = tarea.comentarios.select_related("usuario").all()
        return render(request, self.template_name, {
            "tarea": tarea,
            "comentarios": comentarios,
            "current_agency": agencia,
        })


class TaskDeleteView(LoginRequiredMixin, View):
    """Eliminar tarea."""

    def post(self, request, pk):
        tarea = get_object_or_404(Tarea, pk=pk, agencia=get_agencia_from_request(request))
        tarea.delete()
        messages.success(request, "Tarea eliminada")
        return redirect("tasks:board")


class TaskCommentView(LoginRequiredMixin, View):
    """Agregar comentario a tarea (HTMX)."""

    def post(self, request, pk):
        tarea = get_object_or_404(Tarea, pk=pk, agencia=get_agencia_from_request(request))
        texto = request.POST.get("texto", "").strip()
        if texto:
            ComentarioTarea.objects.create(
                tarea=tarea, usuario=request.user, texto=texto, agencia=tarea.agencia
            )
        return redirect(f"{reverse('tasks:detail', args=[pk])}#comentarios")
