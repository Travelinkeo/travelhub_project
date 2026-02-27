
import re

def test_avior_logic():
    text = """
    Nombre: Correo:
    HECTOR ZULUAGA HECTOR@GMAIL.COM
    
    Itinerario:
    BOGOTA-EL DO9V1425 W 24FEB 1900 2130 WCCSBOGV1 0P OK CARACAS
    """
    
    # --- NAME EXTRACTION ---
    nombres = []
    nombre_header_match = re.search(r"Nombre:.*Correo:", text, re.IGNORECASE)
    if nombre_header_match:
         lines = text.splitlines()
         for i, line in enumerate(lines):
             if "NOMBRE:" in line.upper() and ("CORREO:" in line.upper() or "EMAIL:" in line.upper()):
                 if i + 1 < len(lines):
                     raw_name_line = lines[i+1].strip()
                     parts = raw_name_line.split()
                     name_parts = []
                     for p in parts:
                         if "@" in p: break
                         name_parts.append(p)
                     nombres.append(" ".join(name_parts))
                     break
    
    print(f"Nombre Extraído: {nombres}")
    
    # --- ITINERARY EXTRACTION ---
    vuelos_data = []
    
    # NEW LOGIC: Flatten text first
    text_flat = text.replace('\n', ' ').replace('\r', ' ')
    
    itin_regex = re.compile(
        r'([A-Z -]+?)\s*(\d[A-Z]|[A-Z]\d|[A-Z]{2})\s*(\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4}).*?\b([A-Z ]{3,})$',
        re.IGNORECASE
    )
    
    matches = itin_regex.finditer(text_flat)
    for match in matches:
        v_ori = match.group(1).strip()
        v_code = match.group(2).strip()
        v_num = match.group(3).strip()
        v_clase = match.group(4).strip()
        v_date = match.group(5).strip()
        v_dep = match.group(6).strip()
        v_arr = match.group(7).strip()
        v_dest = match.group(8).strip()
        
        vuelos_data.append({
            'origen': v_ori,
            'destino': v_dest,
            'numero_vuelo': f"{v_code}{v_num}",
            'fecha': v_date,
            'salida': f"{v_dep[:2]}:{v_dep[2:]}",
            'llegada': f"{v_arr[:2]}:{v_arr[2:]}"
        })

    print(f"Vuelos Procesados: {vuelos_data}")

    print(f"Vuelos Procesados: {vuelos_data}")

if __name__ == "__main__":
    test_avior_logic()
