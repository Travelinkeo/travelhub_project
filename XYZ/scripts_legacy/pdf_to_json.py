import PyPDF2
import json

pdf_path = "TARIFARIO NACIONAL SEPTIEMBRE 2025-028.pdf"
reader = PyPDF2.PdfReader(open(pdf_path, 'rb'))

# Extraer páginas de Morrocoy (119-123)
paginas_morrocoy = []
for i in range(118, 123):
    page = reader.pages[i]
    texto = page.extract_text()
    paginas_morrocoy.append({
        'numero_pagina': i + 1,
        'texto': texto
    })

# Guardar como JSON
with open('morrocoy_tarifario.json', 'w', encoding='utf-8') as f:
    json.dump(paginas_morrocoy, f, ensure_ascii=False, indent=2)

print("JSON generado: morrocoy_tarifario.json")
print(f"Total páginas: {len(paginas_morrocoy)}")
