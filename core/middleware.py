"""
Shim para core.middleware package.
Re-exporta todo desde el paquete core.middleware.tenant para garantizar una única definición
de ContextVar (agency_var, user_var, system_context_var) en todo el sistema.
"""
from core.middleware.domain import MultiTenantDomainMiddleware
from core.middleware.rls import get_rls_bypass_flag, is_admin_path, rls_session_context
from core.middleware.security_headers import SecurityHeadersMiddleware, csp_report_view
from core.middleware.tenant import (
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
    "ThreadLocalContextMiddleware",
    "MultiTenantDomainMiddleware",
    "SecurityHeadersMiddleware",
    "csp_report_view",
    "get_current_request_meta",
    "get_current_user",
    "get_current_agency",
    "is_system_context",
    "is_impersonating",
    "get_impersonator",
    "agency_context",
    "system_context",
    "rls_session_context",
    "get_rls_bypass_flag",
    "is_admin_path",
    "meta_var",
    "user_var",
    "agency_var",
    "system_context_var",
    "is_impersonating_var",
    "impersonator_var",
]
