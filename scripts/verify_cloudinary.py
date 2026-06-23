import os
import sys

import cloudinary
import cloudinary.api


def check_cloudinary():
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.environ.get("CLOUDINARY_API_KEY", "")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")

    if not all([cloud_name, api_key, api_secret]):
        print(
            "❌ Variables de entorno CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY y CLOUDINARY_API_SECRET son requeridas."
        )
        sys.exit(1)

    print(f"Probando conexion a Cloudinary para: {cloud_name}")

    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)

    try:
        resp = cloudinary.api.ping()
        print("\nConexion EXITOSA!")
        print("   La cuenta esta activa y las credenciales funcionan.")
        print(f"   Respuesta: {resp}")

    except Exception as e:
        print(f"\nError de Conexion: {e}")

        err_msg = str(e).lower()
        print("\n--- Diagnostico ---")
        if "invalid api_key" in err_msg:
            print("1. La API Key es incorrecta o fue borrada en la consola de Cloudinary.")
        elif "unauthorized" in err_msg or "signature" in err_msg:
            print("2. El API Secret no coincide. Alguien regenero las claves.")
        elif "account blocked" in err_msg:
            print("3. La cuenta ha sido bloqueada (posiblemente por impago o exceso de uso).")
        elif "not found" in err_msg:
            print("4. El 'Cloud Name' no existe.")


if __name__ == "__main__":
    check_cloudinary()
