"""
Modelo de configuración de proveedores SSO (SAML / OIDC).

Cada agencia puede configurar sus propios proveedores de identidad.
"""

from django.db import models


class SSOProvider(models.Model):
    """Configuración de un proveedor SSO para una agencia."""

    class ProviderType(models.TextChoices):
        AZURE_AD = "azure_ad", "Azure AD (OIDC)"
        OKTA_OIDC = "okta_oidc", "Okta (OIDC)"
        OKTA_SAML = "okta_saml", "Okta (SAML)"
        GOOGLE = "google_oidc", "Google Workspace (OIDC)"
        GENERIC_OIDC = "generic_oidc", "Generic OIDC"
        GENERIC_SAML = "generic_saml", "Generic SAML 2.0"

    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.CASCADE,
        related_name="sso_providers",
    )
    provider_type = models.CharField(
        max_length=20,
        choices=ProviderType.choices,
        help_text="Tipo de proveedor de identidad",
    )
    name = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo (ej: 'Okta TravelHub')",
    )
    client_id = models.CharField(
        max_length=512,
        blank=True,
        help_text="Client ID (OIDC) / SAML Entity ID",
    )
    client_secret = models.CharField(
        max_length=512,
        blank=True,
        help_text="Client Secret (OIDC solamente)",
    )
    # OIDC endpoints
    oidc_config_url = models.URLField(
        max_length=512,
        blank=True,
        help_text="OIDC Discovery URL (ej: https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration)",
    )
    # SAML fields
    saml_entity_id = models.CharField(
        max_length=512,
        blank=True,
        help_text="SAML Entity ID / Issuer",
    )
    saml_acs_url = models.URLField(
        max_length=512,
        blank=True,
        help_text="SAML Assertion Consumer Service URL",
    )
    saml_x509_cert = models.TextField(
        blank=True,
        help_text="Certificado X.509 público del IdP (SAML)",
    )
    # Mapeo de atributos
    email_attribute = models.CharField(
        max_length=64,
        default="email",
        help_text="Atributo que contiene el email del usuario",
    )
    name_attribute = models.CharField(
        max_length=64,
        default="name",
        help_text="Atributo que contiene el nombre completo",
    )
    # Estado
    is_active = models.BooleanField(default=True)
    auto_provision = models.BooleanField(
        default=True,
        help_text="Crear usuario automáticamente si no existe",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor SSO"
        verbose_name_plural = "Proveedores SSO"
        unique_together = [("agencia", "provider_type", "client_id")]
        indexes = [
            models.Index(fields=["agencia", "is_active"]),
        ]

    def __str__(self):
        return f"[{self.agencia}] {self.name} ({self.provider_type})"
