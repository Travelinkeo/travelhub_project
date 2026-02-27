
import pdfplumber
import sys

PDF_PATH = r"C:\Users\ARMANDO\Downloads\boletos revision sabre\Recibo_de_pasaje_electrónico_19_marzo_para_ROSANGELA_DIAZ_SILVA_hgbtqy.pdf"

def main():
    print(f"Analyzing PDF: {PDF_PATH}")
    text = ""
    try:
        with pdfplumber.open(PDF_PATH) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return

    print("--- RAW TEXT DUMP ---")
    print(text[:2000])

if __name__ == "__main__":
    main()
