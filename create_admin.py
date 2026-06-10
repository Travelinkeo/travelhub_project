from django.contrib.auth import get_user_model

User = get_user_model()
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@travelhub.cc", "admin123456")
    print("Superuser admin created with password: admin123456")
else:
    admin = User.objects.get(username="admin")
    admin.set_password("admin123456")
    admin.save()
    print("Admin password reset to: admin123456")
