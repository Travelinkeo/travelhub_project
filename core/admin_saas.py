from django.contrib import admin
from django.db import models

class SaaSAdminMixin:
    """
    Mixin para aislar datos por agencia en el Django Admin.
    Asegura que:
    1. El QuerySet esté filtrado por la agencia del usuario.
    2. La agencia se asigne automáticamente al guardar.
    3. Los campos de selección (ForeignKeys) solo muestren datos de la misma agencia.
    4. El campo 'agencia' esté oculto para no-superusuarios.
    """
    
    saas_agency_field = 'agencia'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # 'agencia' es inyectado en el request por SaasLimitMiddleware
        if hasattr(request, 'agencia') and request.agencia:
            # Soportar lookups directos o relacionados (ej: 'venta__agencia')
            if '__' in self.saas_agency_field or hasattr(self.model, self.saas_agency_field):
                return qs.filter(**{self.saas_agency_field: request.agencia})
        
        # Si no tiene agencia asignada y no es superusuario, no ve nada si el modelo debería ser aislado
        should_isolate = '__' in self.saas_agency_field or hasattr(self.model, self.saas_agency_field)
        return qs.none() if should_isolate else qs

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not change:
            # Solo asignar si es un campo directo
            if '__' not in self.saas_agency_field and hasattr(obj, self.saas_agency_field) and hasattr(request, 'agencia'):
                setattr(obj, self.saas_agency_field, request.agencia)
        super().save_model(request, obj, form, change)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser and '__' not in self.saas_agency_field:
            # Ocultar campo agencia en todos los fieldsets solo si es directo
            for name, options in fieldsets:
                if 'fields' in options:
                    # Filtrar fields que sean exactamente el nombre del campo de agencia
                    options['fields'] = [f for f in options['fields'] if f != self.saas_agency_field]
        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request, 'agencia') and request.agencia:
            # Filtrar dropdowns si el modelo relacionado tiene campo 'agencia'
            related_model = db_field.remote_field.model
            if hasattr(related_model, 'agencia'):
                kwargs["queryset"] = related_model.objects.filter(agencia=request.agencia)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request, 'agencia') and request.agencia:
            related_model = db_field.remote_field.model
            if hasattr(related_model, 'agencia'):
                kwargs["queryset"] = related_model.objects.filter(agencia=request.agencia)
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    def has_view_permission(self, request, obj=None):
        return True # El queryset ya filtra

    def has_add_permission(self, request):
        if request.user.is_superuser: return True
        return hasattr(request, 'agencia') and request.agencia is not None

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        if obj is None: return hasattr(request, 'agencia') and request.agencia is not None
        # Verificar que el objeto pertenezca a la agencia
        if hasattr(obj, self.saas_agency_field):
            return getattr(obj, self.saas_agency_field) == request.agencia
        return True

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        if obj is None: return hasattr(request, 'agencia') and request.agencia is not None
        if hasattr(obj, self.saas_agency_field):
            return getattr(obj, self.saas_agency_field) == request.agencia
        return True
