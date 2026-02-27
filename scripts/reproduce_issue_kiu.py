
import re
import unittest

def parse_kiu_flight_segments(itinerary_text):
    vuelos = []
    if not itinerary_text: return vuelos
    
    # Regex Standards (Copied from core/ticket_parser.py)
    patterns = [
        re.compile(r'(\d{1,2}[A-Z]{3}\d{0,2})\s+([A-Z0-9]{2,3}\s*\d{1,4}[A-Z]?)\s+([A-Z]{3})\s*(\d{4})\s*-?\s*([A-Z]{3})\s*(\d{4})(.*)'),
        re.compile(r'(\d{1,2}[A-Z]{3}\d{0,2})\s+([A-Z0-9]{2,3}\s*\d{1,4}[A-Z]?)\s+([A-Z]{3})\s+(\d{4})\s+([A-Z]{3})\s+(\d{4})(.*)') 
    ]
    conviasa_pattern = re.compile(r'^([A-Z \.]+)\s+([A-Z0-9]{2}\s*\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4})(.*)')

    lines = [l.strip() for l in itinerary_text.split('\n') if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        matched = False
        
        # Strip HTML tags for the test (Simulating the fix)
        # Uncomment the next line to test the fix
        # line = re.sub(r'<[^>]+>', '', line).strip()
        
        print(f"Processing line: {line}")

        for p in patterns:
            m = p.search(line)
            if m:
                print("Matched Standard Pattern")
                vuelos.append("MATCH_STANDARD")
                matched = True
                break
        
        if not matched:
            m = conviasa_pattern.search(line)
            if m:
                print("Matched Conviasa Pattern")
                vuelos.append("MATCH_CONVIASA")
                matched = True
        
        if not matched:
            print("NO MATCH")
            
        i += 1
    return vuelos

if __name__ == "__main__":
    # The problematic string from the user
    messy_text = "<B>CARACAS </B>5R1327 T <B>17FEB 0800</B> <B>0840</B> TLOW 23K OK\n<B> BARQUISIMETO </B>"
    
    print("--- Testing with Messy Text ---")
    results = parse_kiu_flight_segments(messy_text)
    print(f"Results: {results}")
    
    print("\n--- Testing with Cleaned Text ---")
    clean_text = re.sub(r'<[^>]+>', '', messy_text)
    print(f"Cleaned Text: {clean_text}")
    results_clean = parse_kiu_flight_segments(clean_text)
    print(f"Results: {results_clean}")
