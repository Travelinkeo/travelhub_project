
with open(r'c:\Users\ARMANDO\travelhub_project\core\ticket_parser.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Lines are 0-indexed, so line 367 is index 366.
    # We want lines 367-370 roughly.
    start = 365
    end = 375
    print(f"--- LINES {start+1} to {end} ---")
    for i in range(start, end):
        print(f"Line {i+1}: {repr(lines[i])}")
