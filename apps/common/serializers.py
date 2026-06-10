from django.contrib.auth.models import User
from rest_framework import serializers

from apps.common.models import Aerolinea, Ciudad, Pais
from core.models.agencia import Agencia, UsuarioAgencia
from core.models.audit import AuditLog


class PaisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pais
        fields = ["id_pais", "nombre", "codigo_iso_2", "codigo_iso_3"]


class CiudadSerializer(serializers.ModelSerializer):
    pais_detalle = PaisSerializer(source="pais", read_only=True)

    class Meta:
        model = Ciudad
        fields = ["id_ciudad", "nombre", "pais", "pais_detalle", "region_estado"]
        extra_kwargs = {"pais": {"write_only": True}}


class AerolineaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aerolinea
        fields = ["id_aerolinea", "codigo_iata", "nombre", "activa"]


class AuditLogSerializer(serializers.ModelSerializer):
    venta_localizador = serializers.CharField(source="venta.localizador", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id_audit_log",
            "modelo",
            "object_id",
            "venta",
            "venta_localizador",
            "accion",
            "descripcion",
            "datos_previos",
            "datos_nuevos",
            "metadata_extra",
            "creado",
        ]
        read_only_fields = fields


class UsuarioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "nombre_completo",
            "is_active",
        ]
        read_only_fields = ["id"]


class AgenciaSerializer(serializers.ModelSerializer):
    propietario_nombre = serializers.CharField(source="propietario.get_full_name", read_only=True)
    total_usuarios = serializers.SerializerMethodField()

    class Meta:
        model = Agencia
        fields = [
            "id",
            "nombre",
            "nombre_comercial",
            "rif",
            "iata",
            "telefono_principal",
            "telefono_secundario",
            "email_principal",
            "email_soporte",
            "email_ventas",
            "direccion",
            "ciudad",
            "estado",
            "pais",
            "codigo_postal",
            "branding",
            "configuracion",
            "website",
            "facebook",
            "instagram",
            "twitter",
            "whatsapp",
            "activa",
            "dominio_personalizado",
            "fecha_creacion",
            "fecha_actualizacion",
            "propietario",
            "propietario_nombre",
            "total_usuarios",
        ]
        read_only_fields = ["fecha_creacion", "fecha_actualizacion", "propietario"]

    def get_total_usuarios(self, obj):
        return obj.usuarios.filter(activo=True).count()


class UsuarioAgenciaSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source="usuario", read_only=True)
    agencia_nombre = serializers.CharField(source="agencia.nombre", read_only=True)
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)

    class Meta:
        model = UsuarioAgencia
        fields = [
            "id",
            "usuario",
            "usuario_detalle",
            "agencia",
            "agencia_nombre",
            "rol",
            "rol_display",
            "activo",
            "fecha_asignacion",
            "telegram_chat_id",
        ]
        read_only_fields = ["fecha_asignacion", "agencia"]


class CrearUsuarioAgenciaSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    rol = serializers.ChoiceField(choices=UsuarioAgencia.ROLES)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya existe")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está registrado")
        return value


class ComunicacionProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.communications.models import ComunicacionProveedor

        model = ComunicacionProveedor
        fields = [
            "id",
            "remitente",
            "asunto",
            "fecha_recepcion",
            "categoria",
            "contenido_extraido",
            "cuerpo_completo",
        ]
        read_only_fields = fields
