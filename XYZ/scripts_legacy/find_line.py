
def find_line():
    path = r"c:\Users\ARMANDO\travelhub_project\core\data\airports.json"
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if '"code": "LKL"' in line:
                print(f"Found LKL at line {i}: {line.strip()}")
            if '"code": "LKE"' in line:
                print(f"Found LKE at line {i}: {line.strip()}")

if __name__ == "__main__":
    find_line()
