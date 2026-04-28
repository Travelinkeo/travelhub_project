import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

# Check which file is being imported
import core.ticket_parser
print(f"File location: {core.ticket_parser.__file__}")

# Get the actual source code from the FILE (not from memory)
with open(core.ticket_parser.__file__, 'r', encoding='utf-8') as f:
    file_content = f.read()

if 'ACCELYA.COM' in file_content:
    print("✅ ACCELYA.COM found in FILE on disk")
else:
    print("❌ ACCELYA.COM NOT found in FILE on disk")

# Now check what Python has loaded in memory
import inspect
try:
    source = inspect.getsource(core.ticket_parser.extract_data_from_text)
    if 'ACCELYA.COM' in source:
        print("✅ ACCELYA.COM found in LOADED code in memory")
    else:
        print("❌ ACCELYA.COM NOT found in LOADED code in memory")
        print("\n🔍 First 100 lines of loaded code:")
        for i, line in enumerate(source.split('\n')[:100], 1):
            if 'copa' in line.lower() or 'sabre' in line.lower():
                print(f"   Line {i}: {line.strip()}")
except Exception as e:
    print(f"Error getting source: {e}")
