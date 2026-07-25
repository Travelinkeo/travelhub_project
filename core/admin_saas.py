class SaaSAdminMixin:
    """
    Mixin para aislar datos por agencia en el Django Admin.
    Asegura que:
    1. El QuerySet este filtrado por la agencia del usuario.
    2. La agencia se asigne automaticamente al guardar.
    3. Los campos de seleccion (ForeignKeys) solo muestren datos de la misma agencia.
    4. El campo 'agencia' este oculto para no-superusuarios.
    """

    saas_agency_field = "agencia"

    def get_queryset(self, request):
        """Filtra queryset por agencia para aislamiento multi-tenant. Args: request. Returns: QuerySet."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        if hasattr(request, "agencia") and request.agencia:
            if "__" in self.saas_agency_field or hasattr(self.model, self.saas_agency_field):
                return qs.filter(**{self.saas_agency_field: request.agencia})

        should_isolate = "__" in self.saas_agency_field or hasattr(
            self.model, self.saas_agency_field
        )
        return qs.none() if should_isolate else qs

    def save_model(self, request, obj, form, change):
        """Método que actualiza/guarda model."""
        if not request.user.is_superuser and not change:
            if (
                "__" not in self.saas_agency_field
                and hasattr(obj, self.saas_agency_field)
                and hasattr(request, "agencia")
            ):
                setattr(obj, self.saas_agency_field, request.agencia)
        super().save_model(request, obj, form, change)

    def get_fieldsets(self, request, obj=None):
        """Método que obtiene fieldsets. Args: según implementación. Returns: datos solicitados."""
        fieldsets = super().get_fieldsets(request, obj)
        if fieldsets is None:
            return None
        if not request.user.is_superuser and "__" not in self.saas_agency_field:
            for _name, options in fieldsets:
                if "fields" in options:
                    options["fields"] = [
                        f for f in options["fields"] if f != self.saas_agency_field
                    ]
        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Método: formfield for foreignkey."""
        if not request.user.is_superuser and hasattr(request, "agencia") and request.agencia:
            related_model = db_field.remote_field.model
            if hasattr(related_model, "agencia"):
                kwargs["queryset"] = related_model.objects.filter(agencia=request.agencia)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Método: formfield for manytomany."""
        if not request.user.is_superuser and hasattr(request, "agencia") and request.agencia:
            related_model = db_field.remote_field.model
            if hasattr(related_model, "agencia"):
                kwargs["queryset"] = related_model.objects.filter(agencia=request.agencia)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def has_view_permission(self, request, obj=None):
        """Método que verifica  view permission. Returns: bool."""
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return hasattr(request, "agencia") and request.agencia is not None

    def has_add_permission(self, request):
        """Método que verifica  add permission. Returns: bool."""
        if request.user.is_superuser:
            return True
        return hasattr(request, "agencia") and request.agencia is not None

    def _get_obj_agency(self, obj):
        """Resuelve la agencia del objeto, soportando campos con __ (FK chain)."""
        if obj is None:
            return None
        if "__" not in self.saas_agency_field:
            return getattr(obj, self.saas_agency_field, None)
        parts = self.saas_agency_field.split("__")
        current = obj
        for part in parts:
            current = getattr(current, part, None)
            if current is None:
                return None
        return current

    def has_change_permission(self, request, obj=None):
        """Método que verifica  change permission. Returns: bool."""
        if request.user.is_superuser:
            return True
        if obj is None:
            return hasattr(request, "agencia") and request.agencia is not None
        obj_agency = self._get_obj_agency(obj)
        if obj_agency is not None:
            return obj_agency == request.agencia
        return False

    def has_delete_permission(self, request, obj=None):
        """Método que verifica  delete permission. Returns: bool."""
        if request.user.is_superuser:
            return True
        if obj is None:
            return hasattr(request, "agencia") and request.agencia is not None
        obj_agency = self._get_obj_agency(obj)
        if obj_agency is not None:
            return obj_agency == request.agencia
        return False
