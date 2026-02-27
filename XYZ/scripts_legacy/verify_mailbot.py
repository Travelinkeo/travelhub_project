import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.tasks import process_incoming_emails
import logging

# Configure logging to console
logging.basicConfig(level=logging.INFO)

print("Running process_incoming_emails task manually...")
result = process_incoming_emails()
print(f"Result: {result}")
