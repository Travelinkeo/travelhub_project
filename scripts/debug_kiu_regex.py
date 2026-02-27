import re

text = """SAN ANTONIO V01187 G 2FEB 0850 0950 GPROMO 23K OK
CARACAS
PARA MAYOR INFORMACION INGRESAR AL SIGUIENTE LINK HTTP://WWW.CONVIASA.AERO/ES/"""

lines = text.splitlines()

# The regex from the parser
flight_pattern = r'^\s*([A-ZÁÉÍÓÚ ]+?)\s+([A-Z0-9]{2}\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4})\s+(.+)$'

print(f"Testing regex against {len(lines)} lines")

for i, line in enumerate(lines):
    line = line.strip()
    print(f"\nLine {i}: '{line}'")
    
    match = re.search(flight_pattern, line)
    if match:
        print("✅ MATCH!")
        print(f"  Origin: '{match.group(1)}'")
        print(f"  Flight: '{match.group(2)}'")
        print(f"  Class: '{match.group(3)}'")
        print(f"  Date: '{match.group(4)}'")
        print(f"  Dep: '{match.group(5)}'")
        print(f"  Arr: '{match.group(6)}'")
        print(f"  Rest: '{match.group(7)}'")
    else:
        print("❌ NO MATCH")
        # Try to debug why
        part_match = re.search(r'([A-Z0-9]{2}\d{3,4})', line)
        if part_match:
            print(f"  Found potential flight number: {part_match.group(1)}")
        else:
            print("  No flight number found pattern-wise")

