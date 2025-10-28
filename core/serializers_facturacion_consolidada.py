"""
Serializers para modelos consolidados de facturación venezolana.
"""

from rest_framework import serializers
from .models import FacturaConsolidada, ItemFacturaConsolidada, DocumentoExportacionConsolidado
from .serializers import ClienteSerializer, MonedaSerializer


class ItemFacturaConsolidadaSerializer(serializers.ModelSerializer):
    """Serializer para items de factura consolidada"""
    
    class Meta:
        model = ItemFacturaConsolidada
        fields = [
            'id_item_factura', 'descripcion', 'cantidad', 'precio_unitario',
            'subtotal_item', 'tipo_servicio', 'es_gravado', 'alicuota_iva',
            'nombre_pasajero', 'numero_boleto', 'itinerario', 'codigo_aerolinea'
        ]
        read_only_fields = ('subtotal_item',)


class DocumentoExportacionConsolidadoSerializer(serializers.ModelSerializer):
    """Serializer para documentos de exportación"""
    
    class Meta:
        model = DocumentoExportacionConsolidado
        fields = '__all__'


class FacturaConsolidadaSerializer(serializers.ModelSerializer):
    """Serializer para factura consolidada con normativa venezolana"""
    
    items_factura = ItemFacturaConsolidadaSerializer(many=True, required=False)
    documentos_exportacion = DocumentoExportacionConsolidadoSerializer(many=True, read_only=True)
    cliente_detalle = ClienteSerializer(source='cliente', read_only=True)
    moneda_detalle = MonedaSerializer(source='moneda', read_only=True)
    venta_asociada_numero = serializers.CharField(
        source='venta_asociada.localizador', 
        read_only=True, 
        allow_null=True
    )
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_operacion_display = serializers.CharField(source='get_tipo_operacion_display', read_only=True)
    moneda_operacion_display = serializers.CharField(source='get_moneda_operacion_display', read_only=True)
    
    class Meta:
        model = FacturaConsolidada
        fields = [
            # IDs y referencias
            'id_factura', 'numero_factura', 'numero_control',
            'venta_asociada', 'venta_asociada_numero',
            'cliente', 'cliente_detalle',
            
            # Fechas
            'fecha_emision', 'fecha_vencimiento',
            
            # Emisor (agencia)
            'emisor_rif', 'emisor_razon_social', 'emisor_direccion_fiscal',
            'es_sujeto_pasivo_especial', 'esta_inscrita_rtn',
            
            # Cliente
            'cliente_es_residente', 'cliente_identificacion', 'cliente_direccion',
            
            # Tipo de operación
            'tipo_operacion', 'tipo_operacion_display',
            
            # Moneda y cambio
            'moneda', 'moneda_detalle',
            'moneda_operacion', 'moneda_operacion_display',
            'tasa_cambio_bcv',
            
            # Bases imponibles (USD)
            'subtotal_base_gravada', 'subtotal_exento', 'subtotal_exportacion',
            
            # Impuestos (USD)
            'monto_iva_16', 'monto_iva_adicional', 'monto_igtf',
            
            # Totales (USD)
            'subtotal', 'monto_total', 'saldo_pendiente',
            
            # Equivalentes en Bolívares
            'subtotal_base_gravada_bs', 'subtotal_exento_bs',
            'monto_iva_16_bs', 'monto_igtf_bs', 'monto_total_bs',
            
            # Intermediación
            'tercero_rif', 'tercero_razon_social',
            
            # Digital
            'modalidad_emision', 'firma_digital',
            
            # Estado
            'estado', 'estado_display',
            
            # Archivos
            'archivo_pdf',
            
            # Contabilidad
            'asiento_contable_factura',
            
            # Notas
            'notas',
            
            # Items y documentos
            'items_factura',
            'documentos_exportacion',
        ]
        read_only_fields = (
            'numero_factura', 'subtotal', 'monto_total', 'saldo_pendiente',
            'subtotal_base_gravada_bs', 'subtotal_exento_bs',
            'monto_iva_16_bs', 'monto_igtf_bs', 'monto_total_bs'
        )
    
    def create(self, validated_data):
        """Crear factura con items"""
        items_data = validated_data.pop('items_factura', [])
        factura = FacturaConsolidada.objects.create(**validated_data)
        
        for item_data in items_data:
            ItemFacturaConsolidada.objects.create(factura=factura, **item_data)
        
        return factura
    
    def update(self, instance, validated_data):
        """Actualizar factura con items"""
        items_data = validated_data.pop('items_factura', None)
        
        # Actualizar factura
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar items si se proporcionaron
        if items_data is not None:
            # Eliminar items existentes
            instance.items_factura.all().delete()
            # Crear nuevos items
            for item_data in items_data:
                ItemFacturaConsolidada.objects.create(factura=instance, **item_data)
        
        return instance
