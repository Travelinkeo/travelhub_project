import pytest

from core.utils import sanitize_passenger_name


@pytest.mark.parametrize("raw,expected", [
    # Mantener nombre limpio
    ("PEREZ/JOSE", "PEREZ/JOSE"),
    # Remover ciudad/pais simples
    ("PEREZ/JOSE FLORIDA", "PEREZ/JOSE"),
    ("PEREZ/JOSE PANAMA", "PEREZ/JOSE"),
    # Frase compuesta CIUDAD DE ...
    ("PEREZ/JOSE CIUDAD DE PANAMA PANAMA", "PEREZ/JOSE"),
    # Paréntesis múltiples
    ("PEREZ/JOSE (CIUDAD DE PANAMA) (PANAMA)", "PEREZ/JOSE"),
    # Paréntesis residuales cortos
    ("PEREZ/JOSE (VE)", "PEREZ/JOSE"),
    # Espacios múltiples colapsados
    ("PEREZ/  JOSE   CIUDAD   DE   PANAMA", "PEREZ/JOSE"),
    # Acentos preservados
    ("GARCIA/ÁNGEL CIUDAD DE MEXICO", "GARCIA/ÁNGEL"),
    # Caso sin '/': se limpia suavemente (remueve paréntesis finales) pero no intenta token split
    ("JOSE (PANAMA)", "JOSE"),
    # Caso single token ubicación solo (debería vaciar parte nombres)
    ("PEREZ/PANAMA", "PEREZ/"),
])

def test_sanitize_passenger_name(raw, expected):
    assert sanitize_passenger_name(raw) == expected


def test_idempotent():
    """Aplicar dos veces produce el mismo resultado."""
    s = "PEREZ/JOSE CIUDAD DE PANAMA PANAMA"
    once = sanitize_passenger_name(s)
    twice = sanitize_passenger_name(once)
    assert once == twice
