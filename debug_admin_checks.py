import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib import admin
from django.forms.models import _get_foreign_key
from django.db import models

print("Starting Admin Check Debug...")

for model, model_admin in admin.site._registry.items():
    if hasattr(model_admin, 'inlines'):
        for inline_class in model_admin.inlines:
            try:
                # Basic initialization of inline to mimic Django's check
                inline_obj = inline_class(model, admin.site)
                # print(f"Checking Inline: {inline_obj.__class__.__name__} for Parent: {model.__name__}")
                
                # Simulate _check_relation logic
                inline_model = inline_obj.model
                fk_name = getattr(inline_obj, 'fk_name', None)
                
                for f in inline_model._meta.fields:
                    if isinstance(f, models.ForeignKey):
                        # print(f"  Field: {f.name}, Remote Model: {f.remote_field.model}")
                        if isinstance(f.remote_field.model, str):
                            print(f"!!! FOUND UNRESOLVED FOREIGN KEY !!!")
                            print(f"Parent Model: {model.__name__}")
                            print(f"Inline Model: {inline_model.__name__}")
                            print(f"Field Name: {f.name}")
                            print(f"Remote Model (String): {f.remote_field.model}")
                            print("-" * 40)
            except Exception as e:
                # print(f"Error checking {inline_class}: {e}")
                pass

print("Debug Finished.")
