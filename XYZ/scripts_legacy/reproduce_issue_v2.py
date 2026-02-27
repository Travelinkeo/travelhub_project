
import re
import logging
from core.parsers.console_parser import ConsoleParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_new_kiu_format():
    kiu_text = """1  V01014T 01DEC MO CCSPMV SS1  0600 0650
2   V01015T 02DEC TU PMVCCS SS1  0730 0820"""
    
    print(f"Testing text:\n{kiu_text}\n")
    
    parser = ConsoleParser()
    result = parser.parse(kiu_text)
    
    print("Result:")
    print(result)
    
    if 'error' in result:
        print("\nFAIL: Parsing failed.")
    elif len(result.get('vuelos', [])) == 2:
        print("\nSUCCESS: Parsed 2 flights.")
        for v in result['vuelos']:
            print(v)
    else:
        print(f"\nPARTIAL: Parsed {len(result.get('vuelos', []))} flights (expected 2).")

if __name__ == "__main__":
    test_new_kiu_format()
