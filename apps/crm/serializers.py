from rest_framework import serializers

from .models import Cliente, Pasajero, PasaporteEscaneado


class CoreClienteSerializer(serializers.ModelSerializer):
    """CoreClienteSerializer."""

    get_nombre_completo = serializers.CharField(read_only=True)
    id_cliente = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Cliente
        fields = ["id_cliente", "get_nombre_completo", "email", "nombre_empresa"]


class ClienteSerializer(serializers.ModelSerializer):
    """ClienteSerializer."""

    get_nombre_completo = serializers.CharField(read_only=True)
    id_cliente = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id_cliente",
            "tipo_cliente",
            "nombres",
            "apellidos",
            "cedula_identidad",
            "nombre_empresa",
            "email",
            "telefono_principal",
            "fecha_nacimiento",
            "nacionalidad",
            "numero_pasaporte",
            "pais_emision_pasaporte",
            "fecha_expiracion_pasaporte",
            "direccion",
            "ciudad",
            "puntos_fidelidad",
            "es_cliente_frecuente",
            "get_nombre_completo",
        ]


class PasajeroSerializer(serializers.ModelSerializer):
    """PasajeroSerializer."""

    nombre_completo = serializers.CharField(read_only=True)
    numero_documento = serializers.CharField(read_only=True)

    class Meta:
        model = Pasajero
        fields = [
            "id_pasajero",
            "uuid",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "numero_pasaporte",
            "cedula_identidad",
            "email",
            "telefono",
            "nacionalidad",
            "pais_emision_documento",
            "tipo_documento",
            "fecha_emision_documento",
            "fecha_vencimiento_documento",
            "fecha_vencimiento_pasaporte",
            "preferencias",
            "notas",
            "documento_hash",
            "tiene_fiebre_amarilla",
            "fecha_vacuna_fiebre_amarilla",
            "foto_perfil",
            "nombre_completo",
            "numero_documento",
            "agencia",
            "is_deleted",
            "deleted_at",
        ]
        read_only_fields = ["agencia", "is_deleted", "deleted_at", "documento_hash", "uuid"]


class PasaporteEscaneadoSerializer(serializers.ModelSerializer):
    """PasaporteEscaneadoSerializer."""

    es_valido = serializers.ReadOnlyField()
    nombre_completo = serializers.ReadOnlyField()

    class Meta:
        model = PasaporteEscaneado
        fields = [
            "id",
            "imagen_original",
            "imagen_procesada",
            "numero_pasaporte",
            "nombres",
            "apellidos",
            "nacionalidad",
            "fecha_nacimiento",
            "fecha_vencimiento",
            "sexo",
            "lugar_nacimiento",
            "confianza_ocr",
            "datos_ocr_completos",
            "texto_mrz",
            "errores_detectados",
            "fecha_procesamiento",
            "verificado_manualmente",
            "cliente",
            "procesado_por",
            "agencia",
            "es_valido",
            "nombre_completo",
        ]
        read_only_fields = ["agencia", "fecha_procesamiento", "datos_ocr_completos", "texto_mrz"]
