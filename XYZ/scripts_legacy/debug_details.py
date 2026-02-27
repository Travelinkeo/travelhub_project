
import re

def debug_details_extraction():
    # Simulated content based on user report and typical Sabre structure
    # We suspect "UHL6NT" is the airline locator.
    text_sample = """
    RECIBO DE PASAJE ELECTRÓNICO
    ISSUING AIRLINE: TURKISH AIRLINES
    AGENTE EMISOR: GRUPO SOPORTE GLOBAL
    REFERENCIA DE LA AEROLINEA: UHL6NT
    AIRLINE REF: UHL6NT
    
    VUELO TK224
    SALIDA: 16:50
    LLEGADA: 23 OCT 25
    EQUIPAJE: 2PC
    
    VUELO TK72
    SALIDA: 16:50
    LLEGADA: 24 OCT 25
    
    VUELO TK281
    SALIDA: 05:00
    LLEGADA: 22 OCT 26
    EQUIPAJE: 2PC
    """
    
    print("--- 1. LOCATOR EXTRACTION ---")
    # Current candidates in code (likely)
    patterns = [
        r"AIRLINE REF\s*[:\s]*([A-Z0-9]{6})",
        r"REFERENCIA DE LA AEROLINEA\s*[:\s]*([A-Z0-9]{6})",
        r"CONFIRMATION\s*[:\s]*([A-Z0-9]{6})"
    ]
    
    for pat in patterns:
        m = re.search(pat, text_sample, re.IGNORECASE)
        if m:
            print(f"Match found for '{pat}': {m.group(1)}")
        else:
            print(f"No match for '{pat}'")

    print("\n--- 2. TIME EXTRACTION ---")
    # Logic from sabre_parser.py
    text_clean = text_sample # simplified
    all_times = re.findall(r'(?:Time|Hora|Salida|Llegada)\s*(\d{1,2}:\d{2})', text_clean, re.IGNORECASE)
    print(f"Keywords Times: {all_times}")
    
    if not all_times:
         all_times = re.findall(r'(?<!\d)(\d{1,2}:\d{2})(?!\d)', text_clean)
         print(f"Backup Times: {all_times}")

    print("\n--- 3. BAGGAGE EXTRACTION (Per Block Simulation) ---")
    blocks = [
        "VUELO TK224 ... EQUIPAJE: 2PC", 
        "VUELO TK72 ... (No baggage text)", 
        "VUELO TK281 ... EQUIPAJE: 2PC"
    ]
    
    for i, blk in enumerate(blocks):
        bag_match = re.search(r'(?:Límite de equipaje|Baggage Allowance|Equipaje).*?(\d+\s*(?:PC|KG)?)', blk, re.IGNORECASE)
        res = bag_match.group(1) if bag_match else "None"
        print(f"Block {i+1}: {res}")

if __name__ == "__main__":
    debug_details_extraction()
