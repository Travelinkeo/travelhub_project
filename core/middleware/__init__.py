"""
Core Middleware Package

Este paquete contiene los middlewares divididos por responsabilidad:

- tenant.py: ThreadLocalContextMiddleware + context managers (system_context, agency_context)
- security_headers.py: SecurityHeadersMiddleware + csp_report_view
- domain.py: MultiTenantDomainMiddleware (resolución de tenants por dominio/subdominio)
- rls.py: rls_session_context + helpers (RLS/Row Level Security)

Orden recomendado en settings.MIDDLEWARE:
1. core.middleware.tenant.ThreadLocalContextMiddleware  (primero - establece contexto)
2. core.middleware.domain.MultiTenantDomainMiddleware   (resuelve tenant por dominio)
3. core.middleware.security_headers.SecurityHeadersMiddleware  (CSP, HSTS, etc.)
"""

from .domain import (
    MultiTenantDomainMiddleware,
)
from .rls import (
    get_rls_bypass_flag,
    is_admin_path,
    rls_session_context,
)
from .security_headers import (
    SecurityHeadersMiddleware,
    csp_report_view,
)
from .tenant import (
    ThreadLocalContextMiddleware,
    agency_context,
    agency_var,
    get_current_agency,
    get_current_request_meta,
    get_current_user,
    get_impersonator,
    impersonator_var,
    is_impersonating,
    is_impersonating_var,
    is_system_context,
    meta_var,
    system_context,
    system_context_var,
    user_var,
)

__all__ = [
    # tenant.py
    "ThreadLocalContextMiddleware",
    "get_current_request_meta",
    "get_current_user",
    "get_current_agency",
    "is_system_context",
    "is_impersonating",
    "get_impersonator",
    "agency_context",
    "system_context",
    "meta_var",
    "user_var",
    "agency_var",
    "system_context_var",
    "is_impersonating_var",
    "impersonator_var",
    # security_headers.py
    "SecurityHeadersMiddleware",
    "csp_report_view",
    # domain.py
    "MultiTenantDomainMiddleware",
    # rls.py
    "rls_session_context",
    "get_rls_bypass_flag",
    "is_admin_path",
]
