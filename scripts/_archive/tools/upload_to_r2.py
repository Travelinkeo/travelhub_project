import os

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

media_root = settings.MEDIA_ROOT
print(f"Subiendo archivos desde {media_root} hacia R2...")

uploaded_count = 0
for root, _dirs, files in os.walk(media_root):
    for file in files:
        file_path = os.path.join(root, file)
        rel_path = os.path.relpath(file_path, media_root)
        # Convert backslashes to forward slashes for S3
        s3_key = rel_path.replace("\\", "/")

        try:
            if not default_storage.exists(s3_key):
                with open(file_path, "rb") as f:
                    default_storage.save(s3_key, File(f))
                    print(f"✅ Subido: {s3_key}")
                    uploaded_count += 1
            else:
                print(f"⏭️ Ya existe en R2: {s3_key}")
        except Exception as e:
            print(f"❌ Error al subir {s3_key}: {e}")

print(f"Proceso finalizado. Total de archivos nuevos subidos: {uploaded_count}")
