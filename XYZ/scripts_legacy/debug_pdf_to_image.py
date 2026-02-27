import pypdfium2 as pdfium
import os

pdf_path = r"C:\Users\ARMANDO\Downloads\Copa Airlines - aaleman - 11.2.1.pdf"
output_image = "copa_preview.jpg"

def test_render():
    print(f"--- RENDERING PDF TO IMAGE: {pdf_path} ---")
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        page = pdf[0] # First page
        bitmap = page.render(scale=2) # 2x scale for better resolution
        pil_image = bitmap.to_pil()
        pil_image.save(output_image)
        print(f"✅ Image saved to {output_image}")
        print(f"Image size: {pil_image.size}")
    except Exception as e:
        print(f"❌ Error rendering PDF: {e}")

if __name__ == "__main__":
    test_render()
