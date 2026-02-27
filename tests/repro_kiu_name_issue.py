import pytest
from core.ticket_parser import extract_data_from_text

def test_kiu_laser_name_regression():
    """
    Test para asegurar que 'ISSUING AIRLINE/LINEA AEREA EMISORA' no se capture como nombre.
    """
    sample_text = """
    ISSUING AIRLINE/LINEA AEREA EMISORA: LASER AIRLINES
    NAME/NOMBRE: SMITH/JANE MS
    TICKET NUMBER: 1234567890
    """
    
    data = extract_data_from_text(sample_text)
    
    nombre = data.get('NOMBRE_DEL_PASAJERO')
    print(f"Nombre extraido: {nombre}")
    
    assert "ISSUING AIRLINE" not in nombre.upper()
    assert "SMITH/JANE" in nombre.upper()

if __name__ == "__main__":
    test_kiu_laser_name_regression()
