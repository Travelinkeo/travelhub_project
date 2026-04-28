
import psycopg2
import sys
from urllib.parse import urlparse

def test_connection(url, description):
    print(f"\n--- Probando: {description} ---")
    print(f"URL: {url}")
    
    try:
        # Parse output just for display (hiding password)
        p = urlparse(url)
        print(f"Host: {p.hostname}")
        print(f"User: {p.username}")
        # print(f"Pass: {p.password}") # Hidden
        
        conn = psycopg2.connect(url)
        print("✅ ¡CONEXIÓN EXITOSA!")
        
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM core_agencia;")
        count = cur.fetchone()[0]
        print(f"   Agencias encontradas: {count}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Falló: {e}")
        return False

if __name__ == "__main__":
    # URL original del usuario
    base_url = "postgresql://travelhub:2jNgY6qdqcXNuDnSLS3uajexLKwTXxSf@dpg-d40ahdmmcj7s738uo88g-a/travelhub_0a07"
    
    # Intentar URL base (por si acaso resuelve)
    if test_connection(base_url + "?sslmode=require", "URL Original (Internal?)"):
        sys.exit(0)

    # Intentar sufijos comunes de Render.com
    regions = [
        "oregon-postgres.render.com",
        "ohio-postgres.render.com",
        "frankfurt-postgres.render.com",
        "singapore-postgres.render.com",
        "washington-postgres.render.com" # Added Washington just in case
    ]
    
    # La parte del host en la URL original es "dpg-d40ahdmmcj7s738uo88g-a"
    # Necesitamos reemplazarla por "dpg-d40ahdmmcj7s738uo88g-a.region"
    
    parsed = urlparse(base_url)
    original_host = parsed.hostname
    
    for region in regions:
        new_host = f"{original_host}.{region}"
        # Reconstruir URL
        new_url = base_url.replace(original_host, new_host) + "?sslmode=require"
        
        if test_connection(new_url, f"Region: {region}"):
            print(f"\n🎉 ¡ENCONTRADA LA URL EXTERNA CORRECTA!\n   {new_url}")
            sys.exit(0)
            
    print("\n❌ No se pudo conectar con ninguna variante regional.")
