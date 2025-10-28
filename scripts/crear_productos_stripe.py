"""
Script para crear productos y precios en Stripe.
Ejecutar: python scripts/crear_productos_stripe.py
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')

try:
    import stripe
except ImportError:
    print("Error: stripe no está instalado")
    print("Instalar con: pip install stripe")
    sys.exit(1)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

if not stripe.api_key or 'TU_CLAVE' in stripe.api_key:
    print("Error: STRIPE_SECRET_KEY no configurada en .env")
    print("Obtener de: https://dashboard.stripe.com/test/apikeys")
    sys.exit(1)

print("Creando productos en Stripe...")
print("=" * 60)

# Crear producto BASIC
print("\n1. Creando plan BASIC...")
try:
    basic_product = stripe.Product.create(
        name="TravelHub Basic",
        description="Plan Básico - 3 usuarios, 200 ventas/mes"
    )
    basic_price = stripe.Price.create(
        product=basic_product.id,
        unit_amount=2900,  # $29.00 en centavos
        currency="usd",
        recurring={"interval": "month"}
    )
    print("BASIC creado exitosamente")
    print(f"  Product ID: {basic_product.id}")
    print(f"  Price ID: {basic_price.id}")
    print(f"  Agregar a .env: STRIPE_PRICE_ID_BASIC={basic_price.id}")
except Exception as e:
    print(f"Error: {e}")

# Crear producto PRO
print("\n2. Creando plan PRO...")
try:
    pro_product = stripe.Product.create(
        name="TravelHub Pro",
        description="Plan Profesional - 10 usuarios, 1000 ventas/mes"
    )
    pro_price = stripe.Price.create(
        product=pro_product.id,
        unit_amount=9900,  # $99.00 en centavos
        currency="usd",
        recurring={"interval": "month"}
    )
    print("PRO creado exitosamente")
    print(f"  Product ID: {pro_product.id}")
    print(f"  Price ID: {pro_price.id}")
    print(f"  Agregar a .env: STRIPE_PRICE_ID_PRO={pro_price.id}")
except Exception as e:
    print(f"Error: {e}")

# Crear producto ENTERPRISE
print("\n3. Creando plan ENTERPRISE...")
try:
    enterprise_product = stripe.Product.create(
        name="TravelHub Enterprise",
        description="Plan Enterprise - Usuarios ilimitados, ventas ilimitadas"
    )
    enterprise_price = stripe.Price.create(
        product=enterprise_product.id,
        unit_amount=29900,  # $299.00 en centavos
        currency="usd",
        recurring={"interval": "month"}
    )
    print("ENTERPRISE creado exitosamente")
    print(f"  Product ID: {enterprise_product.id}")
    print(f"  Price ID: {enterprise_price.id}")
    print(f"  Agregar a .env: STRIPE_PRICE_ID_ENTERPRISE={enterprise_price.id}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("Productos creados exitosamente!")
print("\nPróximos pasos:")
print("1. Copiar los Price IDs a tu archivo .env")
print("2. Reiniciar el servidor Django")
print("3. Probar checkout en /api/billing/checkout/")
