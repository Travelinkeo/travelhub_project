"""Cambio de planes (upgrade/downgrade)."""
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from django.conf import settings
import os

try:
    import stripe
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_AVAILABLE = bool(stripe.api_key)
except ImportError:
    STRIPE_AVAILABLE = False

from core.views.billing_views import PLAN_CONFIG


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def change_plan(request):
    """Cambia el plan de la agencia (upgrade o downgrade)."""
    if not STRIPE_AVAILABLE:
        return Response({'error': 'Stripe no configurado'}, status=503)
    
    nuevo_plan = request.data.get('plan')
    if nuevo_plan not in PLAN_CONFIG or nuevo_plan == 'FREE':
        return Response({'error': 'Plan inválido'}, status=400)
    
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        plan_actual = agencia.plan
        
        # Verificar si ya tiene este plan
        if plan_actual == nuevo_plan:
            return Response({'error': 'Ya tienes este plan'}, status=400)
        
        # Si no tiene suscripción, crear checkout
        if not agencia.stripe_subscription_id:
            return Response({
                'error': 'No tienes suscripción activa',
                'action': 'create_checkout'
            }, status=400)
        
        # Obtener la suscripción actual
        subscription = stripe.Subscription.retrieve(agencia.stripe_subscription_id)
        
        # Actualizar el plan con proration automática
        nuevo_price_id = PLAN_CONFIG[nuevo_plan]['stripe_price_id']
        
        stripe.Subscription.modify(
            agencia.stripe_subscription_id,
            items=[{
                'id': subscription['items']['data'][0].id,
                'price': nuevo_price_id,
            }],
            proration_behavior='create_prorations',  # Proration automática
        )
        
        # Actualizar en la base de datos
        agencia.plan = nuevo_plan
        agencia.actualizar_limites_por_plan()
        agencia.save()
        
        # Determinar si es upgrade o downgrade
        plan_order = {'FREE': 0, 'BASIC': 1, 'PRO': 2, 'ENTERPRISE': 3}
        es_upgrade = plan_order[nuevo_plan] > plan_order[plan_actual]
        
        return Response({
            'message': f'Plan {"actualizado" if es_upgrade else "cambiado"} exitosamente',
            'plan_anterior': plan_actual,
            'plan_nuevo': nuevo_plan,
            'tipo': 'upgrade' if es_upgrade else 'downgrade',
            'proration': 'Se aplicará un cargo/crédito proporcional en tu próxima factura',
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def preview_plan_change(request):
    """Previsualiza el costo de cambiar de plan."""
    if not STRIPE_AVAILABLE:
        return Response({'error': 'Stripe no configurado'}, status=503)
    
    nuevo_plan = request.data.get('plan')
    if nuevo_plan not in PLAN_CONFIG:
        return Response({'error': 'Plan inválido'}, status=400)
    
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        plan_actual = agencia.plan
        
        if not agencia.stripe_subscription_id:
            return Response({
                'plan_actual': PLAN_CONFIG[plan_actual],
                'plan_nuevo': PLAN_CONFIG[nuevo_plan],
                'costo_inmediato': PLAN_CONFIG[nuevo_plan]['price'],
                'mensaje': 'Costo completo del nuevo plan (sin suscripción activa)'
            })
        
        # Obtener preview de Stripe
        subscription = stripe.Subscription.retrieve(agencia.stripe_subscription_id)
        nuevo_price_id = PLAN_CONFIG[nuevo_plan]['stripe_price_id']
        
        # Crear preview de la factura
        upcoming_invoice = stripe.Invoice.upcoming(
            customer=agencia.stripe_customer_id,
            subscription=agencia.stripe_subscription_id,
            subscription_items=[{
                'id': subscription['items']['data'][0].id,
                'price': nuevo_price_id,
            }],
        )
        
        return Response({
            'plan_actual': {
                'code': plan_actual,
                'name': PLAN_CONFIG[plan_actual]['name'],
                'price': PLAN_CONFIG[plan_actual]['price'],
            },
            'plan_nuevo': {
                'code': nuevo_plan,
                'name': PLAN_CONFIG[nuevo_plan]['name'],
                'price': PLAN_CONFIG[nuevo_plan]['price'],
            },
            'proration': {
                'amount': upcoming_invoice.amount_due / 100,
                'currency': upcoming_invoice.currency.upper(),
                'fecha_cargo': upcoming_invoice.period_end,
            },
            'mensaje': 'El cambio se aplicará inmediatamente con ajuste proporcional'
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def downgrade_to_free(request):
    """Downgrade a plan FREE (cancela suscripción)."""
    if not STRIPE_AVAILABLE:
        return Response({'error': 'Stripe no configurado'}, status=503)
    
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        
        if agencia.plan == 'FREE':
            return Response({'error': 'Ya estás en el plan FREE'}, status=400)
        
        if not agencia.stripe_subscription_id:
            # Solo actualizar en BD
            agencia.plan = 'FREE'
            agencia.actualizar_limites_por_plan()
            agencia.save()
            return Response({'message': 'Plan cambiado a FREE'})
        
        # Cancelar suscripción en Stripe al final del período
        stripe.Subscription.modify(
            agencia.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        return Response({
            'message': 'Tu suscripción se cancelará al final del período actual',
            'plan_actual': agencia.plan,
            'acceso_hasta': 'Final del período de facturación',
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)
