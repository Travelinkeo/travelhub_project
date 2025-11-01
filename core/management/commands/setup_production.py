from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Setup production: migrate + collectstatic'

    def handle(self, *args, **options):
        self.stdout.write('Running migrations...')
        call_command('migrate', '--noinput', verbosity=2)
        
        self.stdout.write('Collecting static files...')
        call_command('collectstatic', '--noinput', verbosity=1)
        
        self.stdout.write(self.style.SUCCESS('Production setup complete!'))
