import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from core.models.audit import AuditLog, crear_audit_log, _calcular_diff

logger = logging.getLogger(__name__)

# --- AUDIT SIGNALS FOR VENTA ---
@receiver(post_delete, sender='bookings.Venta')
def audit_delete_venta(sender, instance, **kwargs):
    crear_audit_log(
        modelo='Venta',
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        descripcion=f"Borrado de Venta {instance.localizador}",
        datos_previos={'id': instance.pk, 'localizador': instance.localizador}
    )

@receiver(pre_save, sender='bookings.Venta')
def audit_pre_save_venta(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None

@receiver(post_save, sender='bookings.Venta')
def audit_post_save_venta(sender, instance, created, **kwargs):
    if created:
        crear_audit_log(
            modelo='Venta',
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            venta=instance,
            descripcion=f"Creación de Venta {instance.localizador}",
            datos_nuevos={'id': instance.pk, 'localizador': instance.localizador}
        )
    elif hasattr(instance, '_pre_save_instance') and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo='Venta',
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                venta=instance,
                descripcion=f"Actualización de Venta {instance.localizador}",
                datos_previos={k: v['old'] for k, v in diff.items()},
                datos_nuevos={k: v['new'] for k, v in diff.items()}
            )

# --- AUDIT SIGNALS FOR ITEMVENTA ---
@receiver(post_delete, sender='bookings.ItemVenta')
def audit_delete_itemventa(sender, instance, **kwargs):
    crear_audit_log(
        modelo='ItemVenta',
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        venta=instance.venta,
        descripcion=f"Borrado de ItemVenta {instance.pk} ({instance.descripcion_personalizada})"
    )

@receiver(pre_save, sender='bookings.ItemVenta')
def audit_pre_save_itemventa(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None

@receiver(post_save, sender='bookings.ItemVenta')
def audit_post_save_itemventa(sender, instance, created, **kwargs):
    if created:
        crear_audit_log(
            modelo='ItemVenta',
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            venta=instance.venta,
            descripcion=f"Creación de ItemVenta {instance.pk}",
            datos_nuevos={'id': instance.pk, 'venta_id': instance.venta_id}
        )
    elif hasattr(instance, '_pre_save_instance') and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo='ItemVenta',
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                venta=instance.venta,
                descripcion=f"Actualización de ItemVenta {instance.pk}",
                datos_previos={k: v['old'] for k, v in diff.items()},
                datos_nuevos={k: v['new'] for k, v in diff.items()}
            )

# --- AUDIT SIGNALS FOR PASAJERO (CRM) ---
@receiver(post_delete, sender='crm.Pasajero')
def audit_delete_pasajero(sender, instance, **kwargs):
    crear_audit_log(
        modelo='Pasajero',
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        descripcion=f"Borrado de Pasajero {instance.get_nombre_completo()}",
        datos_previos={'id': instance.pk, 'nombre': instance.get_nombre_completo()}
    )

@receiver(pre_save, sender='crm.Pasajero')
def audit_pre_save_pasajero(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None

@receiver(post_save, sender='crm.Pasajero')
def audit_post_save_pasajero(sender, instance, created, **kwargs):
    if created:
        crear_audit_log(
            modelo='Pasajero',
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            descripcion=f"Creación de Pasajero {instance.get_nombre_completo()}",
            datos_nuevos={'id': instance.pk, 'nombre': instance.get_nombre_completo()}
        )
    elif hasattr(instance, '_pre_save_instance') and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo='Pasajero',
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                descripcion=f"Actualización de Pasajero {instance.get_nombre_completo()}",
                datos_previos={k: v['old'] for k, v in diff.items()},
                datos_nuevos={k: v['new'] for k, v in diff.items()}
            )

# --- AUDIT SIGNALS FOR FACTURA (FINANCE) ---
@receiver(post_delete, sender='finance.Factura')
def audit_delete_factura(sender, instance, **kwargs):
    crear_audit_log(
        modelo='Factura',
        object_id=instance.pk,
        accion=AuditLog.Accion.DELETE,
        venta=instance.venta_asociada,
        descripcion=f"Borrado de Factura {instance.numero_factura}"
    )

@receiver(pre_save, sender='finance.Factura')
def audit_pre_save_factura(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._pre_save_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._pre_save_instance = None

@receiver(post_save, sender='finance.Factura')
def audit_post_save_factura(sender, instance, created, **kwargs):
    if created:
        crear_audit_log(
            modelo='Factura',
            object_id=instance.pk,
            accion=AuditLog.Accion.CREATE,
            venta=instance.venta_asociada,
            descripcion=f"Creación de Factura {instance.numero_factura}",
            datos_nuevos={'id': instance.pk, 'numero': instance.numero_factura}
        )
    elif hasattr(instance, '_pre_save_instance') and instance._pre_save_instance:
        diff = _calcular_diff(instance._pre_save_instance, instance)
        if diff:
            crear_audit_log(
                modelo='Factura',
                object_id=instance.pk,
                accion=AuditLog.Accion.UPDATE,
                venta=instance.venta_asociada,
                descripcion=f"Actualización de Factura {instance.numero_factura}",
                datos_previos={k: v['old'] for k, v in diff.items()},
                datos_nuevos={k: v['new'] for k, v in diff.items()}
            )
