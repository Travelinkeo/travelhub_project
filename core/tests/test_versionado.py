"""
Tests para el Sistema de Versionado de Boletos

Verifica que:
- Los boletos originales se crean con versión 1
- Las re-emisiones incrementan la versión correctamente
- La relación padre-hijo se establece
- Los estados de emisión son correctos
"""
import pytest
from decimal import Decimal
from apps.bookings.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService

pytestmark = pytest.mark.django_db

class TestTicketVersioning:
    """Suite de tests para versionado de boletos"""
    
    def test_boleto_original_version_1(self, agencia):
        """Test: Boleto original debe tener versión 1"""
        boleto = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto="TEST001",
            nombre_pasajero_completo="TEST/USER",
            total_boleto=Decimal("100.00")
        )
        
        assert boleto.version == 1
        assert boleto.estado_emision == BoletoImportado.EstadoEmision.ORIGINAL
        assert boleto.boleto_padre is None
    
    def test_reemision_incrementa_version(self, agencia):
        """Test: Re-emisión debe incrementar versión a 2"""
        # Crear boleto original
        boleto_v1 = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto="TEST002",
            nombre_pasajero_completo="TEST/USER",
            total_boleto=Decimal("200.00"),
            estado_parseo="COM"
        )
        
        # Crear re-emisión
        boleto_v2 = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto="TEST002",  # Mismo número
            nombre_pasajero_completo="TEST/USER",
            total_boleto=Decimal("250.00"),  # Precio diferente
            estado_parseo="PEN"
        )
        
        # Aplicar lógica de versionado
        service = TicketParserService()
        service._gestionar_versionado(boleto_v2)
        
        # Recargar desde DB
        boleto_v2.refresh_from_db()
        
        assert boleto_v2.version == 2
        assert boleto_v2.estado_emision == BoletoImportado.EstadoEmision.REEMISION
        assert boleto_v2.boleto_padre == boleto_v1
    
    def test_multiples_reemisiones(self, agencia):
        """Test: Múltiples re-emisiones deben incrementar versión secuencialmente"""
        numero_boleto = "TEST003"
        
        # V1: Original
        v1 = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto=numero_boleto,
            total_boleto=Decimal("300.00"),
            estado_parseo="COM"
        )
        
        # V2: Primera re-emisión
        v2 = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto=numero_boleto,
            total_boleto=Decimal("320.00"),
            estado_parseo="PEN"
        )
        
        service = TicketParserService()
        service._gestionar_versionado(v2)
        v2.refresh_from_db()
        
        # V3: Segunda re-emisión
        v3 = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto=numero_boleto,
            total_boleto=Decimal("350.00"),
            estado_parseo="PEN"
        )
        
        service._gestionar_versionado(v3)
        v3.refresh_from_db()
        
        assert v1.version == 1
        assert v2.version == 2
        assert v3.version == 3
        
        assert v2.boleto_padre == v1
        assert v3.boleto_padre == v2
    
    def test_historial_versiones(self, agencia):
        """Test: Debe poder recuperar historial completo de versiones"""
        numero_boleto = "TEST004"
        
        # Crear 3 versiones
        for i in range(1, 4):
            boleto = BoletoImportado.objects.create(
                agencia=agencia,
                numero_boleto=numero_boleto,
                total_boleto=Decimal(f"{100 * i}.00"),
                estado_parseo="COM" if i == 1 else "PEN"
            )
            
            if i > 1:
                service = TicketParserService()
                service._gestionar_versionado(boleto)
        
        # Recuperar historial
        historial = BoletoImportado.objects.filter(
            numero_boleto=numero_boleto
        ).order_by('version')
        
        assert historial.count() == 3
        assert list(historial.values_list('version', flat=True)) == [1, 2, 3]
    
    def test_versiones_posteriores_relation(self, agencia):
        """Test: Debe poder acceder a versiones posteriores desde el padre"""
        numero_boleto = "TEST005"
        
        # V1
        v1 = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto=numero_boleto,
            total_boleto=Decimal("400.00"),
            estado_parseo="COM"
        )
        
        # V2
        v2 = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto=numero_boleto,
            total_boleto=Decimal("420.00"),
            estado_parseo="PEN"
        )
        
        service = TicketParserService()
        service._gestionar_versionado(v2)
        v2.refresh_from_db()
        
        # Verificar relación inversa
        posteriores = v1.versiones_posteriores.all()
        assert posteriores.count() == 1
        assert posteriores.first() == v2
    
    @pytest.mark.critical
    def test_versionado_no_afecta_boletos_diferentes(self, agencia):
        """Test: Versionado solo debe afectar boletos con mismo número"""
        # Boleto A
        boleto_a = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto="TESTA",
            total_boleto=Decimal("500.00"),
            estado_parseo="COM"
        )
        
        # Boleto B (diferente)
        boleto_b = BoletoImportado.objects.create(
            agencia=agencia,
            numero_boleto="TESTB",
            total_boleto=Decimal("600.00"),
            estado_parseo="COM"
        )
        
        # Ambos deben ser versión 1
        assert boleto_a.version == 1
        assert boleto_b.version == 1
        assert boleto_a.boleto_padre is None
        assert boleto_b.boleto_padre is None
