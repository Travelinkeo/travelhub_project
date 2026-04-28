import sys
import os
import django
import re

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.sabre_parser import SabreParser

def test_sabre_split():
    parser = SabreParser()
    
    # CASE 1: Date at start of string (The reported bug)
    text_start = "09MAR26 AV 120 BOG -> MIA\n10MAR26 AV 121 MIA -> BOG"
    
    # CASE 2: Date after newline (Standard)
    text_newline = "\n09MAR26 AV 120 BOG -> MIA\n10MAR26 AV 121 MIA -> BOG"
    
    print("--- TESTING SABRE DATE SPLIT LOGIC ---")
    
    # We must use similar logic to _parse_flights.
    # The regex in the file is now: r'((?:\n|^)\s*\d{1,2}\s*[a-zA-Z]{3,}\s*\d{2,4})'
    # Wait, in the file I updated, I referenced p_block.
    # Let's import the method or verify via splitting here using the SAME regex.
    
    regex = r'((?:\n|^)\s*\d{1,2}\s*[a-zA-Z]{3,}\s*\d{2,4})'
    
    print(f"Regex: {regex}")
    
    print("\nCase 1: '09MAR...' (Start of String)")
    split_1 = re.split(regex, text_start)
    print(f"Split Result: {split_1}")
    if len(split_1) > 1 and "09MAR" in split_1[1]:
        print("[PASS] Caught first date!")
    else:
        print("[FAIL] Missed first date.")

    print("\nCase 2: '\\n09MAR...' (Newline)")
    split_2 = re.split(regex, text_newline)
    print(f"Split Result: {split_2}")
    if len(split_2) > 1 and "09MAR" in split_2[1].strip():
        print("[PASS] Caught first date!")
    else:
        print("[FAIL] Missed first date.")

if __name__ == '__main__':
    test_sabre_split()
