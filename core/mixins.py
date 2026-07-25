from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

from core.security import get_user_active_agency


class SaaSMixin:
    """
    Mixin para filtrar querysets por la agencia del usuario actual
    y aplicar reglas estrictas de RBAC por rol en la agencia.
    """

    def get_queryset(self):
        """Método que obtiene queryset. Args: según implementación. Returns: datos solicitados."""
        if hasattr(super(), "get_queryset"):
            qs = super().get_queryset()
        else:
            if hasattr(self, "model") and self.model:
                qs = self.model.objects.all()
            elif hasattr(self, "queryset") and self.queryset is not None:
                qs = self.queryset.all()
            else:
                from django.core.exceptions import ImproperlyConfigured

                raise ImproperlyConfigured(
                    f"{self.__class__.__name__} is missing a QuerySet. Define model, queryset, or override get_queryset()."
                )
        user = self.request.user

        if not user.is_authenticated:
            return qs.none()

        if user.is_superuser:
            return qs

        # Obtener la agencia activa del usuario
        agencia = get_user_active_agency(user)
        if agencia:
            # Solo filtrar por agencia si el modelo tiene ese campo
            if hasattr(qs.model, "agencia"):
                qs = qs.filter(agencia=agencia)

            # RBAC por rol
            usuario_agencia = user.agencias.filter(agencia=agencia, activo=True).first()
            if usuario_agencia:
                rol = usuario_agencia.rol
                # vendedor: sólo ve lo creado por sí mismo en modelos operacionales
                if rol == "vendedor":
                    operational_models = [
                        "Venta",
                        "ItemVenta",
                        "PagoVenta",
                        "FeeVenta",
                        "GastoOperativo",
                        "SolicitudAnulacion",
                    ]
                    if qs.model.__name__ in operational_models:
                        if hasattr(qs.model, "creado_por"):
                            qs = qs.filter(creado_por=user)
                        elif hasattr(qs.model, "venta"):
                            qs = qs.filter(venta__creado_por=user)
                        elif hasattr(qs.model, "venta_asociada"):
                            qs = qs.filter(venta_asociada__creado_por=user)
            return qs

        return qs.none()

    def get_object(self, queryset=None):
        """Método que obtiene object. Args: según implementación. Returns: datos solicitados."""
        if hasattr(super(), "get_object"):
            obj = super().get_object(queryset)
        else:
            if queryset is None:
                queryset = self.get_queryset()
            pk = self.kwargs.get("pk")
            from django.shortcuts import get_object_or_404

            obj = get_object_or_404(queryset, pk=pk)

        user = self.request.user
        if not user.is_authenticated or user.is_superuser:
            return obj

        agencia = get_user_active_agency(user)
        if agencia:
            usuario_agencia = user.agencias.filter(agencia=agencia, activo=True).first()
            if usuario_agencia and usuario_agencia.rol == "vendedor":
                model_name = obj.__class__.__name__
                operational_models = [
                    "Venta",
                    "ItemVenta",
                    "PagoVenta",
                    "FeeVenta",
                    "GastoOperativo",
                    "SolicitudAnulacion",
                ]
                if model_name in operational_models:
                    if hasattr(obj, "creado_por") and obj.creado_por != user:
                        raise PermissionDenied(
                            "No tienes permisos para acceder a este registro creado por otro usuario."
                        )
                    elif (
                        hasattr(obj, "venta")
                        and hasattr(obj.venta, "creado_por")
                        and obj.venta.creado_por != user
                    ):
                        raise PermissionDenied(
                            "No tienes permisos para acceder a este registro asociado a otra venta."
                        )
                    elif (
                        hasattr(obj, "venta_asociada")
                        and hasattr(obj.venta_asociada, "creado_por")
                        and obj.venta_asociada.creado_por != user
                    ):
                        raise PermissionDenied(
                            "No tienes permisos para acceder a este registro asociado a otra venta."
                        )
        return obj

    def dispatch(self, request, *args, **kwargs):
        """Método: dispatch."""
        user = request.user
        if not user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        agencia = get_user_active_agency(user)
        if not agencia:
            raise PermissionDenied("No tienes una agencia activa asignada.")

        usuario_agencia = user.agencias.filter(agencia=agencia, activo=True).first()
        if not usuario_agencia:
            raise PermissionDenied("No tienes permisos en esta agencia.")

        rol = usuario_agencia.rol

        # Modificaciones (POST, PUT, PATCH, DELETE)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            # 1. Solo Consulta
            if rol == "consulta":
                raise PermissionDenied(
                    "El rol Solo Consulta no tiene permisos para modificar datos."
                )

            # 2. Contador
            if rol == "contador":
                model = getattr(self, "model", None)
                if model:
                    model_name = model.__name__
                    billing_models = [
                        "Factura",
                        "ItemFactura",
                        "GastoOperativo",
                        "PagoVenta",
                        "PagoBinance",
                        "TransaccionPago",
                    ]
                    if model_name not in billing_models:
                        raise PermissionDenied(
                            "El rol Contador no tiene permisos para modificar datos operacionales."
                        )

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Asigna automáticamente la agencia y el creador al crear un objeto.
        """
        user = self.request.user
        if not user.is_superuser:
            agencia = get_user_active_agency(user)
            if agencia:
                if hasattr(form.instance, "agencia"):
                    form.instance.agencia = agencia
                if hasattr(form.instance, "creado_por") and not getattr(
                    form.instance, "creado_por", None
                ):
                    form.instance.creado_por = user
        return super().form_valid(form)


class AgencyRoleRequiredMixin(AccessMixin, SaaSMixin):
    """
    Mixin para restringir vistas a roles específicos dentro de la agencia.
    Uso:
    allowed_roles = ['admin', 'gerente']
    """

    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        """Método: dispatch."""
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        agencia = get_user_active_agency(request.user)
        if agencia:
            usuario_agencia = request.user.agencias.filter(agencia=agencia, activo=True).first()
            if usuario_agencia and usuario_agencia.rol in self.allowed_roles:
                # Si cumple el rol, se delega al dispatch de SaaSMixin para el resto de validaciones
                return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied("No tienes permisos suficientes para realizar esta acción.")


class HtmxResponseMixin:
    """Devuelve un template parcial si la petición viene de HTMX (y no es un link boosted)"""

    htmx_template_name = None

    def get_template_names(self):
        """Método que obtiene template names. Args: según implementación. Returns: datos solicitados."""
        if (
            self.request.headers.get("HX-Request")
            and not self.request.headers.get("HX-Boosted")
            and self.htmx_template_name
        ):
            return [self.htmx_template_name]
        return super().get_template_names()
