import PyPDF2

pdf_path = "TARIFARIO NACIONAL SEPTIEMBRE 2025-028.pdf"
reader = PyPDF2.PdfReader(open(pdf_path, 'rb'))

# Páginas 119-123 (índice 118-122)
for i in range(118, 123):
    page = reader.pages[i]
    texto = page.extract_text()
    print(f"\n{'='*80}")
    print(f"PÁGINA {i+1}")
    print('='*80)
    print(texto)
    print("\n")
