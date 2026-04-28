
import os
import sys
import django
import vertexai
from vertexai.preview.generative_models import GenerativeModel

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.conf import settings

def verify_text_gen():
    print("📝 Verifying Vertex AI Text Generation (Gemini Pro)...")
    
    try:
        project_id = settings.GCP_PROJECT_ID
        location = settings.GCP_LOCATION
        print(f"   Project: {project_id}, Location: {location}")
        
        vertexai.init(project=project_id, location=location)
        
        model = GenerativeModel("gemini-pro")
        
        print("   Sending prompt: 'Write a tagline for a travel agency'")
        response = model.generate_content("Write a tagline for a travel agency")
        
        if response.text:
            print(f"   ✅ Success! Response: {response.text}")
        else:
            print("   ❌ Empty response.")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verify_text_gen()
