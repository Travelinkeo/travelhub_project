"""
Script para analizar estructura del tarifario BT Travel
"""
import PyPDF2
import re
from pathlib import Path

def analizar_tarifario():
    pdf_path = Path(__file__).parent.parent / "TARIFARIO NACIONAL SEPTIEMBRE 2025-028.pdf"
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        print(f"Total páginas: {len(reader.pages)}")
        print("\n" + "="*80)
        
        # Analizar primeras 3 páginas para entender estructura
        for i in range(min(3, len(reader.pages))):
            print(f"\n--- PÁGINA {i+1} ---")
            text = reader.pages[i].extract_text()
            print(text[:1500])  # Primeros 1500 caracteres
            print("\n" + "="*80)

if __name__ == "__main__":
    analizar_tarifario()
