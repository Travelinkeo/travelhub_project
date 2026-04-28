# core/security.py
"""
🔐 CAPA DE SEGURIDAD MULTI-TENANT — TravelHub SaaS
===================================================
Este módulo centraliza la lógica de aislamiento de datos entre agencias.

REGLA DE ORO:
  Ninguna vista puede acceder a un objeto sin pasar por estas funciones.
  Un usuario de la Agencia A NUNCA debe poder ver datos de la Agencia B,
  aunque conozca el ID del objeto (ataque IDOR - Insecure Direct Object Reference).

USO EN VISTAS FUNCIONALES:
    from core.security import get_agencia_or_403, get_object_tenant_or_404

    def mi_vista(request, pk):
        agencia = get_agencia_or_403(request)
        venta = get_object_tenant_or_404(Venta, agencia, pk=pk)

USO EN CLASS-BASED VIEWS:
    Usar SaaSMixin (ya implementado en core/mixins.py) que aplica el filtro
    en get_queryset() automáticamente.
"""
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import Http404
from functools import wraps


def agency_role_required(allowed_roles):
    """
    Decorador para vistas funcionales que restringe el acceso según el rol 
    del usuario en la agencia.
    
    Uso:
        @agency_role_required(['admin', 'gerente'])
        def mi_vista(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Autenticación requerida.")
                
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            if hasattr(request.user, 'agencias'):
                ua = request.user.agencias.filter(activo=True).select_related('agencia').first()
                if ua and ua.rol in allowed_roles:
                    return view_func(request, *args, **kwargs)
                    
            raise PermissionDenied("No tienes permisos suficientes para realizar esta acción (se requiere rol: " + ", ".join(allowed_roles) + ").")
        return _wrapped_view
    return decorator


def get_agencia_from_request(request):
    """
    Extrae la agencia activa del usuario autenticado.
    Devuelve None si el usuario es superuser (acceso global).
    Lanza PermissionDenied si no tiene agencia asignada.
    """
    user = request.user

    if not user.is_authenticated:
        raise PermissionDenied("Autenticación requerida.")

    # Superusers tienen acceso global — no se les aplica el candado de agencia.
    if user.is_superuser:
        return None

    if hasattr(user, 'agencias'):
        ua = user.agencias.filter(activo=True).select_related('agencia').first()
        if ua and ua.agencia:
            return ua.agencia

    raise PermissionDenied("Tu usuario no tiene una agencia activa asignada.")


def get_agencia_or_403(request):
    """
    Versión explícita que lanza 403 si no hay agencia.
    Alias semántico para get_agencia_from_request().
    """
    return get_agencia_from_request(request)


def get_object_tenant_or_404(model, agencia, **kwargs):
    """
    Versión segura de get_object_or_404 que aplica el filtro de agencia.

    Si agencia es None (superuser), busca sin filtro de agencia.
    Si agencia tiene valor, agrega agencia=agencia al filtro.

    Args:
        model:   Clase del modelo Django (ej. Venta, Factura, BoletoImportado).
        agencia: Instancia de Agencia del usuario, o None para superusers.
        **kwargs: Filtros adicionales (ej. pk=pk, numero_boleto='ABC').

    Returns:
        Instancia del modelo si existe y pertenece a la agencia.

    Raises:
        Http404: Si no existe o no pertenece a la agencia del usuario.
    """
    if agencia is not None:
        kwargs['agencia'] = agencia

    return get_object_or_404(model, **kwargs)


def filter_queryset_by_tenant(queryset, agencia):
    """
    Filtra un queryset existente por la agencia del usuario.
    Si agencia es None (superuser), devuelve el queryset sin modificar.

    Args:
        queryset: QuerySet de Django.
        agencia:  Instancia de Agencia del usuario, o None para superusers.

    Returns:
        QuerySet filtrado (o sin cambios si superuser).
    """
    if agencia is not None:
        return queryset.filter(agencia=agencia)
    return queryset
