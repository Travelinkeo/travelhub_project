import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

# Check which file is being imported
import core.ticket_parser
print(f"📁 ticket_parser.py location: {core.ticket_parser.__file__}")

# Check if Copa detection code exists
import inspect
source = inspect.getsource(core.ticket_parser.extract_data_from_text)

# Look for Copa detection
if 'COPA_SPRK' in source and 'ACCELYA.COM' in source:
    print("✅ Copa detection code FOUND in loaded module")
    print("✅ Code includes ACCELYA.COM marker")
else:
    print("❌ Copa detection code NOT FOUND in loaded module")
    print("❌ This means Python is loading OLD code from somewhere")

# Check line numbers
lines = source.split('\n')
for i, line in enumerate(lines[:50], 1):
    if 'COPA' in line.upper() or 'ACCELYA' in line.upper():
        print(f"   Line {i}: {line.strip()}")
