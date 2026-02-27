
import re

def mock_get_solo_nombre_pasajero(nombre_completo: str) -> str:
    if '/' in nombre_completo:
        parts = nombre_completo.split('/')
        if len(parts) > 1:
            nombre_bruto = parts[1]
            return re.sub(r'\s*(MR|MS|MRS|CHD|INF)\s*$', '', nombre_bruto, flags=re.IGNORECASE).strip()
    return nombre_completo

def test_exact_names():
    cases = [
        ("ZULUAGA/JUAN JOSE", "JUAN JOSE"),
        ("RODRIGUEZ/IDALIA", "IDALIA"),
        ("ALEMAN/JOSE ARMANDO MR", "JOSE ARMANDO"),
        ("PEREZ/JUAN CHD", "JUAN"),
        ("IDALIA/NOMBRE", "NOMBRE"),
    ]
    
    print("--- PRUEBA DE NOMBRE SOLO (MÉTODO EXACTO) ---")
    for full, expected in cases:
        result = mock_get_solo_nombre_pasajero(full)
        status = "✅" if result == expected else "❌"
        print(f"{status} Full: '{full}' | Solo: '{result}' | Expected: '{expected}'")

if __name__ == "__main__":
    test_exact_names()
