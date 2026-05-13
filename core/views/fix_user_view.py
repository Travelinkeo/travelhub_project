from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse


@user_passes_test(lambda u: u.is_superuser)
def fix_my_user(request):
    """Quita superuser al usuario actual y lo deja como staff."""
    u = request.user
    u.is_superuser = False
    u.is_staff = True
    u.save()
    return HttpResponse(f"OK. {u.username} ahora es staff (no superuser). Recarga la pagina.")
