import json

from core import ticket_parser as tp


def load_and_parse(path):
    with open(path, encoding='utf-8', errors='ignore') as f:
        txt = f.read()
    out = tp.extract_data_from_text(txt)
    return out

if __name__ == '__main__':
    tests = [
        ('KIU', r'external_ticket_generator\KIU\E-TICKET ITINERARY RECEIPT - DUQUE ECHEVERRY_OSCAR HUMBERTO1.eml'),
        ('SABRE', r'external_ticket_generator\SABRE\0457281019415.txt')
    ]
    for name, path in tests:
        try:
            out = load_and_parse(path)
            print(f'\n==== {name} PARSE ====')
            print(json.dumps(out, ensure_ascii=False, indent=2)[:8000])
        except Exception as e:
            print(f'\n==== {name} PARSE FAILED ====' )
            print(str(e))
