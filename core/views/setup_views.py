from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import os

User = get_user_model()

@csrf_exempt
@require_http_methods(["POST"])
def create_superuser(request):
    """
    Endpoint temporal para crear superusuario en producción.
    POST /api/setup/create-superuser/
    Body: {"username": "admin", "email": "admin@example.com", "password": "tu_password"}
    """
    # Solo permitir si DEBUG=True o SECRET_SETUP_KEY coincide
    setup_key = request.POST.get('setup_key') or request.headers.get('X-Setup-Key')
    expected_key = os.getenv('SECRET_SETUP_KEY', 'CHANGE_ME_IN_PRODUCTION')
    
    if not (os.getenv('DEBUG') == 'True' or setup_key == expected_key):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Verificar si ya existe un superusuario
    if User.objects.filter(is_superuser=True).exists():
        return JsonResponse({'error': 'Superuser already exists'}, status=400)
    
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
