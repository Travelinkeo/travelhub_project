import os
import sys
import pdfplumber

# Path provided by user
pdf_path = r"C:\Users\ARMANDO\Downloads\Copa Airlines - aaleman - 11.2.1.pdf"
output_file = "copa_debug_text.txt"

def extract_text():
    print(f"--- EXTRACTING TEXT FROM: {pdf_path} ---")
    if not os.path.exists(pdf_path):
        print("❌ Error: File not found at path.")
        return

    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n\n"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
            
        print(f"✅ Text extracted to {output_file}")
        print("--- PREVIEW (First 500 chars) ---")
        print(text[:500])
        print("---------------------------------")
        
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")

if __name__ == "__main__":
    extract_text()
