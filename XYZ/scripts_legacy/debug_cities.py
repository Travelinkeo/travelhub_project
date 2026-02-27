
import re

def debug_city_extraction():
    # Simulated block content from the PDF
    block = """
    TURKISH AIRLINES INC CARACAS, ISTANBUL AIRPORT
    TURKISH AIRLINES INC ISTANBUL AIRPORT, CARACAS
    """
    
    print(f"Analyzing block:\n{block}")

    # 1. STOPWORDS
    CITY_STOPWORDS = ['MATERIALS', 'AEROSOLS', 'FIREWORKS', 'LIQUIDS', 'FORBIDDEN', 'RESTRICTIONS', 'INFORMATION', 'CARRIER', 'POLICY', 'NOTICE', 'DATA', 'DANGEROUS', 'GOODS', 'DORAL', 'FL', 'AGENTE', 'AGENT', 'ADDRESS']
    
    # 2. REGEX (Updated Mixed Case)
    cities_raw = re.findall(r'([A-Za-zÁÉÍÓÚáéíóú -]+,\s*[A-Za-zÁÉÍÓÚáéíóú -]+)', block)
    
    print(f"Raw regex matches: {cities_raw}")
    
    valid_cities = []
    for c in cities_raw:
        c_clean = c.replace('\n', ' ').strip()
        
        # 3. CLEANING
        c_clean = re.sub(r'^(?:TURKISH AIRLINES|AEROLINEA|ISSUING AIRLINE|AIRLINE)(?:\s+INC|\s+LLC)?\s+', '', c_clean, flags=re.IGNORECASE)
        c_clean = c_clean.strip()
        
        print(f"Cleaned candidate: '{c_clean}'")
        
        # 4. VALIDATION
        is_stopword = any(sw in c_clean.upper() for sw in CITY_STOPWORDS)
        has_comma = ',' in c_clean
        length_ok = len(c_clean) > 3
        
        print(f"  Length > 3: {length_ok}")
        print(f"  No Stopwords: {not is_stopword}")
        print(f"  Has Comma: {has_comma}")

        if length_ok and not is_stopword and has_comma:
             valid_cities.append(c_clean)
             print("  -> ACCEPTED")
        else:
             print("  -> REJECTED")

    print(f"\nFinal Valid Cities: {valid_cities}")
    
    # 5. DISTRIBUTION LOGIC SIMULATION
    # Assume we have 4 flights
    num_flights = 4
    
    print(f"\nDistribution Logic (Num Flights = {num_flights}):")
    
    # Scenario A: len(valid_cities) >= len(block_flights) * 2 (Expects 8 for 4 flights)
    if len(valid_cities) >= num_flights * 2:
        print("Scenario A: Full Pair Match (Origin line, Dest line per flight)")
    elif len(valid_cities) >= num_flights:
        print("Scenario B: Single Line Match (Origin, Dest per flight)")
        for idx in range(num_flights):
            if idx < len(valid_cities):
                parts = valid_cities[idx].split(',')
                # Logic used in code:
                # parts[0].strip(), parts[1].strip()
                # BUT code assigns parts[0] to 'ciudad' and parts[1] to 'pais'???
                # Let's verify what the code actually does in standard sabre parser.
                print(f"  Flight {idx}: '{valid_cities[idx]}'")
                if len(parts) >= 2:
                    print(f"    Origin derived: {parts[0].strip()}")
                    print(f"    Dest derived:   {parts[1].strip()}")
    else:
        print("Scenario C: Fallback / Not enough info")

if __name__ == "__main__":
    debug_city_extraction()
