
import re

def fix_json():
    path = r"c:\Users\ARMANDO\travelhub_project\core\data\airports.json"
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: "name": "Value""code": "CODE"
    # We want to insert }, { between them
    # Regex: "name":\s*"([^"]+)"\s*"code":\s*"([^"]+)"
    
    # But wait, the previous view showed:
    # "name": "Liege"
    #   },
    #   {
    #     "code": "LGI",
    #     "name": "Deadmans Cay \/ Long Island"
    #   },
    
    # Wait, in step 2661 view:
    # 3488:     "name": "Liege"
    # 3489:   },
    # 3490:   {
    # 3491:     "code": "LGI",
    
    # So LGG and LGI were fine in the view!
    # But the error says: line 3488 column 20.
    
    # Let's look at the error again:
    # JSON Decode Error: Expecting ',' delimiter: line 3488 column 20 (char 45157)
    
    # Line 3488 in the view was: "name": "Liege"
    # Column 20 is after "Liege".
    
    # If it expects a comma, maybe it thinks it's inside an object but missing a comma?
    # Or maybe the previous line didn't have a comma?
    
    # Let's use regex to find "name": "..."\s*"code" and fix it.
    
    fixed_content = re.sub(r'("name":\s*"[^"]+")\s*("code":)', r'\1\n  },\n  {\n    \2', content)
    
    # Also fix missing commas between objects if any
    # fixed_content = re.sub(r'(})\s*({)', r'\1,\n\2', fixed_content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Fixed content written.")

if __name__ == "__main__":
    fix_json()
