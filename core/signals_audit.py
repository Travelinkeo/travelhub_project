import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from core.models.audit import AuditLog, _calcular_diff, crear_audit_log
from core.signals_bypass import are_signals_blocked

logger = logging.getLogger(__name__)


# --- AUDIT SIGNALS FOR VENTA ---
@receiver(post_delete, sender="bookings.Venta")
def audit_delete_venta(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    crear_audit_log(
        modelo="Venta",
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        descripcion=f"Borrado de Venta {instance.localizador}",
        datos_previos={"id": instance.pk, "localizador": instance.localizador},
    )


@receiver(pre_save, sender="bookings.Venta")
def audit_pre_save_venta(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None


@receiver(post_save, sender="bookings.Venta")
def audit_post_save_venta(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    if created:
        crear_audit_log(
            modelo="Venta",
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            venta=instance,
            descripcion=f"Creacion de Venta {instance.localizador}",
            datos_nuevos={"id": instance.pk, "localizador": instance.localizador},
        )
    elif hasattr(instance, "_pre_save_instance") and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo="Venta",
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                venta=instance,
                descripcion=f"Actualizacion de Venta {instance.localizador}",
                datos_previos={k: v["old"] for k, v in diff.items()},
                datos_nuevos={k: v["new"] for k, v in diff.items()},
            )


# --- AUDIT SIGNALS FOR ITEMVENTA ---
@receiver(post_delete, sender="bookings.ItemVenta")
def audit_delete_itemventa(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    crear_audit_log(
        modelo="ItemVenta",
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        venta=instance.venta,
        descripcion=f"Borrado de ItemVenta {instance.pk} ({instance.descripcion_personalizada})",
    )


@receiver(pre_save, sender="bookings.ItemVenta")
def audit_pre_save_itemventa(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None


@receiver(post_save, sender="bookings.ItemVenta")
def audit_post_save_itemventa(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    if created:
        crear_audit_log(
            modelo="ItemVenta",
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            venta=instance.venta,
            descripcion=f"Creacion de ItemVenta {instance.pk}",
            datos_nuevos={"id": instance.pk, "venta_id": instance.venta_id},
        )
    elif hasattr(instance, "_pre_save_instance") and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo="ItemVenta",
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                venta=instance.venta,
                descripcion=f"Actualizacion de ItemVenta {instance.pk}",
                datos_previos={k: v["old"] for k, v in diff.items()},
                datos_nuevos={k: v["new"] for k, v in diff.items()},
            )


# --- AUDIT SIGNALS FOR PASAJERO (CRM) ---
@receiver(post_delete, sender="crm.Pasajero")
def audit_delete_pasajero(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    crear_audit_log(
        modelo="Pasajero",
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        descripcion=f"Borrado de Pasajero {instance.get_nombre_completo()}",
        datos_previos={"id": instance.pk, "nombre": instance.get_nombre_completo()},
    )


@receiver(pre_save, sender="crm.Pasajero")
def audit_pre_save_pasajero(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None


@receiver(post_save, sender="crm.Pasajero")
def audit_post_save_pasajero(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    if created:
        crear_audit_log(
            modelo="Pasajero",
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            descripcion=f"Creacion de Pasajero {instance.get_nombre_completo()}",
            datos_nuevos={"id": instance.pk, "nombre": instance.get_nombre_completo()},
        )
    elif hasattr(instance, "_pre_save_instance") and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo="Pasajero",
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                descripcion=f"Actualizacion de Pasajero {instance.get_nombre_completo()}",
                datos_previos={k: v["old"] for k, v in diff.items()},
                datos_nuevos={k: v["new"] for k, v in diff.items()},
            )


# --- AUDIT SIGNALS FOR FACTURA (FINANCE) ---
@receiver(post_delete, sender="finance.Factura")
def audit_delete_factura(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    venta = getattr(instance, "venta_asociada", None) or getattr(instance, "venta", None)
    numero = getattr(instance, "numero_factura", None) or getattr(instance, "numero_control", None)
    crear_audit_log(
        modelo="Factura",
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        venta=venta,
        descripcion=f"Borrado de Factura {numero}",
    )


@receiver(pre_save, sender="finance.Factura")
def audit_pre_save_factura(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None


@receiver(post_save, sender="finance.Factura")
def audit_post_save_factura(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    venta = getattr(instance, "venta_asociada", None) or getattr(instance, "venta", None)
    numero = getattr(instance, "numero_factura", None) or getattr(instance, "numero_control", None)
    if created:
        crear_audit_log(
            modelo="Factura",
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            venta=venta,
            descripcion=f"Creacion de Factura {numero}",
            datos_nuevos={"id": instance.pk, "numero": str(numero)},
        )
    elif hasattr(instance, "_pre_save_instance") and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo="Factura",
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                venta=venta,
                descripcion=f"Actualizacion de Factura {numero}",
                datos_previos={k: v["old"] for k, v in diff.items()},
                datos_nuevos={k: v["new"] for k, v in diff.items()},
            )


# --- AUDIT SIGNALS FOR PAGOVENTA ---
@receiver(post_delete, sender="bookings.PagoVenta")
def audit_delete_pagovanta(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    crear_audit_log(
        modelo="PagoVenta",
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        venta=instance.venta,
        descripcion=f"Borrado de PagoVenta {instance.pk} ({instance.monto})",
    )


@receiver(pre_save, sender="bookings.PagoVenta")
def audit_pre_save_pagovanta(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None


@receiver(post_save, sender="bookings.PagoVenta")
def audit_post_save_pagovanta(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    if created:
        crear_audit_log(
            modelo="PagoVenta",
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            venta=instance.venta,
            descripcion=f"Creacion de PagoVenta {instance.pk} ({instance.monto})",
            datos_nuevos={
                "id": instance.pk,
                "monto": str(instance.monto),
                "metodo": instance.metodo,
            },
        )
    elif hasattr(instance, "_pre_save_instance") and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo="PagoVenta",
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                venta=instance.venta,
                descripcion=f"Actualizacion de PagoVenta {instance.pk}",
                datos_previos={k: v["old"] for k, v in diff.items()},
                datos_nuevos={k: v["new"] for k, v in diff.items()},
            )


# --- AUDIT SIGNALS FOR FEEVENTA ---
@receiver(post_delete, sender="bookings.FeeVenta")
def audit_delete_feeventa(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    crear_audit_log(
        modelo="FeeVenta",
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        venta=instance.venta,
        descripcion=f"Borrado de FeeVenta {instance.pk} ({instance.monto})",
    )


@receiver(pre_save, sender="bookings.FeeVenta")
def audit_pre_save_feeventa(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None


@receiver(post_save, sender="bookings.FeeVenta")
def audit_post_save_feeventa(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    if created:
        crear_audit_log(
            modelo="FeeVenta",
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            venta=instance.venta,
            descripcion=f"Creacion de FeeVenta {instance.pk} ({instance.monto})",
            datos_nuevos={
                "id": instance.pk,
                "monto": str(instance.monto),
                "tipo_fee": instance.tipo_fee,
            },
        )
    elif hasattr(instance, "_pre_save_instance") and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo="FeeVenta",
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                venta=instance.venta,
                descripcion=f"Actualizacion de FeeVenta {instance.pk}",
                datos_previos={k: v["old"] for k, v in diff.items()},
                datos_nuevos={k: v["new"] for k, v in diff.items()},
            )


# --- AUDIT SIGNALS FOR CLIENTE (CRM) ---
@receiver(post_delete, sender="crm.Cliente")
def audit_delete_cliente(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    crear_audit_log(
        modelo="Cliente",
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        descripcion=f"Borrado de Cliente {instance.get_nombre_completo()}",
        datos_previos={"id": instance.pk, "nombre": instance.get_nombre_completo()},
    )


@receiver(pre_save, sender="crm.Cliente")
def audit_pre_save_cliente(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None


@receiver(post_save, sender="crm.Cliente")
def audit_post_save_cliente(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    if created:
        crear_audit_log(
            modelo="Cliente",
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            descripcion=f"Creacion de Cliente {instance.get_nombre_completo()}",
            datos_nuevos={"id": instance.pk, "nombre": instance.get_nombre_completo()},
        )
    elif hasattr(instance, "_pre_save_instance") and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo="Cliente",
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                descripcion=f"Actualizacion de Cliente {instance.get_nombre_completo()}",
                datos_previos={k: v["old"] for k, v in diff.items()},
                datos_nuevos={k: v["new"] for k, v in diff.items()},
            )


# --- AUDIT SIGNALS FOR PROVEEDOR (BOOKINGS) ---
@receiver(post_delete, sender="bookings.Proveedor")
def audit_delete_proveedor(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    crear_audit_log(
        modelo="Proveedor",
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        descripcion=f"Borrado de Proveedor {instance.nombre}",
        datos_previos={"id": instance.pk, "nombre": instance.nombre},
    )


@receiver(pre_save, sender="bookings.Proveedor")
def audit_pre_save_proveedor(sender, instance, **kwargs):
    if are_signals_blocked():
        return
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None


@receiver(post_save, sender="bookings.Proveedor")
def audit_post_save_proveedor(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    if created:
        crear_audit_log(
            modelo="Proveedor",
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            descripcion=f"Creacion de Proveedor {instance.nombre}",
            datos_nuevos={"id": instance.pk, "nombre": instance.nombre},
        )
    elif hasattr(instance, "_pre_save_instance") and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo="Proveedor",
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                descripcion=f"Actualizacion de Proveedor {instance.nombre}",
                datos_previos={k: v["old"] for k, v in diff.items()},
                datos_nuevos={k: v["new"] for k, v in diff.items()},
            )
