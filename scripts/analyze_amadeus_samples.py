
import pdfplumber
import os

SAMPLES_DIR = 'XYZ/amadeus_samples'
OUTPUT_FILE = 'XYZ/amadeus_samples/analysis_dump.txt'

def extract_pdf_text(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text += f"\n--- PAGE {i+1} ---\n"
                text += page.extract_text()
    except Exception as e:
        text = f"Error extracting PDF: {e}"
    return text

def main():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        # PDFs
        for i in range(1, 9):
            filename = f"sample_{i}.pdf"
            path = os.path.join(SAMPLES_DIR, filename)
            if os.path.exists(path):
                print(f"Analyzing {filename}...")
                content = extract_pdf_text(path)
                f_out.write(f"\n{'='*50}\nFILE: {filename}\n{'='*50}\n")
                f_out.write(content)
        
        # EML (Simple dump)
        # For now skipping EML deep structure logic, focusing on PDF
        
    print(f"Analysis saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
