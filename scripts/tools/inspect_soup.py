from bs4 import BeautifulSoup
import re

with open("estelar_debug.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

ticket_labels = soup.find_all(string=re.compile("Número de ticket", re.I))
print(f"Found {len(ticket_labels)} labels.")

for i, label in enumerate(ticket_labels):
    print(f"\n--- Label {i} ---")
    print(f"Text: '{label.strip()}'")
    curr = label
    depth = 0
    while curr and depth < 5:
        parent = curr.parent
        if parent:
            print(f"Dept {depth} Parent: <{parent.name}> (attrs: {parent.attrs})")
            curr = parent
            depth += 1
        else:
            print(f"Dept {depth} Parent: NONE")
            break
