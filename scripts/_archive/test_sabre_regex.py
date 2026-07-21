import re


def test_regex():
    s_clean = "MADRID, SPAIN SHANGHAI PUDONG, Código de"

    # Current Regex
    city_regex = r"\b([A-ZÁÉÍÓÚ]{3,}(?:\s+[A-ZÁÉÍÓÚ]+)*),\s*([A-ZÁÉÍÓÚ]{2,})?\b"

    print(f"Testing text: '{s_clean}'")
    print(f"Regex: {city_regex}")

    matches = re.findall(city_regex, s_clean)
    print(f"Matches found: {len(matches)}")
    for i, m in enumerate(matches):
        print(f"  Match {i}: {m}")

    # Test Case 2: Multi-word city 2
    s_clean_2 = "MADRID, SPAIN PARIS DE GAULLE, FRANCE"
    matches_2 = re.findall(city_regex, s_clean_2)
    print(f"\nTesting text 2: '{s_clean_2}'")
    for i, m in enumerate(matches_2):
        print(f"  Match {i}: {m}")


if __name__ == "__main__":
    test_regex()
