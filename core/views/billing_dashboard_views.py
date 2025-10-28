"""Dashboard de billing - Facturas, historial, métricas."""
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


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_invoices(request):
    """Obtiene el historial de facturas de la agencia."""
    if not STRIPE_AVAILABLE:
        return Response({'error': 'Stripe no configurado'}, status=503)
    
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        
        if not agencia.stripe_customer_id:
            return Response({'invoices': []})
        
        # Obtener facturas de Stripe
        invoices = stripe.Invoice.list(
            customer=agencia.stripe_customer_id,
            limit=10
        )
        
        invoices_data = []
        for invoice in invoices.data:
            invoices_data.append({
                'id': invoice.id,
                'amount': invoice.amount_paid / 100,  # Convertir de centavos
                'currency': invoice.currency.upper(),
                'status': invoice.status,
                'date': invoice.created,
                'pdf_url': invoice.invoice_pdf,
                'hosted_url': invoice.hosted_invoice_url,
            })
        
        return Response({'invoices': invoices_data})
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_payment_method(request):
    """Obtiene el método de pago actual."""
    if not STRIPE_AVAILABLE:
        return Response({'error': 'Stripe no configurado'}, status=503)
    
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        
        if not agencia.stripe_customer_id:
            return Response({'payment_method': None})
        
        # Obtener métodos de pago
        payment_methods = stripe.PaymentMethod.list(
            customer=agencia.stripe_customer_id,
            type='card'
        )
        
        if payment_methods.data:
            pm = payment_methods.data[0]
            return Response({
                'payment_method': {
                    'brand': pm.card.brand,
                    'last4': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year,
                }
            })
        
        return Response({'payment_method': None})
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_usage_stats(request):
    """Obtiene estadísticas de uso del plan actual."""
    try:
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return Response({'error': 'No perteneces a ninguna agencia'}, status=404)
        
        agencia = usuario_agencia.agencia
        
        # Calcular porcentajes de uso
        usuarios_porcentaje = (agencia.usuarios.filter(activo=True).count() / agencia.limite_usuarios * 100) if agencia.limite_usuarios > 0 else 0
        ventas_porcentaje = (agencia.ventas_mes_actual / agencia.limite_ventas_mes * 100) if agencia.limite_ventas_mes > 0 else 0
        
        return Response({
            'usuarios': {
                'usado': agencia.usuarios.filter(activo=True).count(),
                'limite': agencia.limite_usuarios,
                'porcentaje': round(usuarios_porcentaje, 1),
                'disponible': agencia.limite_usuarios - agencia.usuarios.filter(activo=True).count(),
            },
            'ventas': {
                'usado': agencia.ventas_mes_actual,
                'limite': agencia.limite_ventas_mes,
                'porcentaje': round(ventas_porcentaje, 1),
                'disponible': agencia.limite_ventas_mes - agencia.ventas_mes_actual,
            },
            'plan': {
                'code': agencia.plan,
                'name': agencia.get_plan_display(),
            }
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)
