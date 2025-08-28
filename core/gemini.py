import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def get_gemini_model():
    """Initializes and returns the Gemini Pro model."""
    return genai.GenerativeModel('gemini-pro')

def generate_content(prompt):
    """Generates content using the Gemini model."""
    model = get_gemini_model()
    response = model.generate_content(prompt)
    return response.text
