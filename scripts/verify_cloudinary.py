
import cloudinary
import cloudinary.api
import os
import sys

def check_cloudinary():
    # Credenciales extraídas de tu .env
    cloud_name = "dt2xzykvz"
    api_key = "385223398934149"
    api_secret = "u0_M2-V3qJ8yC8sE5d6kQz1wP0o"

    print(f"🔍 Probando conexión a Cloudinary para: {cloud_name}")
    print(f"   API Key: {api_key}")

    # Configuración manual
    cloudinary.config(
        cloud_name = cloud_name,
        api_key = api_key,
        api_secret = api_secret
    )
    
    try:
        # Intentamos una llamada administrativa simple: Ver uso de la cuenta/Ping
        # Esta llamada solo funciona si las credenciales son válidas y la cuenta está activa.
        resp = cloudinary.api.ping()
        print("\n✅ ¡Conexión EXITOSA!")
        print("   La cuenta está activa y las credenciales funcionan.")
        print(f"   Respuesta: {resp}")
        
    except Exception as e:
        print(f"\n❌ Error de Conexión: {e}")
        
        err_msg = str(e).lower()
        print("\n--- Diagnóstico ---")
        if "invalid api_key" in err_msg:
            print("1. La API Key es incorrecta o fue borrada en la consola de Cloudinary.")
        elif "unauthorized" in err_msg or "signature" in err_msg:
            print("2. El API Secret no coincide. Alguien regeneró las claves.")
        elif "account blocked" in err_msg:
            print("3. La cuenta ha sido bloqueada (posiblemente por impago o exceso de uso).")
        elif "not found" in err_msg:
            print("4. El 'Cloud Name' no existe.")

if __name__ == '__main__':
    check_cloudinary()
