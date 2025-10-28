import PyPDF2
import sys

if len(sys.argv) < 2:
    print("Uso: python ver_estructura_pdf.py <ruta_pdf>")
    sys.exit(1)
    
print("Buscando hoteles de Los Roques...\n")

pdf_path = sys.argv[1]
reader = PyPDF2.PdfReader(open(pdf_path, 'rb'))

# Ver páginas de Los Roques (84-117 = páginas 83-116 en índice 0)
for i in [83, 84, 85]:  # Primeras 3 páginas de Los Roques
    page = reader.pages[i]
    texto = page.extract_text()
    print(f"\n{'='*80}")
    print(f"PÁGINA {i+1}")
    print('='*80)
    print(texto[:1500])  # Primeros 1500 caracteres
    print("\n" + "="*80)
