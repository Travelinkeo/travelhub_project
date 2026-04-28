import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()
from apps.crm.models_freelancer import FreelancerProfile
print(f"Total Freelancers: {FreelancerProfile.objects.count()}")
for f in FreelancerProfile.objects.all():
    print(f"Freelancer: {f.usuario.username}, Agencia: {f.agencia}, Comision: {f.porcentaje_comision}%")
