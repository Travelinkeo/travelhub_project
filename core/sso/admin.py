"""
Admin de SSO/SAML/OIDC.
"""

from django.contrib import admin

from core.admin_saas import SaaSAdminMixin
from core.sso.models import SSOProvider


@admin.register(SSOProvider)
class SSOProviderAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ("name", "agencia", "provider_type", "is_active", "auto_provision")
    list_filter = ("provider_type", "is_active", "auto_provision")
    search_fields = ("name", "agencia__nombre", "client_id")
    fieldsets = (
        (
            "General",
            {
                "fields": ("agencia", "provider_type", "name", "is_active", "auto_provision"),
            },
        ),
        (
            "OIDC",
            {
                "classes": ("collapse",),
                "fields": ("client_id", "client_secret", "oidc_config_url"),
            },
        ),
        (
            "SAML",
            {
                "classes": ("collapse",),
                "fields": ("saml_entity_id", "saml_acs_url", "saml_x509_cert"),
            },
        ),
        (
            "Atributos",
            {
                "fields": ("email_attribute", "name_attribute"),
            },
        ),
    )
