
import pdfplumber

file_path = r"C:\Users\ARMANDO\Downloads\Tabla Mundial de Aerolíneas.pdf"

try:
    with pdfplumber.open(file_path) as pdf:
        print(f"--- Inspecting {file_path} ---")
        print(f"Total Pages: {len(pdf.pages)}")
        
        for i, page in enumerate(pdf.pages[:5]):
            print(f"\n--- Page {i+1} Tables ---")
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                print(f"Table {t_idx + 1}:")
                for row in table:
                    print(row)
            if not tables:
                print("No tables found.")
                # Fallback to text with layout preservation
                print("Text (Layout Mode):")
                print(page.extract_text(layout=True))
            print("--- End Page ---")
            
except Exception as e:
    print(f"Error: {e}")
