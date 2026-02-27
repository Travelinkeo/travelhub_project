
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_kiu_raw(plain_text):
    print(f"Testing text: '{plain_text}'")
    
    # Regex from ticket_parser.py
    raw_kiu_pattern = r'^\s*\d+\s+[A-Z0-9]{2}\d+\s+[A-Z]\s+\d{2}[A-Z]{3}'
    
    if re.search(raw_kiu_pattern, plain_text, re.MULTILINE):
        print("MATCH: Raw KIU pattern detected.")
        
        # Simulate KIUParser logic for raw lines
        # In ticket_parser.py we call KIUParser().parse(plain_text)
        # Let's see what KIUParser does with this.
        
        from core.parsers.kiu_parser import KIUParser
        parser = KIUParser()
        try:
            result = parser.parse(plain_text)
            print("\nParsing Result:")
            print(result.to_dict())
        except Exception as e:
            print(f"\nParsing Error: {e}")
            
    else:
        print("NO MATCH: Raw KIU pattern NOT detected.")

if __name__ == "__main__":
    # The problematic itinerary
    kiu_text = "1 5R300 S 30NOV SU CCSPMV HK1 0800 0840"
    parse_kiu_raw(kiu_text)
