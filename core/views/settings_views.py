import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

logger = logging.getLogger(__name__)


class BrandingSettingsView(LoginRequiredMixin, View):
    template_name = "core/settings/branding.html"

    def _get_agencia(self, request):
        ua = request.user.agencias.filter(activo=True).first()
        return ua.agencia if ua else None

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
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

        branding.save(
            update_fields=[
                f for f in [
                    "color_primario",
                    "plantilla_boletos",
                    "plantilla_vouchers",
                    "plantilla_facturas",
                    "ui_theme",
                ] if request.POST.get(f)
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
