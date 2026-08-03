"""
Vistas de autenticación SSO (SAML / OIDC).

Maneja el flujo de login y callback para proveedores configurados.
"""

import json
import logging
import secrets
import time
import urllib.parse
from base64 import b64encode

import jwt
import requests
from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

SESSION_KEY_SSO_STATE = "sso_oauth_state"


def _get_provider(provider_id: str):
    """Obtiene un proveedor SSO activo por ID."""
    from core.sso.models import SSOProvider

    return get_object_or_404(SSOProvider, id=provider_id, is_active=True)


def _discover_oidc(config_url: str) -> dict:
    """Descubre los endpoints OIDC desde el well-known URL."""
    try:
        resp = requests.get(config_url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("OIDC discovery failed for %s: %s", config_url, e)
        return {}


def _verify_jwt(id_token: str, provider) -> bool:
    """
    Verifica la firma del id_token JWT contra JWKS del proveedor.

    SEGURIDAD (fail-closed): Si no se puede obtener el JWKS del proveedor,
    el token es RECHAZADO. No existe un fallback que acepte tokens sin firma,
    ya que eso permitiría a un atacante fabricar tokens válidos provocando
    un timeout en el servidor JWKS.
    """
    try:
        unverified_header = jwt.get_unverified_header(id_token)
        config_url = provider.oidc_config_url
        if not config_url:
            logger.error(
                "SSO RECHAZADO: proveedor %s no tiene oidc_config_url configurado.", provider
            )
            return False

        config = _discover_oidc(config_url)
        jwks_uri = config.get("jwks_uri")
        if not jwks_uri:
            logger.error(
                "SSO RECHAZADO: no se encontró jwks_uri en la configuración OIDC de %s.", provider
            )
            return False

        resp = requests.get(jwks_uri, timeout=10)
        resp.raise_for_status()
        jwks = resp.json()

        kid = unverified_header.get("kid")
        jwk_data = [k for k in jwks.get("keys", []) if k.get("kid") == kid]
        if not jwk_data:
            logger.error("SSO RECHAZADO: kid='%s' no encontrado en JWKS de %s.", kid, provider)
            return False

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk_data[0]))
        jwt.decode(id_token, public_key, algorithms=["RS256"], options={"verify_exp": True})
        return True

    except Exception as e:
        logger.warning("SSO RECHAZADO: JWT verification failed para %s: %s", provider, e)
        return False


def _create_or_get_user(email: str, name: str, provider):
    """Crea o recupera un usuario del SSO."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    email = email.lower().strip()

    user = User.objects.filter(email=email).first()
    if user:
        return user

    if not provider.auto_provision:
        logger.warning("SSO auto-provision disabled for %s", email)
        return None

    username = email.split("@")[0]
    from django.db import IntegrityError

    base_username = username
    suffix = 1

    while True:
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                is_active=True,
            )
            break
        except IntegrityError:
            username = f"{base_username}{suffix}"
            suffix += 1
    if name:
        parts = name.strip().split(" ", 1)
        user.first_name = parts[0]
        if len(parts) > 1:
            user.last_name = parts[1]
        user.save()

    logger.info("SSO auto-provisioned user: %s", email)
    return user


# ─── OIDC FLOW ─────────────────────────────────────────────


@require_GET
def sso_login(request, provider_id):
    """Inicia el flujo OIDC: redirige al proveedor."""
    provider = _get_provider(provider_id)

    if provider.provider_type in ("azure_ad", "okta_oidc", "google_oidc", "generic_oidc"):
        return _oidc_login(request, provider)
    elif provider.provider_type in ("okta_saml", "generic_saml"):
        return _saml_login(request, provider)
    return HttpResponseBadRequest("Unsupported provider type")


def _oidc_login(request, provider):
    """Redirige al usuario al endpoint de autorización OIDC."""
    discovery = _discover_oidc(provider.oidc_config_url)
    auth_url = discovery.get("authorization_endpoint")
    if not auth_url:
        logger.error("No authorization_endpoint found for %s", provider)
        return HttpResponseBadRequest("OIDC misconfigured: no authorization endpoint")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(16)
    request.session[SESSION_KEY_SSO_STATE] = {"state": state, "provider_id": provider.id}

    redirect_uri = request.build_absolute_uri(reverse("sso_callback", args=[provider.id]))

    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
    }

    return HttpResponseRedirect(f"{auth_url}?{urllib.parse.urlencode(params)}")


@require_GET
def sso_callback(request, provider_id):
    """Maneja el callback OIDC después de la autenticación."""
    provider = _get_provider(provider_id)

    if provider.provider_type in ("azure_ad", "okta_oidc", "google_oidc", "generic_oidc"):
        return _oidc_callback(request, provider)
    elif provider.provider_type in ("okta_saml", "generic_saml"):
        return _saml_callback(request, provider)
    return HttpResponseBadRequest("Unsupported provider type")


def _oidc_callback(request, provider):
    """Intercambia el código de autorización por tokens y autentica."""
    # Manejo de error de IdP
    error = request.GET.get("error")
    if error:
        logger.warning(f"OIDC error response: {error}")
        return render(request, "sso/error.html", {"error": f"Identity Provider Error: {error}"})

    # Validar state
    saved = request.session.pop(SESSION_KEY_SSO_STATE, {})
    if saved.get("state") != request.GET.get("state"):
        return HttpResponseBadRequest("Invalid state (CSRF check failed)")
    if saved.get("provider_id") != provider.id:
        return HttpResponseBadRequest("Provider mismatch")

    code = request.GET.get("code")
    if not code:
        return HttpResponseBadRequest("No authorization code")

    discovery = _discover_oidc(provider.oidc_config_url)
    token_url = discovery.get("token_endpoint")
    if not token_url:
        return HttpResponseBadRequest("OIDC misconfigured: no token endpoint")

    redirect_uri = request.build_absolute_uri(reverse("sso_callback", args=[provider.id]))

    # Intercambio de código por tokens
    try:
        resp = requests.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as e:
        logger.error("OIDC token exchange failed: %s", e)
        return HttpResponseBadRequest("Token exchange failed")

    # Decodificar ID Token (JWT)
    id_token = token_data.get("id_token", "")
    if not id_token:
        return HttpResponseBadRequest("No id_token received")

    # Verificar firma JWT contra JWKS del proveedor
    if not _verify_jwt(id_token, provider):
        return HttpResponseBadRequest("Invalid id_token signature")

    try:
        payload_b64 = id_token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(
            __import__("base64", fromlist=["urlsafe_b64decode"])
            .urlsafe_b64decode(payload_b64)
            .decode("utf-8")
        )
    except Exception as e:
        logger.error("Failed to decode id_token: %s", e)
        return HttpResponseBadRequest("Invalid id_token")

    email = (
        payload.get("email", "") or payload.get("upn", "") or payload.get("preferred_username", "")
    )
    name = payload.get("name", "") or payload.get("given_name", "") or email

    if not email:
        return HttpResponseBadRequest("No email in token")

    email_verified = payload.get("email_verified")
    if email_verified is not None and not email_verified:
        return HttpResponseBadRequest("Email not verified by IdP")

    user = _create_or_get_user(email, name, provider)
    if not user:
        return render(request, "sso/error.html", {"error": "User not authorized", "email": email})

    # Autenticar usuario
    user.backend = "django.contrib.auth.backends.ModelBackend"
    auth.login(request, user)

    next_url = request.GET.get("next") or getattr(settings, "LOGIN_REDIRECT_URL", "/")
    return HttpResponseRedirect(next_url)


# ─── SAML FLOW (minimal) ───────────────────────────────────


def _saml_login(request, provider):
    """Inicia flujo SAML: redirige al IdP."""

    # Generar AuthnRequest
    request_id = f"_{secrets.token_hex(16)}"
    acs_url = request.build_absolute_uri(reverse("sso_callback", args=[provider.id]))

    authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}" Version="2.0"
    IssueInstant="{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}"
    Destination="{provider.saml_acs_url}"
    AssertionConsumerServiceURL="{acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{provider.saml_entity_id or provider.client_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""

    # Base64 encode para redirección
    encoded = b64encode(authn_request.encode("utf-8")).decode("utf-8")
    relay_state = secrets.token_urlsafe(16)

    request.session[SESSION_KEY_SSO_STATE] = {
        "relay_state": relay_state,
        "provider_id": provider.id,
    }

    sso_url = provider.saml_acs_url
    return render(
        request,
        "sso/saml_post.html",
        {
            "action": sso_url,
            "saml_request": encoded,
            "relay_state": relay_state,
        },
    )


def _saml_callback(request, provider):
    """Procesa la respuesta SAML del IdP."""
    from base64 import b64decode

    saml_response = request.POST.get("SAMLResponse", "")
    if not saml_response:
        return HttpResponseBadRequest("No SAMLResponse")

    try:
        decoded = b64decode(saml_response).decode("utf-8")
    except Exception as e:
        logger.error("SAML decode failed: %s", e)
        return HttpResponseBadRequest("Invalid SAMLResponse encoding")

    # Parsear XML
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(decoded)  # noqa: S314 - SAML XML from IdP
        # Extraer atributos
        email = ""
        name = ""

        # Buscar en Assertion > AttributeStatement
        for attr_stmt in root.iter("{urn:oasis:names:tc:SAML:2.0:assertion}AttributeStatement"):
            for attr in attr_stmt:
                attr_name = attr.get("Name", "")
                attr_values = [v.text or "" for v in attr if v.text]
                if attr_name == provider.email_attribute:
                    email = attr_values[0] if attr_values else ""
                elif attr_name == provider.name_attribute:
                    name = attr_values[0] if attr_values else ""

        # También probar NameID
        if not email:
            for name_id in root.iter("{urn:oasis:names:tc:SAML:2.0:assertion}NameID"):
                if name_id.text:
                    email = name_id.text
                    break
    except ET.ParseError as e:
        logger.error("SAML XML parse error: %s", e)
        return HttpResponseBadRequest("Invalid SAML XML")

    if not email:
        return HttpResponseBadRequest("No user identifier in SAML response")

    user = _create_or_get_user(email, name, provider)
    if not user:
        return render(request, "sso/error.html", {"error": "User not authorized", "email": email})

    user.backend = "django.contrib.auth.backends.ModelBackend"
    auth.login(request, user)

    next_url = request.GET.get("next") or getattr(settings, "LOGIN_REDIRECT_URL", "/")
    return HttpResponseRedirect(next_url)
