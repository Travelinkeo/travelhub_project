import re

def _parse_kiu_flight_segments(itinerary_text: str):
    vuelos = []
    if not itinerary_text:
        return vuelos
        
    print(f"DEBUG INPUT:\n{itinerary_text}\n---")

    # Regex Standards
    patterns = [
        # 1. Standard: 29ENE26 AV 09V BLA0600 - CCS0645
        re.compile(r'(\d{1,2}[A-Z]{3}\d{0,2})\s+([A-Z0-9]{2,3}\s*\d{1,4}[A-Z]?)\s+([A-Z]{3})\s*(\d{4})\s*-?\s*([A-Z]{3})\s*(\d{4})(.*)'),
        # 2. Spaced: 29ENE26 9V 1234 BLA 0800 CCS 0900
        re.compile(r'(\d{1,2}[A-Z]{3}\d{0,2})\s+([A-Z0-9]{2,3}\s*\d{1,4}[A-Z]?)\s+([A-Z]{3})\s+(\d{4})\s+([A-Z]{3})\s+(\d{4})(.*)') 
    ]
    
    # Regex Conviasa/Legacy: SAN ANTONIO V01187 G 2FEB ... o CARACAS ES 891 ...
    # G1: Org, G2: Flt (con espacio opcional), G3: Class, G4: Date, G5: Dep, G6: Arr
    conviasa_pattern = re.compile(r'^([A-Z \.]+)\s+([A-Z0-9]{2}\s*\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4})(.*)')

    lines = [l.strip() for l in itinerary_text.split('\n') if l.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        matched = False
        print(f"Checking line: '{line}'")
        
        # Try Standard Patterns (Single Line)
        for idx, p in enumerate(patterns):
            m = p.search(line)
            if m:
                print(f"  Matched Standard Pattern #{idx+1}")
                vuelos.append("MATCH_STANDARD")
                matched = True
                break
        
        # Try Conviasa Pattern (Multi Line) if not matched
        if not matched:
            m = conviasa_pattern.search(line)
            if m:
                print(f"  Matched Conviasa Pattern!")
                print(f"    G1(Org): '{m.group(1)}'")
                print(f"    G2(Flt): '{m.group(2)}'")
                print(f"    G3(Cls): '{m.group(3)}'")
                
                # Buscar destino en la siguiente linea
                destino = "---"
                if i + 1 < len(lines):
                     candidate = lines[i+1]
                     print(f"    Looking ahead at: '{candidate}'")
                     if not conviasa_pattern.search(candidate) and len(candidate) < 30:
                         destino = candidate.split("PARA MAYOR")[0].strip()
                         print(f"    Destino Found: '{destino}'")
                
                vuelos.append(f"MATCH_CONVIASA -> Dest: {destino}")
                matched = True

        i += 1
            
    return vuelos

soto_text = """
CARACAS           ES 891 G   16DEC 0930 1030 GOW                       23K  OK
BARINAS
PARA MAYOR INFORMACION INGRESAR AL SIGUIENTE LINK
"""

print(_parse_kiu_flight_segments(soto_text))
