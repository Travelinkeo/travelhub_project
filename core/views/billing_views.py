"""
Vistas para facturación y gestión de planes SaaS con Stripe.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from core.models.agencia import Agencia
import os

# Stripe se importa solo si está configurado
try:
    import stripe
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_AVAILABLE = bool(stripe.api_key)
except ImportError:
    STRIPE_AVAILABLE = False


# Configuración de planes y precios
PLAN_CONFIG = {
    'FREE': {
        'name': 'Gratuito (Trial 30 días)',
        'price': 0,
        'stripe_price_id': None,
        'usuarios': 1,
        'ventas': 50,
        'features': [
            '1 usuario',
            '50 ventas/mes',
            'Funcionalidad básica',
            'Soporte por email',
        ]
    },
    'BASIC': {
        'name': 'Básico',
        'price': 29,
        'stripe_price_id': os.getenv('STRIPE_PRICE_ID_BASIC', ''),
        'usuarios': 3,
        'ventas': 200,
        'features': [
            '3 usuarios',
            '200 ventas/mes',
            'Todas las funcionalidades',
            'Soporte por email',
            'Reportes básicos',
        ]
    },
    'PRO': {
        'name': 'Profesional',
        'price': 99,
        'stripe_price_id': os.getenv('STRIPE_PRICE_ID_PRO', ''),
        'usuarios': 10,
        'ventas': 1000,
        'features': [
            '10 usuarios',
            '1000 ventas/mes',
            'Todas las funcionalidades',
            'Integraciones API',
            'Reportes avanzados',
            'Soporte prioritario',
        ]
    },
    'ENTERPRISE': {
        'name': 'Enterprise',
        'price': 299,
        'stripe_price_id': os.getenv('STRIPE_PRICE_ID_ENTERPRISE', ''),
        'usuarios': 999999,
        'ventas': 999999,
        'features': [
            'Usuarios ilimitados',
            'Ventas ilimitadas',
            'Todas las funcionalidades',
            'Servidor dedicado',
            'Personalización',
            'Soporte 24/7',
            'Onboarding personalizado',
        ]
    },
}


@api_view(['GET'])
@permission_classes([AllowAny])
def get_plans(request):
    """Obtiene la lista de planes disponibles."""
    return Response({
        'plans': PLAN_CONFIG,
        'stripe_available': STRIPE_AVAILABLE,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_subscription(request):
    """Obtiene la suscripción actual del usuario."""
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        plan_info = PLAN_CONFIG.get(agencia.plan, PLAN_CONFIG['FREE'])
        
        return Response({
            'agencia': {
                'id': agencia.id,
                'nombre': agencia.nombre,
                'es_demo': agencia.es_demo,
            },
            'plan': {
                'code': agencia.plan,
                'name': plan_info['name'],
                'price': plan_info['price'],
                'features': plan_info['features'],
            },
            'usage': {
                'usuarios': {
                    'usado': agencia.usuarios.filter(activo=True).count(),
                    'limite': agencia.limite_usuarios,
                },
                'ventas': {
                    'usado': agencia.ventas_mes_actual,
                    'limite': agencia.limite_ventas_mes,
                },
            },
            'stripe': {
                'customer_id': agencia.stripe_customer_id,
                'subscription_id': agencia.stripe_subscription_id,
            },
            'dates': {
                'inicio_plan': agencia.fecha_inicio_plan,
                'fin_trial': agencia.fecha_fin_trial,
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    # DRF con JWT debería bypass CSRF automáticamente
    """Crea una sesión de checkout de Stripe."""
    if not STRIPE_AVAILABLE:
        return Response({
            'error': 'Stripe no está configurado. Contacta al administrador.'
        }, status=503)
    
    plan = request.data.get('plan')
    if plan not in PLAN_CONFIG or plan == 'FREE':
        return Response({'error': 'Plan inválido'}, status=400)
    
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        plan_config = PLAN_CONFIG[plan]
        
        # Crear o recuperar customer de Stripe
        if not agencia.stripe_customer_id:
            customer = stripe.Customer.create(
                email=agencia.email_principal,
                name=agencia.nombre,
                metadata={'agencia_id': agencia.id}
            )
            agencia.stripe_customer_id = customer.id
            agencia.save(update_fields=['stripe_customer_id'])
        
        # Crear sesión de checkout
        checkout_session = stripe.checkout.Session.create(
            customer=agencia.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan_config['stripe_price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/billing/success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/billing/cancel/'),
            metadata={
                'agencia_id': agencia.id,
                'plan': plan,
            }
        )
        
        return Response({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def stripe_webhook(request):
    """Webhook para eventos de Stripe."""
    if not STRIPE_AVAILABLE:
        return Response({'error': 'Stripe no configurado'}, status=503)
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return Response({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return Response({'error': 'Invalid signature'}, status=400)
    
    # Manejar eventos
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        agencia_id = session['metadata'].get('agencia_id')
        plan = session['metadata'].get('plan')
        
        if agencia_id and plan:
            try:
                agencia = Agencia.objects.get(id=agencia_id)
                agencia.plan = plan
                agencia.stripe_subscription_id = session.get('subscription')
                agencia.actualizar_limites_por_plan()
                agencia.save()
            except Agencia.DoesNotExist:
                pass
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        try:
            agencia = Agencia.objects.get(stripe_subscription_id=subscription['id'])
            agencia.plan = 'FREE'
            agencia.actualizar_limites_por_plan()
            agencia.save()
        except Agencia.DoesNotExist:
            pass
    
    return Response({'status': 'success'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancela la suscripción actual."""
    if not STRIPE_AVAILABLE:
        return Response({'error': 'Stripe no configurado'}, status=503)
    
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        
        if not agencia.stripe_subscription_id:
            return Response({'error': 'No tienes suscripción activa'}, status=400)
        
        # Cancelar en Stripe
        stripe.Subscription.delete(agencia.stripe_subscription_id)
        
        # Actualizar agencia
        agencia.plan = 'FREE'
        agencia.stripe_subscription_id = ''
        agencia.actualizar_limites_por_plan()
        agencia.save()
        
        return Response({
            'message': 'Suscripción cancelada exitosamente',
            'plan': 'FREE'
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)
