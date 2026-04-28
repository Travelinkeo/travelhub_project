
import os
import sys
import django
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.agencia import Agencia
from core.services.stripe_service import StripeService

from django.contrib.auth.models import User

def test_billing_logic():
    print("💳 Iniciando pruebas de Lógica de Facturación SaaS...")
    
    # 1. Crear Usuario y Agencia de Prueba
    try:
        user, _ = User.objects.get_or_create(username='billing_tester', defaults={'email':'tester@billing.com'})
        
        agencia, created = Agencia.objects.get_or_create(
            nombre="Test Agency Billing",
            defaults={
                'email_principal': 'billing@test.com',
                'plan': 'FREE',
                'propietario': user
            }
        )
        if not created:
             agencia.propietario = user
        
        # Resetear estado
        agencia.plan = 'FREE'
        agencia.stripe_subscription_id = ''
        agencia.actualizar_limites_por_plan()
        agencia.save()
        
        print(f"   Agencia creada: {agencia.nombre} (Plan: {agencia.plan}, Ventas Límite: {agencia.limite_ventas_mes})")
    except Exception as e:
        print(f"❌ Error creando agencia de prueba: {e}")
        return

    # 2. Probar Creación de Checkout (Mock Stripe)
    print("\n[1] Probando creación de Checkout Session...")
    with patch('stripe.Customer.create') as mock_customer_create, \
         patch('stripe.checkout.Session.create') as mock_session_create:
        
        mock_customer_create.return_value = MagicMock(id='cus_test123')
        mock_session_create.return_value = MagicMock(url='https://checkout.stripe.com/test', id='cs_test_abc')
        
        try:
            url = StripeService.create_checkout_session(
                agencia=agencia,
                price_id='price_fake_pro',
                success_url='http://ok',
                cancel_url='http://cancel'
            )
            print(f"   ✅ URL Generada: {url}")
            
            # Verificar que se guardó el customer id
            agencia.refresh_from_db()
            if agencia.stripe_customer_id == 'cus_test123':
                print("   ✅ Customer ID guardado en Agencia")
            else:
                print(f"   ❌ Customer ID no guardado: {agencia.stripe_customer_id}")
                
        except Exception as e:
            print(f"   ❌ Error en create_checkout_session: {e}")

    # 3. Probar Webhook: Upgrade a PRO
    print("\n[2] Probando Webhook (Upgrade a PRO)...")
    mock_event = {
        'type': 'checkout.session.completed',
        'data': {
            'object': {
                'subscription': 'sub_pro_123',
                'metadata': {
                    'agencia_id': agencia.id,
                    'plan': 'PRO'
                }
            }
        }
    }
    
    try:
        StripeService.handle_webhook(mock_event)
        
        agencia.refresh_from_db()
        if agencia.plan == 'PRO' and agencia.stripe_subscription_id == 'sub_pro_123':
            print(f"   ✅ Agencia actualizada a PRO (Límite Ventas: {agencia.limite_ventas_mes})")
            if agencia.limite_ventas_mes == 1000:
                 print("   ✅ Límites actualizados correctamente (1000)")
            else:
                 print(f"   ❌ Error en límites: {agencia.limite_ventas_mes}")
        else:
             print(f"   ❌ Agencia no se actualizó: Plan={agencia.plan}")

    except Exception as e:
        print(f"   ❌ Error en handle_webhook: {e}")

    # 4. Probar Webhook: Cancelación
    print("\n[3] Probando Webhook (Cancelación)...")
    mock_cancel_event = {
        'type': 'customer.subscription.deleted',
        'data': {
            'object': {
                'id': 'sub_pro_123'
            }
        }
    }
    
    try:
        StripeService.handle_webhook(mock_cancel_event)
        
        agencia.refresh_from_db()
        if agencia.plan == 'FREE' and agencia.stripe_subscription_id == '':
            print("   ✅ Agencia revertida a FREE tras cancelación")
        else:
            print(f"   ❌ Agencia no revertida correctamente: Plan={agencia.plan}")
            
    except Exception as e:
        print(f"   ❌ Error en handle_webhook (cancel): {e}")

if __name__ == '__main__':
    test_billing_logic()
