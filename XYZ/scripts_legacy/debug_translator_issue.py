
import os
import django
import sys
import logging

# Setup Django
sys.path.append(r'c:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.itinerary_translator import ItineraryTranslator
from core.parsers.console_parser import ConsoleParser

def test_issue():
    text = "1 ES862 B 10JAN SA STDCCS SS1   1410 1510"
    print(f"Testing text 1 (Original): '{text}'")
    
    # 1. Test Parser directly
    parser = ConsoleParser()
    parsed = parser.parse(text)
    print("Result 1:", parsed.get('source_system'), len(parsed.get('vuelos', [])))

    text2 = "1 ES 862 B 10JAN SA STDCCS SS1   1410 1510"
    print(f"\nTesting text 2 (Spaced): '{text2}'")
    parsed2 = parser.parse(text2)
    print("Result 2:", parsed2.get('source_system'), len(parsed2.get('vuelos', [])))
    
    # 2. Test Translator
    print("\n--- ItineraryTranslator Result (Original) ---")
    translator = ItineraryTranslator()
    result = translator.translate_itinerary(text, 'KIU')
    print("\n--- ItineraryTranslator Result ---")
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Flights found: {len(result.get('structured_data', []))}")
        print(result.get('structured_data'))

if __name__ == '__main__':
    test_issue()
