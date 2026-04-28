import os
import sys

# Asegurar que el directorio raíz del proyecto está en sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importar la función de saneamiento desde el módulo externo
# from external_ticket_generator.KIU.mi_proyecto_final.mi_proyecto_final.main import sanitize_nombre_completo_pasajero, get_solo_nombre_pasajero

# @pytest.mark.parametrize("raw,expected_full,expected_solo", [
#     ("DUQUE ECHEVERRY/OSCA CIUDAD DE PANAMA PANAMA", "DUQUE ECHEVERRY/OSCA", "OSCA"),
#     ("PEREZ DIAZ/JUAN CARLOS CIUDAD DE MEXICO", "PEREZ DIAZ/JUAN CARLOS", "JUAN CARLOS"),
#     ("RODRIGUEZ/ANA", "RODRIGUEZ/ANA", "ANA"),
#     ("ROJAS/EMMA (CIUDAD DE PANAMA) (PANAMA)", "ROJAS/EMMA", "EMMA"),
# ])
# def test_external_passenger_name_sanitization(raw, expected_full, expected_solo):
#     cleaned = sanitize_nombre_completo_pasajero(raw)
#     assert cleaned == expected_full
#     solo = get_solo_nombre_pasajero(cleaned)
#     assert solo == expected_solo
