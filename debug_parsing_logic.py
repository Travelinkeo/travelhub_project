
import re
from bs4 import BeautifulSoup

def clean_money(value_str):
    value_str = str(value_str)
    return re.sub(r'[^\d.,]', '', value_str)

html_content = open('debug_text_1050.txt', 'r', encoding='utf-8', errors='ignore').read()
soup = BeautifulSoup(html_content, 'html.parser')
text = soup.get_text().upper()

print("--- TEXT CONTENT START ---")
print(repr(text))
print("--- TEXT CONTENT END ---")

# --- SIMULATING _parse_avior_text ---

# 2. Pasajeros y Tickets
nombres = []
header_pattern = r"(?:Nombre|Name|Passenger Name|Passenger)\s*:"
delimiter_pattern = r"(?:Correo|Email|Documento|Document|Doc|Id|Tiquete|Ticket|Tel|Phone)"

# Estrategia 1: Bloque
match_block = re.search(f"{header_pattern}\\s*(.*?)\\s*(?:{delimiter_pattern}:)", text, re.IGNORECASE | re.DOTALL)
if match_block:
     raw_name = match_block.group(1).strip()
     clean_name = re.sub(r'[\r\n]+', ' ', raw_name).strip()
     clean_name = clean_name.strip(":-_ ")
     if len(clean_name) > 2 and clean_name.lower() != "no":
         print(f"Strategy 1 Name Found: '{clean_name}'")
         nombres.append(clean_name)
else:
    print("Strategy 1 Failed")

if not nombres:
     # Estrategia 2: Line by line
     lines = text.splitlines()
     for i, line in enumerate(lines):
         line_upper = line.upper()
         if ("NOMBRE:" in line_upper or "NAME:" in line_upper) and \
            ("CORREO:" in line_upper or "EMAIL:" in line_upper or "DOC:" in line_upper):
             if i + 1 < len(lines):
                 raw_name_line = lines[i+1].strip()
                 # Heuristic check next line
                 parts = raw_name_line.split()
                 name_parts = []
                 for p in parts:
                     if "@" in p or "IDEPAZ" in p or "ID:" in p.upper() or "DOC" in p.upper(): break
                     name_parts.append(p)
                 
                 extracted = " ".join(name_parts).strip()
                 
                 # Heuristic: If single name
                 if len(extracted.split()) == 1 and i + 2 < len(lines):
                    next_line_cand = lines[i+2].strip()
                    if next_line_cand and ":" not in next_line_cand and not any(char.isdigit() for char in next_line_cand):
                        extracted += " " + next_line_cand
                 
                 if len(extracted) > 2:
                     print(f"Strategy 2 Name Found: '{extracted}'")
                     nombres.append(extracted)
                 break
     if not nombres:
        print("Strategy 2 Failed")

if not nombres:
     # Estrategia 3: Labels
     patterns_name = [
         r'(?:NAME|NOMBRE|PASSENGER)\s*[:\s]*(.+)', 
         r'(?:NAME|NOMBRE)/\s*([A-Z\s]+)'
     ]
     for p in patterns_name:
         m = re.search(p, text, re.IGNORECASE)
         if m:
             cand = m.group(1).strip()
             if len(cand) > 2:
                print(f"Strategy 3 Name Found: '{cand}'")
                nombres.append(cand)
                break
     if not nombres:
        print("Strategy 3 Failed")


# --- ITINERARY ---
vuelos_data = []
text_flat = text.replace('\n', ' ').replace('\r', ' ')
print(f"Text Flat Sample: {text_flat[500:800]}") # Print area around flight likely

itin_regex = re.compile(
    r'([A-Z -]+?)\s*([A-Z0-9]{2})\s*(\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4}).*?\b([A-Z ]{3,})$',
    re.IGNORECASE
)

itin_matches = itin_regex.finditer(text_flat)
count = 0
for match in itin_matches:
    print(f"Flight Match found: {match.group(0)}")
    count += 1

if count == 0:
    print("❌ No flights found via Regex")

