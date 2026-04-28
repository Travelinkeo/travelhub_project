import hashlib
import json as _json
import logging
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone as _tz
from core.middleware import get_current_request_meta

logger = logging.getLogger(__name__)

class AuditLog(models.Model):
    """
    Log de Auditoría Forense (Bóveda de Estado).
    Registra cambios inmutables en modelos críticos con encadenamiento de hash.
    """
    class Accion(models.TextChoices):
        CREATE = 'CREATE', _('Creación')
        UPDATE = 'UPDATE', _('Actualización')
        DELETE = 'DELETE', _('Eliminación')
        STATE = 'STATE', _('Cambio de Estado')
        LOGIN = 'LOGIN', _('Inicio de Sesión')
        LOGOUT = 'LOGOUT', _('Cierre de Sesión')
    
    # Aliases
    Action = Accion 

    id_audit_log = models.AutoField(primary_key=True, verbose_name=_("ID Audit Log"))
    modelo = models.CharField(_("Modelo"), max_length=120, db_index=True)
    object_id = models.CharField(_("Object ID"), max_length=120, db_index=True)
    
    # Referencia opcional a Venta para facilitar filtrado en el panel de ventas
    venta = models.ForeignKey('bookings.Venta', related_name='audit_logs_central', on_delete=models.CASCADE, blank=True, null=True, verbose_name=_("Venta Asociada"))
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Usuario"), related_name='audit_logs_central_creados')
    accion = models.CharField(_("Acción"), max_length=10, choices=Accion.choices)
    descripcion = models.TextField(_("Descripción / Resumen"), blank=True, null=True)
    
    datos_previos = models.JSONField(_("Datos Previos"), blank=True, null=True)
    datos_nuevos = models.JSONField(_("Datos Nuevos"), blank=True, null=True)
    metadata_extra = models.JSONField(_("Metadata Extra"), blank=True, null=True)
    
    creado = models.DateTimeField(_("Creado"), auto_now_add=True, db_index=True)
    
    # DOCTRINA ANTIGRAVITY: Encadenamiento de integridad (Blockchain-style)
    previous_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    record_hash = models.CharField(max_length=64, blank=True, null=True, unique=True, db_index=True)

    class Meta:
        verbose_name = _("Log de Auditoría")
        verbose_name_plural = _("Logs de Auditoría")
        ordering = ['-creado']
        db_table = 'core_auditlog' # Mantenemos el nombre de tabla para compatibilidad

    def __str__(self):
        return f"AuditLog {self.modelo} {self.object_id} {self.accion} {self.creado:%Y-%m-%d %H:%M:%S}"

    def save(self, *args, **kwargs):
        es_creacion = self.pk is None
        if es_creacion and not self.creado:
            self.creado = _tz.now()
            
        if es_creacion and not self.previous_hash:
            ultimo = AuditLog.objects.order_by('-creado', '-id_audit_log').first()
            self.previous_hash = ultimo.record_hash if ultimo else "0" * 64
            
        super().save(*args, **kwargs)
        
        if es_creacion and not self.record_hash:
            # Construir payload para el hash
            payload = {
                'modelo': self.modelo,
                'object_id': self.object_id,
                'accion': self.accion,
                'datos_previos': self.datos_previos,
                'datos_nuevos': self.datos_nuevos,
                'creado': self.creado.isoformat()
            }
            try:
                canon = _json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            except Exception:
                canon = str(payload)
                
            base_str = (self.previous_hash or '') + '|' + canon
            self.record_hash = hashlib.sha256(base_str.encode('utf-8')).hexdigest()
            super().save(update_fields=['record_hash'])

def crear_audit_log(*, modelo, object_id, accion, venta=None, descripcion=None, datos_previos=None, datos_nuevos=None, metadata_extra=None):
    """
    Función utilitaria centralizada para crear logs de auditoría capturando el contexto.
    """
    try:
        req_meta = get_current_request_meta()
        merged_meta = metadata_extra.copy() if metadata_extra else {}
        user_obj = None
        
        if req_meta:
            merged_meta.setdefault('ip', req_meta.get('ip'))
            merged_meta.setdefault('user_agent', req_meta.get('user_agent'))
            # El middleware guarda el usuario en _request_local.user, pero req_meta solo tiene ip/ua?
            # Revisando core/middleware.py, ThreadLocalContextMiddleware guarda user por separado.
            from core.middleware import get_current_user
            user_obj = get_current_user()

        return AuditLog.objects.create(
            modelo=modelo,
            object_id=str(object_id),
            accion=accion,
            venta=venta,
            user=user_obj,
            descripcion=descripcion,
            datos_previos=datos_previos,
            datos_nuevos=datos_nuevos,
            metadata_extra=merged_meta or None
        )
    except Exception:
        logger.exception(f"Fallo creando AuditLog para {modelo} {object_id}")
        return None

def _sanitize_value(val):
    from decimal import Decimal
    import datetime
    from django.db.models.fields.files import FieldFile
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, FieldFile):
        return val.name if val else None
    if hasattr(val, 'id_cliente'): return val.id_cliente
    if hasattr(val, 'id_pasajero'): return val.id_pasajero
    if hasattr(val, 'pk'): return val.pk
    return val

def _calcular_diff(prev, current, exclude_fields=None):
    if exclude_fields is None:
        exclude_fields = [
            'creado', 'actualizado', 'creado_por', 'id_audit_log', 
            'fecha_actualizacion', 'id_venta', 'id_item_venta'
        ]
    
    diff = {}
    for field in current._meta.fields:
        name = field.name
        if name in exclude_fields or name.startswith('_'):
            continue
        
        try:
            val_prev = getattr(prev, name, None)
            val_curr = getattr(current, name, None)
            
            if val_prev != val_curr:
                diff[name] = {
                    'old': _sanitize_value(val_prev),
                    'new': _sanitize_value(val_curr)
                }
        except Exception:
            continue
    return diff
