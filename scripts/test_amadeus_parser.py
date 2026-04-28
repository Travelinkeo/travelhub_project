
import os
import sys
import re
import json

# Setup Django path needed? The parser imports 'core.parsers.base_parser'.
# Yes, safer to setup.
sys.path.append(os.getcwd())

from core.parsers.amadeus_parser import AmadeusParser

DUMP_FILE = 'XYZ/amadeus_samples/analysis_dump.txt'

def main():
    if not os.path.exists(DUMP_FILE):
        print("Dump file not found.")
        return

    with open(DUMP_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by file marker
    # ==================================================
    # FILE: sample_X.pdf
    # ==================================================
    

    sections = re.split(r'={50}\nFILE: (.+?)\n={50}\n', content)
    
    parser = AmadeusParser()

    output_path = 'XYZ/amadeus_samples/test_results.json'
    results = {}

    for i in range(1, len(sections), 2):
        filename = sections[i]
        text = sections[i+1]
        
        print(f"Analyzing {filename}...")
        try:
            parsed = parser.parse(text)
            if hasattr(parsed, 'to_dict'):
                results[filename] = parsed.to_dict()
            else:
                results[filename] = parsed
        except Exception as e:
            results[filename] = {'error': str(e)}

    with open(output_path, 'w', encoding='utf-8') as f_out:
        json.dump(results, f_out, indent=2, default=str)
    
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    main()
