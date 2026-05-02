import os

def find_ready_methods(root_dirs):
    for root_dir in root_dirs:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file == 'apps.py':
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'def ready(self):' in content:
                            print(f"Found ready() in {path}")

find_ready_methods(['apps', 'core'])
