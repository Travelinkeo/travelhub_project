from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import os
import json

User = get_user_model()

@csrf_exempt
def create_superuser(request):
    """
    Endpoint temporal para crear superusuario en producción.
    POST /api/setup/create-superuser/
    Body: {"username": "admin", "email": "admin@example.com", "password": "tu_password"}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Solo permitir si DEBUG=True
    debug_mode = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    if not debug_mode:
        return JsonResponse({'error': 'Unauthorized - DEBUG must be True'}, status=403)
    
    # Verificar si ya existe un superusuario
    if User.objects.filter(is_superuser=True).exists():
        return JsonResponse({'error': 'Superuser already exists'}, status=400)
    
    # Obtener datos del POST o JSON
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            username = data.get('username', 'admin')
            email = data.get('email', 'admin@travelhub.com')
            password = data.get('password')
        except:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    else:
        username = request.POST.get('username', 'admin')
        email = request.POST.get('email', 'admin@travelhub.com')
        password = request.POST.get('password')
    
    if not password:
        return JsonResponse({'error': 'Password is required'}, status=400)
    
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        return JsonResponse({
            'success': True,
            'message': 'Superuser created successfully',
            'username': user.username,
            'email': user.email
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
