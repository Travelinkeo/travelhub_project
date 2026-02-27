
import os
import sys
import django
import base64

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.marketing_service import MarketingService

def verify_imagen_3():
    print("🎨 Verifying Google Imagen 3 Integration...")
    
    try:
        # Test Parameters
        hotel_name = "Grand Hotel Test"
        price = "120"
        style = "Cinematic"
        custom_text = "AI Verify"
        
        print(f"   Requesting image for: {hotel_name} (${price}) - Style: {style}")

        # Call Service
        b64_image = MarketingService.generate_ai_promo_image(
            hotel_name=hotel_name,
            price=price,
            style=style,
            custom_text=custom_text
        )
        
        if b64_image:
            print("   ✅ API Call Successful! Received Base64 string.")
            
            # Save to file to inspect
            output_path = "verify_image_result.jpg"
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(b64_image))
            
            print(f"   ✅ Image saved to: {os.path.abspath(output_path)}")
            print("   Please open this file to visually verify the quality.")
        else:
            print("   ❌ API Returned None (Failure). Check console logs for exceptions.")
            
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"   ❌ Exception during verification. Writing to verify_error.txt")
        with open("scripts/verify_error.txt", "w") as f:
            f.write(error_msg)
        print(f"   ❌ Error saved to scripts/verify_error.txt")

if __name__ == '__main__':
    verify_imagen_3()
