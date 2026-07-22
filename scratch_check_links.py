import django, re
from django.urls import resolve, Resolver404

django.setup()

with open('/app/travelhub/settings_unfold.py') as f:
    text = f.read()

links = re.findall(r'"link":\s*"([^"]+)"', text)
broken = []

for l in links:
    try:
        resolve(l)
    except Resolver404:
        broken.append(l)

print('Total sidebar links:', len(links))
print('Broken links (404):', broken)
