import PyPDF2

pdf_path = r"C:\Users\ARMANDO\OTRA CARPETA\TARIFARIO NACIONAL SEPTIEMBRE 2025-028.pdf"
reader = PyPDF2.PdfReader(open(pdf_path, 'rb'))

# Buscar página con MARGARITA DYNASTY
for i, page in enumerate(reader.pages):
    texto = page.extract_text()
    if 'MARGARITA DYNASTY' in texto:
        print(f"=== PÁGINA {i+1} - MARGARITA DYNASTY ===")
        print(texto[:3000])  # Primeros 3000 caracteres
        print("\n\n=== BUSCANDO TARIFAS ===")
        # Buscar líneas con fechas
        for linea in texto.split('\n'):
            if '2025' in linea and 'AL' in linea:
                print(f"TARIFA: {linea}")
        break
