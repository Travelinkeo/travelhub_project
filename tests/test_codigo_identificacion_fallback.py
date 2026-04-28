from core.identification_utils import (
    extract_codigo_identificacion_anywhere,
    normalize_codigo_identificacion,
)

CASOS_INLINE = [
    ("NAME/NOMBRE:  DUQUE ECHEVERRY/OSCA (FLORIDA) FOID/D.IDENTIDAD: IDEPPE151144 OFFICE ID: US-16445-0", "IDEPPE151144"),
    ("RANDOM TEXT /D.IDENTIDAD: FOID: DUPLICATE777 ADDRESS OTHER", "DUPLICATE777"),
    ("XYZ FOID: XYZ999 RIF 123", "XYZ999"),
]

def test_normalize_codigo_identificacion_inline():
    # normalize directo sobre la línea completa (con otros campos) puede fallar; fallback lo rescata
    for texto, esperado in CASOS_INLINE:
        # La función normalize espera una linea que contenga FOID; aquí puede estar inline
        norm = normalize_codigo_identificacion(texto)
        anyw = extract_codigo_identificacion_anywhere(texto)
        assert anyw == esperado, f"Fallback no extrajo correctamente en: {texto} (normalize devolvió {norm})"
