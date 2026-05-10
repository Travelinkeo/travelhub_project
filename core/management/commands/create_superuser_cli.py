from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import secrets

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser from CLI (secure - no web endpoint)'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=False, help='If not provided, a random password is generated')

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            raise CommandError('A superuser already exists. Refusing to create another.')

        username = options['username']
        email = options['email']
        password = options['password'] or secrets.token_urlsafe(16)

        user = User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created.'))
        if not options['password']:
            self.stdout.write(f'Generated password: {password}')
            self.stdout.write(self.style.WARNING('Save this password - it will not be shown again.'))
