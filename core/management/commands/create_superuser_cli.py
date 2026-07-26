import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    """Command."""

    help = "Create a superuser from CLI (secure - no web endpoint)"

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument(
            "--password", required=False, help="If not provided, a random password is generated"
        )

    def handle(self, *args, **options):
        """handle."""
        if User.objects.filter(is_superuser=True).exists():
            raise CommandError("A superuser already exists. Refusing to create another.")

        username = options["username"]
        email = options["email"]
        password = options["password"] or secrets.token_urlsafe(16)

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created.'))
        if not options["password"]:
            self.stdout.write(f"Generated password: {password}")
            self.stdout.write(
                self.style.WARNING("Save this password - it will not be shown again.")
            )
