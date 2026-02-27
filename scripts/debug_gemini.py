import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f"Key loaded: {bool(api_key)}")

if api_key:
    genai.configure(api_key=api_key)
    try:
        print("Listing models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                
        print("\nTesting Generation (gemini-1.5-flash)...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")
else:
    print("No API Key found.")
