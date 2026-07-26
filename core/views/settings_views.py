import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from core.security import get_agencia_from_request

logger = logging.getLogger(__name__)


class BrandingSettingsView(LoginRequiredMixin, View):
    """BrandingSettingsView."""

    template_name = "core/settings/branding.html"

    def _get_agencia(self, request):
        """_get_agencia."""
        return get_agencia_from_request(request)

    def get(self, request, *args, **kwargs):
        """get."""
        agencia = self._get_agencia(request)
        branding = agencia.branding if agencia else None
        return render(
            request,
            self.template_name,
            {
                "current_agency": agencia,
                "branding": branding,
            },
        )

    def post(self, request, *args, **kwargs):
        """post."""
        agencia = self._get_agencia(request)

        if not agencia:
            return HttpResponse(
                '<div class="text-red-400 font-bold p-4 bg-red-500/10 border border-red-500/30 rounded-xl">'
                "Error: No se encontro una agencia activa para este usuario.</div>",
                status=400,
            )

        branding = agencia.branding

        color = request.POST.get("color_primario", "")
        if color:
            branding.color_primario = color

        tkt = request.POST.get("plantilla_boletos", "")
        if tkt:
            branding.plantilla_boletos = tkt

        vch = request.POST.get("plantilla_vouchers", "")
        if vch:
            branding.plantilla_vouchers = vch

        fac = request.POST.get("plantilla_facturas", "")
        if fac:
            branding.plantilla_facturas = fac

        theme = request.POST.get("ui_theme", "")
        if theme:
            branding.ui_theme = theme

        template_pack = request.POST.get("template_pack", "")
        if template_pack:
            branding.template_pack = template_pack

        color_secundario = request.POST.get("color_secundario", "")
        if color_secundario:
            branding.color_secundario = color_secundario

        branding.save(
            update_fields=[
                f
                for f in [
                    "color_primario",
                    "color_secundario",
                    "plantilla_boletos",
                    "plantilla_vouchers",
                    "plantilla_facturas",
                    "ui_theme",
                    "template_pack",
                ]
                if request.POST.get(f)
            ]
        )

        logger.info(
            "Branding actualizado - Agencia: %s | Color: %s | Tema: %s",
            agencia.nombre_comercial or agencia.nombre,
            branding.color_primario,
            branding.ui_theme,
        )

        return HttpResponse(
            '<div id="form-response"'
            ' class="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-xl'
            ' font-bold flex items-center justify-center gap-3 mt-4"'
            ' x-data x-init="setTimeout(() => $el.remove(), 4000)">'
            '<span class="material-symbols-outlined text-emerald-400">check_circle</span>'
            " Branding actualizado con exito!</div>"
        )
