
import os
import google.generativeai as genai
from django.conf import settings
import sys

# Setup Django minimal (not strictly needed just for dot env but safe)
sys.path.append(os.getcwd())
# Try to get key directly from env as guardian.py does (assuming it worked up to the 404)
# Actually guardian.py loads django setup so env vars might come from there?
# But lets process .env manually just in case
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    # Try hardcoded path if .env load failed
    print("Trying to load .env manually")
    with open('.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY'):
                api_key = line.split('=')[1].strip()
                break

if not api_key:
    print("NO API KEY FOUND")
    sys.exit(1)

genai.configure(api_key=api_key)

print(f"Listing models for key: {api_key[:5]}...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")
