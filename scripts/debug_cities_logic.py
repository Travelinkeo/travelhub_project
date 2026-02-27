import re

def debug_sabre_logic():
    # The string after removing airline/dates/metadata
    s_clean = "MADRID, SPAIN SHANGHAI PUDONG,"
    
    print(f"Input s_clean: '{s_clean}'")
    
    print(f"\n--- TESTING ANCHOR LOGIC ---")
    
    # CASE 5: Anchor Strategy
    # Find "City,". Then look at gap.
    anchor_regex = r'\b([A-ZÁÉÍÓÚ]{3,}(?:\s+[A-ZÁÉÍÓÚ]+)*),'
    
    def parse_anchors(text):
        print(f"Parsing: '{text}'")
        matches = list(re.finditer(anchor_regex, text))
        results = []
        
        for i, m in enumerate(matches):
            city = m.group(1)
            start_gap = m.end()
            end_gap = matches[i+1].start() if i+1 < len(matches) else len(text)
            
            gap = text[start_gap:end_gap].strip()
            # Clean gap (remove newlines, check if it's a valid country)
            # Gap shouldn't be too long or contain restricted words? 
            # Actually, just taking the first word(s) if they match [A-Z] might be enough
            
            # Simple check: Is gap a Country?
            # It shouldn't contain the Next City (matches[i+1]) but end_gap handles that.
            
            # If gap is empty or just spaces/newlines, No Country.
            # If gap is "SPAIN ", Country = SPAIN.
            
            country = None
            if gap:
                 # Clean potential noise
                 gap_clean = re.sub(r'\s+', ' ', gap)
                 if re.match(r'^[A-ZÁÉÍÓÚ\s]{2,}$', gap_clean):
                     country = gap_clean
            
            results.append((city, country))
            print(f"  Match {i}: City='{city}', Gap='{gap}', ResolvedCountry='{country}'")
            
        return results

    parse_anchors("MADRID, SPAIN SHANGHAI PUDONG,")
    parse_anchors("SHANGHAI PUDONG, PARIS DE GAULLE,")

if __name__ == '__main__':
    debug_sabre_logic()
