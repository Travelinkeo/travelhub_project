import google.generativeai as genai
import os

# Set API Key directly for testing
os.environ['GEMINI_API_KEY'] = 'AIzaSyAnQCcq0Hm6QUcdV8KCwtLG5QvvrNvrKyo'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

print("Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
