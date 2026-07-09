"""
SSO / SAML / OIDC Integration Package.

Soporta múltiples proveedores de identidad empresarial:
- Azure AD (OIDC)
- Okta (OIDC + SAML)
- Google Workspace (OIDC)
- Generic SAML 2.0

Uso:
  1. Configurar proveedor en /admin/sso/
  2. Usuarios hacen login vía /sso/login/<provider>/
  3. Callback /sso/callback/<provider>/
"""

from .models import SSOProvider  # noqa: F401
from .views import sso_callback, sso_login  # noqa: F401
