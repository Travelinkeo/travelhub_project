import argparse
from email import policy
from email.parser import BytesParser
import os
import re

eml_path = r"C:\Users\ARMANDO\Downloads\Itinerary for Record Locator KW23RU.eml"

def analyze_eml():
    print(f"--- ANALYZING EML: {eml_path} ---")
    if not os.path.exists(eml_path):
        print("❌ File not found.")
        return

    with open(eml_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)

    # Search for keywords
    keywords = ["IATA", "Record Locator", "AWHKHH", "Copa Airlines"]
    
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get('Content-Disposition'))
            print(f"Part: {ctype}")
            
            if ctype == 'text/plain' or ctype == 'text/html':
                content = part.get_content()
                body += f"\n--- {ctype} ---\n{content[:2000]}\n..."
                
                # Check keywords in this part
                for k in keywords:
                    if k.lower() in content.lower():
                        match = re.search(f".{{0,50}}{k}.{{0,50}}", content, re.IGNORECASE | re.DOTALL)
                        if match:
                            print(f"✅ Found '{k}': ...{match.group(0).strip()}...")
    else:
        body = msg.get_content()
        for k in keywords:
             if k.lower() in body.lower():
                 print(f"✅ Found '{k}': {body}")

    print("\n--- BODY PREVIEW ---")
    print(body[:1000])

if __name__ == "__main__":
    analyze_eml()
