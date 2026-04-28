"""
Fixtures compartidos para tests de TravelHub
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model


    Agencia, Cliente, Moneda, Proveedor,
    BoletoImportado, Venta, ItemVenta,
    ProductoServicio
)

User = get_user_model()

@pytest.fixture
def user_propietario(db):
    """Crea un usuario propietario para la agencia"""
    User = get_user_model()
    return User.objects.create_user(
        username="propietario",
        email="propietario@test.com",
        password="testpass123"
    )

@pytest.fixture
def agencia(db, user_propietario):
    """Crea una agencia de prueba"""
    return Agencia.objects.create(
        nombre="Agencia Test",
        nombre_comercial="Agencia Test",
        email_principal="test@agencia.com",
        propietario=user_propietario
    )

@pytest.fixture
def cliente(db):
    """Crea un cliente de prueba"""
    from apps.crm.models import Cliente
    return Cliente.objects.create(
        nombres="Juan",
        apellidos="Pérez",
        email=f"juan.perez.{timezone.now().timestamp()}@test.com",  # Email único
        telefono_principal="+58412123456"
    )

@pytest.fixture
def moneda_usd(db):
    """Crea moneda USD"""
    return Moneda.objects.get_or_create(
        codigo_iso="USD",
        defaults={
            "nombre": "Dólar Estadounidense",
            "simbolo": "$"
        }
    )[0]

@pytest.fixture
def moneda_ves(db):
    """Crea moneda VES"""
    return Moneda.objects.get_or_create(
        codigo_iso="VES",
        defaults={
            "nombre": "Bolívar Venezolano",
            "simbolo": "Bs"
        }
    )[0]

@pytest.fixture
def proveedor_avianca(db):
    """Crea proveedor Avianca"""
    return Proveedor.objects.create(
        nombre_comercial="Avianca",
        razon_social="Avianca S.A.",
        tipo_proveedor="AER",
        pais_origen_id=1  # Asume que existe
    )

@pytest.fixture
def producto_boleto(db):
    """Crea producto de tipo boleto aéreo"""
    return ProductoServicio.objects.get_or_create(
        nombre="Boleto Aéreo",
        defaults={
            "tipo_producto": "AIR",
            "descripcion": "Boleto aéreo nacional o internacional"
        }
    )[0]

@pytest.fixture
def venta_base(db, agencia, moneda_usd):
    """Crea una venta base"""
    from apps.crm.models import Cliente
    
    # Crear cliente inline para evitar problemas de instancia
    cliente, _ = Cliente.objects.get_or_create(
        email=f"venta.test.{timezone.now().timestamp()}@test.com",
        defaults={
            "nombres": "Test",
            "apellidos": "Venta"
        }
    )
    
    return Venta.objects.create(
        agencia=agencia,
        cliente=cliente,
        moneda=moneda_usd,
        localizador="ABC123",
        total_venta=Decimal("500.00"),
        estado="PEN",
        fecha_venta=timezone.now()
    )

@pytest.fixture
def boleto_importado(db, agencia):
    """Crea un boleto importado de prueba"""
    return BoletoImportado.objects.create(
        agencia=agencia,
        numero_boleto="1234567890",
        nombre_pasajero_completo="DOE/JOHN",
        localizador_pnr="ABC123",
        aerolinea_emisora="AVIANCA",
        total_boleto=Decimal("500.00"),
        estado_parseo="COM",
        version=1,
        estado_emision=BoletoImportado.EstadoEmision.ORIGINAL
    )

@pytest.fixture
def datos_boleto_sabre():
    """Datos parseados de un boleto Sabre"""
    return {
        "gds": "sabre",
        "pnr": "XYZ789",
        "ticket_number": "9876543210",
        "passenger_name": "SMITH/JANE",
        "airline_name": "COPA AIRLINES",
        "total": "750.00",
        "moneda": "USD",
        "issue_date": "15JAN26",
        "itinerary": [
            {
                "origin": "CCS",
                "destination": "PTY",
                "date": "20JAN26",
                "flight": "CM123"
            }
        ]
    }

@pytest.fixture
def datos_boleto_kiu():
    """Datos parseados de un boleto KIU"""
    return {
        "gds": "kiu",
        "CODIGO_RESERVA": "DEF456",
        "NUMERO_DE_BOLETO": "1112223334",
        "NOMBRE_DEL_PASAJERO": "GARCIA/MARIA",
        "NOMBRE_AEROLINEA": "AVIANCA",
        "TOTAL_IMPORTE": "600.00",
        "TOTAL_MONEDA": "USD",
        "FECHA_DE_EMISION": "16JAN26"
    }

@pytest.fixture
def user_admin(db):
    """Crea un usuario administrador"""
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="testpass123"
    )

@pytest.fixture
def user_agente(db):
    """Crea un usuario agente"""
    User = get_user_model()
    return User.objects.create_user(
        username="agente",
        email="agente@test.com",
        password="testpass123"
    )
