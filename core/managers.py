"""
Nota histórica: TenantManager y TenantModelMixin fueron eliminados.
Toda la lógica de multi-tenancy está centralizada en:
  - core.models.base.AgenciaManager (manager principal con filtro por agencia + globales)
  - core.models.base.AgenciaMixin (mixin que asigna objects = AgenciaManager)
El TenantManager anterior era código muerto (ningún modelo lo utilizaba).
"""
