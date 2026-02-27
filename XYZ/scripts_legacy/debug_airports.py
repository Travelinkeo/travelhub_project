
import json
import os

def check_airports_json():
    path = r"c:\Users\ARMANDO\travelhub_project\core\data\airports.json"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Loaded {len(data)} airports.")
        
        for i, entry in enumerate(data):
            if 'name' not in entry:
                print(f"ERROR at index {i}: Missing 'name' key. Entry: {entry}")
                # Print context
                start = max(0, i - 2)
                end = min(len(data), i + 3)
                print(f"Context entries [{start}:{end}]:")
                for j in range(start, end):
                    print(f"  {j}: {data[j]}")
            if 'code' not in entry:
                print(f"ERROR at index {i}: Missing 'code' key. Entry: {entry}")
                
        print("Validation complete.")
        
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_airports_json()
