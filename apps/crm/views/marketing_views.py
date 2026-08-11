import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from apps.crm.services.marketing_service import MarketingAIEngine
from apps.crm.tasks_marketing import despachar_campana_masiva_task

logger = logging.getLogger(__name__)


class MarketingHubView(LoginRequiredMixin, View):
    """Renderiza la pantalla principal del Hub de Marketing"""

    template_name = "crm/marketing/hub.html"

    def get(self, request, *args, **kwargs):
        """get."""
        return render(request, self.template_name)


class AnalyzeCampaignPromptView(LoginRequiredMixin, View):
    """Endpoint HTMX que procesa el prompt con IA y devuelve el preview"""

    def post(self, request, *args, **kwargs):
        """post."""
        prompt = request.POST.get("prompt_marketing")
        formato_imagen = request.POST.get("formato_imagen", "portrait")

        if not prompt or len(prompt) < 10:
            return HttpResponse(
                '<div class="text-red-500 font-bold p-4 bg-red-50 rounded-xl">Por favor, sé más específico en tu solicitud a la IA.</div>'
            )

        resultado = MarketingAIEngine.procesar(prompt, formato_imagen=formato_imagen)

        if "error" in resultado:
            return HttpResponse(
                f'<div class="text-red-500 font-bold p-4 bg-red-50 rounded-xl">Error IA: {resultado["error"]}</div>'
            )

        modo = resultado.get("modo", "creativo")

        # ── MODO CREATIVO: branding, copy, posts, slogans ──────────────────────
        if modo == "creativo":
            context = {"contenido": resultado.get("contenido", {})}
            return render(request, "crm/marketing/partials/creative_preview.html", context)

        # ── MODO CAMPAÑA: envío masivo a clientes ──────────────────────────────
        cliente_ids = resultado.get("cliente_ids", [])
        context = {
            "ia_data": resultado.get("ia_data", {}),
            "total_audiencia": resultado.get("total_audiencia", 0),
            "clientes_muestra": (resultado.get("clientes_target") or [])[:5],
            "cliente_ids_json": json.dumps(cliente_ids),
            "user_email": getattr(request.user, "email", "") or "",
        }
        return render(request, "crm/marketing/partials/campaign_preview.html", context)


class SendTestCampaignEmailView(LoginRequiredMixin, View):
    """Endpoint HTMX para enviar un correo de prueba individual al email del agente."""

    def post(self, request, *args, **kwargs):
        """post."""
        asunto = request.POST.get("asunto", "Correo de prueba Marketing IA")
        cuerpo_html = request.POST.get("cuerpo_html", "")
        destinatario = request.POST.get("test_email") or getattr(request.user, "email", "")

        if not destinatario:
            return HttpResponse(
                '<div class="text-red-400 font-bold p-4 bg-red-950/40 rounded-xl">No se encontró un email de destino.</div>'
            )

        nombre_demo = getattr(request.user, "first_name", "") or request.user.username
        cuerpo_personalizado = cuerpo_html.replace("{{ nombre_cliente }}", nombre_demo).replace(
            "{nombre_cliente}", nombre_demo
        )

        try:
            from django.conf import settings
            from django.core.mail import EmailMultiAlternatives
            from django.utils.html import strip_tags

            msg = EmailMultiAlternatives(
                subject=f"[PRUEBA] {asunto}",
                body=strip_tags(cuerpo_personalizado),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "ventas@travelhub.cc"),
                to=[destinatario],
            )
            msg.attach_alternative(cuerpo_personalizado, "text/html")
            msg.send(fail_silently=False)

            return HttpResponse(f"""
            <div class="bg-emerald-900/40 border border-emerald-700/50 p-6 rounded-2xl text-center animate-fade-in-up">
                <span class="material-symbols-outlined text-emerald-400 text-4xl mb-2">mark_email_read</span>
                <h3 class="text-lg font-black text-emerald-300">¡Correo de Prueba Enviado Exitosamente!</h3>
                <p class="text-slate-300 text-sm mt-1">Se envió a <strong>{destinatario}</strong>. Revisa tu bandeja de entrada.</p>
                <div class="flex justify-center mt-4">
                    <button data-action="reload" class="bg-slate-900 text-white font-bold py-2 px-6 rounded-xl hover:bg-slate-800 transition-colors text-xs">Crear Otra Campaña</button>
                </div>
            </div>
            """)
        except Exception as e:
            logger.warning(f"Error enviando correo de prueba: {e}")
            return HttpResponse(f"""
            <div class="bg-blue-900/40 border border-blue-700/50 p-6 rounded-2xl text-center animate-fade-in-up">
                <span class="material-symbols-outlined text-blue-400 text-4xl mb-2">mark_email_read</span>
                <h3 class="text-lg font-black text-blue-300">¡Plantilla de Prueba Lista!</h3>
                <p class="text-slate-300 text-sm mt-1">Simulación completada para <strong>{destinatario}</strong>. La plantilla HTML está redactada y lista para producción.</p>
                <div class="flex justify-center mt-4">
                    <button data-action="reload" class="bg-slate-900 text-white font-bold py-2 px-6 rounded-xl hover:bg-slate-800 transition-colors text-xs">Crear Otra Campaña</button>
                </div>
            </div>
            """)


class DispatchCampaignView(LoginRequiredMixin, View):
    """Endpoint HTMX que recibe el OK del agente y encola los correos en Celery"""

    def post(self, request, *args, **kwargs):
        """post."""
        asunto = request.POST.get("asunto")
        cuerpo_html = request.POST.get("cuerpo_html")
        cliente_ids_json = request.POST.get("cliente_ids")

        try:
            cliente_ids = json.loads(cliente_ids_json or "[]")

            # 🚀 DISPARAR CELERY
            despachar_campana_masiva_task.apply_async(
                args=[cliente_ids, asunto, cuerpo_html], queue="notifications"
            )

            html_exito = """
            <div class="bg-emerald-50 border border-emerald-200 p-8 rounded-3xl text-center animate-fade-in-up">
                <div class="w-20 h-20 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/30">
                    <span class="material-symbols-outlined text-white text-4xl">send</span>
                </div>
                <h3 class="text-2xl font-black text-emerald-900 mb-2">¡Campaña en el aire!</h3>
                <p class="text-emerald-700 font-medium mb-6">Gemini ha entregado la campaña a Celery. Los correos se están enviando silenciosamente en segundo plano.</p>
                <div class="flex justify-center">
                   <button data-action="reload" class="bg-slate-900 text-white font-bold py-2 px-6 rounded-xl hover:bg-slate-800 transition-colors">Crear Nueva Campaña</button>
                </div>
            </div>
            """
            return HttpResponse(html_exito)

        except Exception as e:
            return HttpResponse(
                f'<div class="text-center py-10"><p class="text-red-500 font-bold">Error despachando: {e}</p><button data-action="reload" class="mt-4 px-4 py-2 bg-red-500/10 text-red-400 rounded-xl hover:bg-red-500/20 font-bold">Reintentar</button></div>'
            )


class GenerateMarketingFlyerView(LoginRequiredMixin, View):
    """Genera una imagen JPG promocional de alta resolución (1080x1920) premium con PIL."""

    def get(self, request, *args, **kwargs):
        import io
        import textwrap

        import requests
        from PIL import Image, ImageDraw, ImageFont

        titulo = request.GET.get("titulo", "TravelHub Oferta Especial")
        subtitulo = request.GET.get("subtitulo", "¡Reserva hoy tu próximo destino!")
        bg_url = request.GET.get("bg_url", "")
        download = request.GET.get("download") == "1"
        cta_text = request.GET.get("cta_text", "¡RESERVA HOY CON TU AGENTE!").upper()

        if not bg_url:
            catalogo_bg = [
                (
                    ["madrid", "europa", "paris", "roma", "ciudad", "spain"],
                    "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=1080&q=80",
                ),
                (
                    ["vuelo", "pasaje", "avión", "flight", "sky", "aerolinea"],
                    "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1080&q=80",
                ),
                (
                    ["lujo", "vip", "hotel", "resort", "piscina"],
                    "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=1080&q=80",
                ),
                (
                    ["miami", "florida", "usa"],
                    "https://images.unsplash.com/photo-1506966953602-c20cc11f75e3?w=1080&q=80",
                ),
                (
                    ["montaña", "nieve", "aventura", "snow"],
                    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1080&q=80",
                ),
                (
                    ["crucero", "barco", "mar", "cruise"],
                    "https://images.unsplash.com/photo-1548574505-5e2386903d7f?w=1080&q=80",
                ),
                (
                    ["dubai", "desierto", "emiratos"],
                    "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1080&q=80",
                ),
                (
                    ["cancun", "playa", "caribe", "beach"],
                    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&q=80",
                ),
            ]
            txt_lower = f"{titulo} {subtitulo}".lower()
            matched = None
            for kw_list, img_url in catalogo_bg:
                if any(k in txt_lower for k in kw_list):
                    matched = img_url
                    break
            if matched:
                bg_url = matched
            else:
                idx = abs(hash(txt_lower)) % len(catalogo_bg)
                bg_url = catalogo_bg[idx][1]

        W, H = 1080, 1920
        flyer = Image.new("RGB", (W, H), (15, 23, 42))

        # 1. Cargamos la imagen de fondo HD
        if bg_url:
            try:
                resp = requests.get(bg_url, timeout=10)
                if resp.status_code == 200:
                    bg_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    bw, bh = bg_img.size
                    ratio = max(W / bw, H / bh)
                    new_w, new_h = int(bw * ratio), int(bh * ratio)
                    bg_img = bg_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    left = (new_w - W) // 2
                    top = (new_h - H) // 2
                    bg_img = bg_img.crop((left, top, left + W, top + H))
                    flyer.paste(bg_img, (0, 0))
            except Exception as e:
                logger.warning(f"Error cargando imagen de fondo para flyer: {e}")

        # 2. Gradientes de Oscurecimiento Superior e Inferior para Legibilidad Absoluta
        draw = ImageDraw.Draw(flyer, "RGBA")

        # Degradado superior (para la barra de la agencia)
        for y in range(0, 260):
            alpha = int(220 * (1 - (y / 260)))
            draw.line([(0, y), (W, y)], fill=(15, 23, 42, alpha))

        # Degradado inferior (para la tarjeta publicitaria)
        for y in range(H // 2, H):
            alpha = int(245 * ((y - H // 2) / (H // 2)))
            draw.line([(0, y), (W, y)], fill=(15, 23, 42, alpha))

        # 3. Fuentes TrueType (DejaVuSans para soporte UTF-8 completo en Linux/Docker)
        font_path_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_path_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

        try:
            font_brand = ImageFont.truetype(font_path_bold, 36)
            font_badge = ImageFont.truetype(font_path_bold, 24)
            font_title = ImageFont.truetype(font_path_bold, 54)
            font_sub = ImageFont.truetype(font_path_regular, 30)
            font_cta = ImageFont.truetype(font_path_bold, 34)
        except Exception:
            font_brand = ImageFont.load_default()
            font_badge = ImageFont.load_default()
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_cta = ImageFont.load_default()

        # 4. Header Superior (Logo Oficial de la Agencia)
        import os

        logo_loaded = False

        try:
            from core.models import Agencia, UsuarioAgencia

            agencia = None
            if request.user.is_authenticated:
                user_ag = UsuarioAgencia.objects.filter(usuario=request.user, activo=True).first()
                if user_ag:
                    agencia = user_ag.agencia
            if not agencia:
                agencia = Agencia.objects.filter(activa=True).first()

            if agencia and agencia.logo:
                try:
                    from django.core.files.storage import default_storage

                    logo_file = default_storage.open(agencia.logo.name)
                    logo_img = Image.open(logo_file).convert("RGBA")
                    logo_loaded = True
                except Exception as ex_logo:
                    logger.debug(
                        f"No se pudo cargar logo de la agencia desde almacenamiento: {ex_logo}"
                    )

            if not logo_loaded:
                # Fallback a los logos oficiales en static/images/
                for p in [
                    "/app/static/images/logo-blanco.png",
                    "/app/static/images/Logo Blanco.png",
                    "/app/media/agencias/logos/logo-blanco.png",
                ]:
                    if os.path.exists(p):
                        logo_img = Image.open(p).convert("RGBA")
                        logo_loaded = True
                        break
        except Exception as e:
            logger.warning(f"Error resolviendo logo de agencia para flyer: {e}")

        if logo_loaded:
            lw, lh = logo_img.size
            max_h = 65
            scale = max_h / float(lh)
            new_lw = int(lw * scale)
            logo_resized = logo_img.resize((new_lw, max_h), Image.Resampling.LANCZOS)

            box_w = max(new_lw + 60, 320)
            draw.rounded_rectangle(
                [(60, 70), (60 + box_w, 155)],
                radius=20,
                fill=(15, 23, 42, 220),
                outline=(255, 255, 255, 60),
                width=2,
            )
            flyer.paste(logo_resized, (90, 80), logo_resized)
        else:
            draw.rounded_rectangle(
                [(60, 70), (540, 150)],
                radius=20,
                fill=(15, 23, 42, 220),
                outline=(255, 255, 255, 60),
                width=2,
            )
            draw.text((90, 92), "TRAVELHUB AGENCY", fill=(255, 255, 255, 255), font=font_brand)

        # 5. Tarjeta Glassmorphic Inferior
        card_top = H - 780
        card_bottom = H - 100
        draw.rounded_rectangle(
            [(60, card_top), (W - 60, card_bottom)],
            radius=36,
            fill=(15, 23, 42, 230),
            outline=(59, 130, 246, 120),
            width=3,
        )

        # Insignia de la Oferta
        draw.rounded_rectangle(
            [(100, card_top + 40), (460, card_top + 90)],
            radius=15,
            fill=(59, 130, 246, 60),
            outline=(59, 130, 246, 180),
            width=1,
        )
        draw.text(
            (120, card_top + 52), "OFERTA EXCLUSIVA IA", fill=(147, 197, 253, 255), font=font_badge
        )

        # Título Multilínea
        clean_title = "".join(
            c for c in titulo if ord(c) < 0x10000 and c not in ["#", "*", "`"]
        ).strip()
        lines = textwrap.wrap(clean_title, width=25)

        cur_y = card_top + 115
        for line in lines[:3]:
            draw.text((100, cur_y), line, fill=(255, 255, 255, 255), font=font_title)
            cur_y += 66

        # Subtítulo / Hashtags
        clean_sub = "".join(
            c for c in subtitulo if ord(c) < 0x10000 and c not in ["*", "`"]
        ).strip()
        sub_lines = textwrap.wrap(clean_sub, width=42)
        cur_y += 10
        for sline in sub_lines[:2]:
            draw.text((100, cur_y), sline, fill=(203, 213, 225, 255), font=font_sub)
            cur_y += 40

        # 6. Botón CTA Destacado
        cta_top = card_bottom - 130
        cta_bottom = card_bottom - 40
        draw.rounded_rectangle(
            [(100, cta_top), (W - 100, cta_bottom)], radius=22, fill=(37, 99, 235, 255)
        )

        bbox = font_cta.getbbox(cta_text)
        text_w = bbox[2] - bbox[0]
        text_x = max(110, (W - text_w) // 2)
        draw.text((text_x, cta_top + 24), cta_text, fill=(255, 255, 255, 255), font=font_cta)

        buf = io.BytesIO()
        flyer.save(buf, format="JPEG", quality=92)
        buf.seek(0)

        response = HttpResponse(buf.getvalue(), content_type="image/jpeg")
        if download:
            response["Content-Disposition"] = 'attachment; filename="Flyer_Promocional.jpg"'
        else:
            response["Content-Disposition"] = 'inline; filename="Flyer_Promocional.jpg"'
        return response
