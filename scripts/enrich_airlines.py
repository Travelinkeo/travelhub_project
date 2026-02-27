
import json
import os

# Updated Data with Numeric Codes (Sample of major airlines)
# We will start with the ones in the file and enrich them.
# Source: IATA Standard

IATA_NUMERIC_MAP = {
    "AV": "134", # Avianca
    "CM": "230", # Copa
    "AA": "001", # American
    "IB": "075", # Iberia
    "UX": "996", # Air Europa
    "TK": "235", # Turkish
    "TP": "047", # TAP
    "AF": "057", # Air France
    "KL": "074", # KLM
    "LH": "220", # Lufthansa
    "DL": "006", # Delta
    "LA": "045", # LATAM
    "AR": "044", # Aerolineas Argentinas
    "AM": "139", # Aeromexico
    "V0": "306", # Conviasa
    "Q6": "038", # Volaris (Check)
    "9V": "322", # Avior
    "QL": "339", # Laser
    "V2": "320", # Venezolana (Check)
    "J2": "308", # Azer
    "R7": "310", # Aserca (Old)
    "UA": "016", # United
    "PU": "349", # Plus Ultra
}

JSON_PATH = 'core/data/airlines.json'

def enrich_airlines():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated_count = 0
    for airline in data:
        code = airline.get('code')
        if code in IATA_NUMERIC_MAP:
            airline['numeric_code'] = IATA_NUMERIC_MAP[code]
            updated_count += 1
        elif 'numeric_code' not in airline:
             airline['numeric_code'] = None # Explicit null for now
             
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    print(f"✅ Updated {updated_count} airlines with numeric codes.")

if __name__ == "__main__":
    enrich_airlines()
