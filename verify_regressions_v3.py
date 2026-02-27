
import re
import sys
import os

# Mock paths for testing
def mock_clean_passenger_name(name):
    """Copia exacta de la lógica implementada en base_parser.py"""
    if not name or name == 'No encontrado':
        return name

    # 1. Asegurar limpieza de cualquier tag residual
    name = re.sub(r'<[^>]+>', '', name)
    name = name.replace('&nbsp;', ' ').strip()

    # 2. Limpieza de FOID/RIF/ID pegado al final (Común en KIU)
    upper_name = name.upper()
    stop_tokens = ['FOID', 'RIF', 'ID', 'PASSPORT', 'VUELO', 'TICKET', 'DOCUMENTO']
    for token in stop_tokens:
        pattern = rf'\b{token}\b'
        match = re.search(pattern, upper_name)
        if match and match.start() > 3:
            name = name[:match.start()].strip()
            upper_name = name.upper()
    
    # 3. Eliminación de títulos y sufijos
    titles_pattern = r'\s*\b(MR|MS|MRS|MSTR|MISS|CHD|INF|JUNIOR|SENIOR|ADULT)\b\s*$'
    name = re.sub(titles_pattern, '', name, flags=re.IGNORECASE).strip()
    
    # 4. Limpieza de caracteres residuales
    name = name.rstrip(':/.- ').strip()
    return name

def test_names():
    cases = [
        ("ZULUAGA/JUAN JOSE ID12345", "ZULUAGA/JUAN JOSE"),
        ("RODRIGUEZ/IDALIA", "RODRIGUEZ/IDALIA"),
        ("ALEMAN/JOSE ARMANDO RIF J-123", "ALEMAN/JOSE ARMANDO"),
        ("DAVID/NOMBRE ID", "DAVID/NOMBRE"),
        ("DAVid/IDENTITAD", "DAVid/IDENTITAD"), # Should NOT match ID inside IDENTITAD
    ]
    
    for input_name, expected in cases:
        result = mock_clean_passenger_name(input_name)
        status = "✅" if result == expected else "❌"
        print(f"{status} Input: '{input_name}' | Result: '{result}' | Expected: '{expected}'")

if __name__ == "__main__":
    print("--- VERIFICACIÓN DE LIMPIEZA DE NOMBRES ---")
    test_names()
