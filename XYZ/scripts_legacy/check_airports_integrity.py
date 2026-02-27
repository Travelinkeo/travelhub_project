
import json
import os

def check_integrity():
    path = r"c:\Users\ARMANDO\travelhub_project\core\data\airports.json"
    print(f"Checking {path}...")
    
    if not os.path.exists(path):
        print("File not found!")
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Loaded {len(data)} entries.")
        
        errors = 0
        for i, entry in enumerate(data):
            if 'name' not in entry:
                print(f"ERROR at index {i}: Missing 'name'. Entry: {entry}")
                errors += 1
            if 'code' not in entry:
                print(f"ERROR at index {i}: Missing 'code'. Entry: {entry}")
                errors += 1
                
        if errors == 0:
            print("INTEGRITY CHECK PASSED: All entries have 'code' and 'name'.")
        else:
            print(f"INTEGRITY CHECK FAILED: Found {errors} errors.")
            
    except json.JSONDecodeError as e:
        print(f"JSON DECODE ERROR: {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    check_integrity()
