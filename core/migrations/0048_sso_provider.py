from django.db import migrations, models


class Migration(migrations.Migration):
    """Crea modelo SSOProvider para configuración de SSO/SAML/OIDC."""

    dependencies = [
        ("core", "0047_numbering_sequence"),
        ("core", "0046_enable_pg_trgm_extension"),
    ]

    operations = [
        migrations.CreateModel(
            name="SSOProvider",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "provider_type",
                    models.CharField(
                        choices=[
                            ("azure_ad", "Azure AD (OIDC)"),
                            ("okta_oidc", "Okta (OIDC)"),
                            ("okta_saml", "Okta (SAML)"),
                            ("google_oidc", "Google Workspace (OIDC)"),
                            ("generic_oidc", "Generic OIDC"),
                            ("generic_saml", "Generic SAML 2.0"),
                        ],
                        help_text="Tipo de proveedor de identidad",
                        max_length=20,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Nombre descriptivo (ej: 'Okta TravelHub')", max_length=100
                    ),
                ),
                (
                    "client_id",
                    models.CharField(
                        blank=True, help_text="Client ID (OIDC) / SAML Entity ID", max_length=512
                    ),
                ),
                (
                    "client_secret",
                    models.CharField(
                        blank=True, help_text="Client Secret (OIDC solamente)", max_length=512
                    ),
                ),
                (
                    "oidc_config_url",
                    models.URLField(blank=True, help_text="OIDC Discovery URL", max_length=512),
                ),
                (
                    "saml_entity_id",
                    models.CharField(
                        blank=True, help_text="SAML Entity ID / Issuer", max_length=512
                    ),
                ),
                (
                    "saml_acs_url",
                    models.URLField(blank=True, help_text="SAML ACS URL", max_length=512),
                ),
                (
                    "saml_x509_cert",
                    models.TextField(blank=True, help_text="Certificado X.509 del IdP"),
                ),
                (
                    "email_attribute",
                    models.CharField(
                        default="email", help_text="Atributo del email", max_length=64
                    ),
                ),
                (
                    "name_attribute",
                    models.CharField(
                        default="name", help_text="Atributo del nombre", max_length=64
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "auto_provision",
                    models.BooleanField(default=True, help_text="Crear usuario si no existe"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agencia",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="sso_providers",
                        to="core.agencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Proveedor SSO",
                "verbose_name_plural": "Proveedores SSO",
                "db_table": "core_sso_provider",
                "indexes": [
                    models.Index(
                        fields=["agencia", "is_active"], name="core_sso_provider_agencia_active_idx"
                    )
                ],
            },
        ),
        migrations.AlterUniqueTogether(
            name="ssoprovider",
            unique_together={("agencia", "provider_type", "client_id")},
        ),
    ]
