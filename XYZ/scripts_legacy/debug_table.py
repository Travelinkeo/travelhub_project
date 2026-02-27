
import pdfplumber
import os

PDF_PATH = r"C:\Users\ARMANDO\Downloads\boletos revision sabre\Recibo_de_pasaje_electrónico_19_marzo_para_ROSANGELA_DIAZ_SILVA_hgbtqy.pdf"

def main():
    print(f"Testing Table Extraction on: {os.path.basename(PDF_PATH)}")
    
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"\n--- Page {i+1} Tables ---")
            tables = page.extract_tables()
            for j, table in enumerate(tables):
                print(f"Table {j+1}:")
                for row in table:
                    # Print row cleaning None values to empty strings
                    clean_row = [cell or "" for cell in row]
                    print(clean_row)

if __name__ == "__main__":
    main()
