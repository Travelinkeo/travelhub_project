
import psycopg2
import sys
from urllib.parse import urlparse

def test_region(base_host, region):
    full_host = f"{base_host}.{region}-postgres.render.com"
    url = f"postgresql://travelhub:2jNgY6qdqcXNuDnSLS3uajexLKwTXxSf@{full_host}/travelhub_0a07?sslmode=require"
    
    print(f"Testing Region: {region} ({full_host})...")
    try:
        conn = psycopg2.connect(url, connect_timeout=5)
        print(f"✅ SUCCESS! Connected to {region}")
        conn.close()
        return url
    except psycopg2.OperationalError as e:
        msg = str(e).strip()
        if "could not translate host name" in msg or "Name or service not known" in msg:
            print(f"   ❌ Host not found (DNS)")
        elif "certificate verify failed" in msg or "SSL" in msg:
            print(f"   ⚠️ HOST FOUND but SSL/Auth Error: {msg}")
            # This is a strong lead, might just need sslrootcert or similar, or it IS the right host
        else:
            print(f"   ❌ Connection Error: {msg}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return None

if __name__ == "__main__":
    base_host = "dpg-d40ahdmmcj7s738uo88g-a"
    regions = ["oregon", "ohio", "frankfurt", "singapore", "washington", "virginia"]
    
    found_url = None
    for r in regions:
        found_url = test_region(base_host, r)
        if found_url:
            break
            
    if found_url:
        print(f"\nFOUND: {found_url}")
    else:
        print("\nAll regions failed.")
