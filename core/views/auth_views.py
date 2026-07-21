import json
import logging

from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.common.services.magic_link_service import (
    create_magic_link,
    send_magic_link_email,
    verify_magic_link,
)
from core.models.magic_link import MagicLinkToken

logger = logging.getLogger(__name__)
User = get_user_model()


@method_decorator(csrf_exempt, name="dispatch")
class MagicLinkRequestView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            data = request.POST.dict()

        email = (data.get("email") or "").strip().lower()
        redirect_url = data.get("redirect_url", "/")
        is_onboarding = data.get("is_onboarding", False)
        onboarding_data = data.get("onboarding_data", {})

        if not email:
            return JsonResponse({"error": "Email es obligatorio"}, status=400)

        # Rate limiting por IP: máximo 10 solicitudes por IP cada 15 minutos
        ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("HTTP_X_REAL_IP")
        if not ip:
            xff = request.META.get("HTTP_X_FORWARDED_FOR")
            if xff:
                ip = [p.strip() for p in xff.split(",")][-1]
            else:
                ip = request.META.get("REMOTE_ADDR")

        if ip:
            ip_rate_key = f"magic_link_rate_ip_{ip}"
            try:
                ip_request_count = cache.incr(ip_rate_key)
            except ValueError:
                cache.set(ip_rate_key, 1, timeout=900)
                ip_request_count = 1
            if ip_request_count > 10:
                logger.warning(f"Rate limit por IP excedido para magic link: {ip}")
                return JsonResponse(
                    {"error": "Demasiadas solicitudes desde esta dirección IP. Espera 15 minutos."},
                    status=429,
                )

        # Rate limiting por email: máximo 3 solicitudes por email cada 15 minutos
        rate_key = f"magic_link_rate_{email}"
        try:
            request_count = cache.incr(rate_key)
        except ValueError:
            cache.set(rate_key, 1, timeout=900)
            request_count = 1
        if request_count > 3:
            logger.warning(f"Rate limit excedido para magic link: {email}")
            return JsonResponse(
                {"error": "Demasiadas solicitudes. Espera 15 minutos antes de intentar de nuevo."},
                status=429,
            )

        if isinstance(onboarding_data, str):
            try:
                onboarding_data = json.loads(onboarding_data)
            except json.JSONDecodeError:
                onboarding_data = {}

        MagicLinkToken.objects.filter(email=email, used_at__isnull=True).update(
            used_at=timezone.now()
        )

        token_obj = create_magic_link(
            email=email,
            redirect_url=redirect_url,
            is_onboarding=is_onboarding,
            onboarding_data=onboarding_data,
        )

        try:
            send_magic_link_email(token_obj, request=request)
        except Exception as e:
            logger.error("Failed to send magic link email to %s: %s", email, e)
            return JsonResponse({"error": "Error enviando el email. Intenta de nuevo."}, status=500)

        return JsonResponse(
            {
                "message": "Enlace magic enviado a tu email",
                "email": email,
                "expires_in_minutes": 15,
            }
        )


class MagicLinkVerifyView(View):
    def get(self, request, token):
        token_obj, status = verify_magic_link(token)

        if status == "invalid":
            return render(
                request,
                "auth/magic_link_error.html",
                {
                    "error": "Enlace inválido",
                    "error_detail": "Este enlace no existe o fue reemplazado por uno más reciente.",
                },
                status=400,
            )

        if status == "expired":
            return render(
                request,
                "auth/magic_link_error.html",
                {
                    "error": "Enlace expirado",
                    "error_detail": "Este enlace ya expiró. Solicita uno nuevo.",
                    "can_retry": True,
                    "email": token_obj.email if token_obj else "",
                },
                status=400,
            )

        if status == "already_used":
            return render(
                request,
                "auth/magic_link_error.html",
                {
                    "error": "Enlace ya utilizado",
                    "error_detail": "Este enlace ya fue utilizado. Solicita uno nuevo.",
                    "can_retry": True,
                },
                status=400,
            )

        if not token_obj:
            return render(
                request,
                "auth/magic_link_error.html",
                {
                    "error": "Error desconocido",
                },
                status=400,
            )

        try:
            user = User.objects.get(email=token_obj.email)
        except User.DoesNotExist:
            username = token_obj.email.split("@")[0]
            base_username = username
            count = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{count}"
                count += 1
            user = User.objects.create_user(username=username, email=token_obj.email)

        if not user.is_active:
            logger.warning(
                f"Intento de login con magic link para usuario desactivado: {user.email}"
            )
            return render(
                request,
                "auth/magic_link_error.html",
                {
                    "error": "Enlace invalido",
                    "error_detail": "Este enlace no es valido o expiro. Solicita uno nuevo.",
                },
                status=400,
            )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        if token_obj.is_onboarding and token_obj.onboarding_data:
            request.session["onboarding_data"] = token_obj.onboarding_data
            request.session["onboarding_email"] = token_obj.email
            return redirect("/onboarding/agency/")

        redirect_url = token_obj.redirect_url or "/"
        return redirect(redirect_url)


class TokenLogoutView(View):
    """
    Vista para logout de tokens JWT.
    Devuelve éxito para que el cliente limpie su almacenamiento local.
    """

    def post(self, request, *args, **kwargs):
        return JsonResponse({"message": "Successfully logged out"}, status=200)
