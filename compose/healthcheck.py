import sys
import urllib.request

try:
    # Intenta hacer un request local al puerto 8000
    response = urllib.request.urlopen("http://127.0.0.1:8000/health/", timeout=5)
    if response.status == 200:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
