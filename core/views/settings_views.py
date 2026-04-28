import logging
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin

logger = logging.getLogger(__name__)


class BrandingSettingsView(LoginRequiredMixin, View):
    """
    Vista para configurar el Branding visual de la Agencia.
    GET  → renderiza el template con los valores actuales.
    POST → guarda color_primario, plantilla_boletos, plantilla_vouchers,
           plantilla_facturas vía HTMX y devuelve fragmento de éxito.
    """
    template_name = 'core/settings/branding.html'

    def _get_agencia(self, request):
        """Helper: devuelve la Agencia activa del usuario o None."""
        ua = request.user.agencias.filter(activo=True).first()
        return ua.agencia if ua else None

    def get(self, request, *args, **kwargs):
        # El context processor 'agency_context' inyecta 'current_agency' automáticamente
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        agencia = self._get_agencia(request)

        if not agencia:
            return HttpResponse(
                '<div class="text-red-400 font-bold p-4 bg-red-500/10 border border-red-500/30 rounded-xl">'
                '❌ Error: No se encontró una agencia activa para este usuario.</div>',
                status=400
            )

        # ——— Capturar campos del formulario ———
        agencia.color_primario = request.POST.get('color_primario', agencia.color_primario)
        agencia.plantilla_boletos = request.POST.get('plantilla_boletos', agencia.plantilla_boletos)
        agencia.plantilla_vouchers = request.POST.get('plantilla_vouchers', agencia.plantilla_vouchers)
        agencia.plantilla_facturas = request.POST.get('plantilla_facturas', agencia.plantilla_facturas)

        # Guardar solo los campos modificados para mayor eficiencia
        agencia.save(update_fields=[
            'color_primario',
            'plantilla_boletos',
            'plantilla_vouchers',
            'plantilla_facturas',
        ])

        logger.info(
            "🎨 Branding actualizado — Agencia: %s | Color: %s | TKT: %s | VCH: %s | FAC: %s",
            agencia.nombre_comercial or agencia.nombre,
            agencia.color_primario,
            agencia.plantilla_boletos,
            agencia.plantilla_vouchers,
            agencia.plantilla_facturas,
        )

        # ——— Respuesta HTMX (fragmento HTML, sin recargar la página) ———
        return HttpResponse('''
        <div id="form-response"
             class="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-xl
                    font-bold flex items-center justify-center gap-3 mt-4"
             x-data x-init="setTimeout(() => $el.remove(), 4000)">
            <span class="material-symbols-outlined text-emerald-400">check_circle</span>
            ¡Branding actualizado con éxito! Los próximos PDFs usarán el nuevo diseño.
        </div>
        ''')
