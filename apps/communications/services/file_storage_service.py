"""
FileStorageService — Almacenamiento unificado con fallback automatico.

Backend primario:  Cloudflare R2 (boto3 / S3Boto3Storage)
Backend fallback:  Telegram Storage (canal privado de la agencia)

Regla de exclusividad:
  Solo uno de los dos backends estara activo en cualquier momento.
  Si USE_R2=True y R2 esta disponible  → se usa R2.
  Si USE_R2=False o R2 falla           → se usa Telegram.
  Nunca ambos simultaneamente.

Uso tipico::

    from apps.communications.services.file_storage_service import FileStorageService

    svc = FileStorageService(agencia=mi_agencia)
    result = svc.store(file_path="/tmp/boleto.pdf", filename="boleto_12345.pdf")
    if result.ok:
        # result.backend == 'r2' o 'telegram'
        # result.reference == URL publica (R2) o file_id (Telegram)
        print(result.reference)

    # Resolver URL de descarga bajo demanda (util para file_id de Telegram)
    url = svc.retrieve_url(result.reference, backend=result.backend)
"""

import logging
import os
from dataclasses import dataclass
from typing import BinaryIO

from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# RESULTADO DE OPERACION
# ============================================================================


@dataclass
class StorageResult:
    """Resultado de una operacion de almacenamiento.

    Attributes:
        ok:         True si el archivo se almaceno con exito.
        backend:    "r2" | "telegram" | None
        reference:  URL publica (R2) o file_id (Telegram). None si fallo.
        is_public:  True si la referencia es una URL directamente accesible.
        error:      Mensaje de error si ok=False.
    """

    ok: bool = False
    backend: str = None
    reference: str = None
    is_public: bool = False
    error: str = None

    @classmethod
    def failure(cls, error: str) -> "StorageResult":
        """Crea un resultado de fallo."""
        return cls(ok=False, error=error)

    @classmethod
    def r2_success(cls, url: str) -> "StorageResult":
        """Crea un resultado exitoso de R2."""
        return cls(ok=True, backend="r2", reference=url, is_public=True)

    @classmethod
    def telegram_success(cls, file_id: str) -> "StorageResult":
        """Crea un resultado exitoso de Telegram Storage."""
        return cls(ok=True, backend="telegram", reference=file_id, is_public=False)


# ============================================================================
# SERVICIO PRINCIPAL
# ============================================================================


class FileStorageService:
    """Servicio de almacenamiento con R2 como primario y Telegram como fallback.

    La seleccion del backend es automatica segun la disponibilidad:
    - Si USE_R2=True y las credenciales de R2 estan configuradas → R2
    - Si R2 no esta disponible o falla → Telegram Storage de la agencia

    Instanciar con la agencia correcta para garantizar el aislamiento multitenant.
    """

    def __init__(self, agencia=None):
        """__init__.

        Args:
            agencia: Instancia de Agencia. Requerido para Telegram fallback.
        """
        self._agencia = agencia
        self._use_r2 = getattr(settings, "USE_R2", False)
        self._r2_configured = self._check_r2_config()

    # ------------------------------------------------------------------
    # API PUBLICA
    # ------------------------------------------------------------------

    def store(
        self,
        file_path: str = None,
        file_obj: BinaryIO = None,
        filename: str = "archivo.pdf",
        caption: str = None,
    ) -> StorageResult:
        """Almacena un archivo y retorna un StorageResult.

        Args:
            file_path: Ruta local al archivo (alternativa a file_obj).
            file_obj:  Buffer de bytes abierto (alternativa a file_path).
            filename:  Nombre del archivo para metadatos.
            caption:   Descripcion opcional (usada en Telegram).

        Returns:
            StorageResult con el backend usado y la referencia al archivo.
        """
        if not file_path and not file_obj:
            return StorageResult.failure("Se requiere file_path o file_obj")

        if self._use_r2 and self._r2_configured:
            result = self._store_r2(file_path=file_path, file_obj=file_obj, filename=filename)
            if result.ok:
                return result
            # R2 fallo en runtime → fallback automatico a Telegram
            logger.warning(
                "[FileStorage] R2 fallo (%s). Usando Telegram como fallback.", result.error
            )

        return self._store_telegram(
            file_path=file_path, file_obj=file_obj, filename=filename, caption=caption
        )

    def retrieve_url(self, reference: str, backend: str = None) -> str | None:
        """Resuelve una URL de descarga para una referencia almacenada.

        Args:
            reference:  URL (R2) o file_id (Telegram).
            backend:    "r2" o "telegram". Si es None, se infiere.

        Returns:
            URL de descarga, o None si no se puede resolver.
        """
        if not reference:
            return None

        # Si es una URL completa, es R2 o un link directo
        if reference.startswith("http"):
            return reference

        # Si no es URL, asumir que es file_id de Telegram
        from apps.communications.services.telegram_unified import TelegramNotificationService

        return TelegramNotificationService.get_file_url(reference, agencia=self._agencia)

    @property
    def active_backend(self) -> str:
        """Retorna el backend que se usaria actualmente."""
        if self._use_r2 and self._r2_configured:
            return "r2"
        return "telegram"

    # ------------------------------------------------------------------
    # BACKENDS INTERNOS
    # ------------------------------------------------------------------

    def _store_r2(self, file_path=None, file_obj=None, filename="archivo.pdf") -> StorageResult:
        """Sube el archivo a Cloudflare R2 via boto3."""
        try:
            import boto3

            endpoint = getattr(settings, "R2_ENDPOINT_URL", None)
            access_key = getattr(settings, "R2_ACCESS_KEY_ID", None)
            secret_key = getattr(settings, "R2_SECRET_ACCESS_KEY", None)
            bucket = getattr(settings, "R2_BUCKET_NAME", None)
            custom_domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", None)

            if not all([endpoint, access_key, secret_key, bucket]):
                return StorageResult.failure("Credenciales R2 incompletas en settings")

            s3 = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )

            # Determinar prefijo con agencia para aislamiento logico
            agencia_slug = getattr(self._agencia, "subdominio_slug", None) or "global"
            s3_key = f"files/{agencia_slug}/{filename}"

            extra_args = {"ContentType": self._guess_content_type(filename)}

            if file_path and os.path.exists(file_path):
                s3.upload_file(file_path, bucket, s3_key, ExtraArgs=extra_args)
            elif file_obj:
                if hasattr(file_obj, "seek"):
                    file_obj.seek(0)
                s3.upload_fileobj(file_obj, bucket, s3_key, ExtraArgs=extra_args)
            else:
                return StorageResult.failure("Archivo no encontrado o buffer vacio")

            # Construir URL publica
            if custom_domain:
                url = f"https://{custom_domain}/{s3_key}"
            else:
                url = f"{endpoint}/{bucket}/{s3_key}"

            logger.info("[FileStorage] Subido a R2: %s", url)
            return StorageResult.r2_success(url)

        except ImportError:
            return StorageResult.failure("boto3 no instalado")
        except Exception as e:
            logger.error("[FileStorage] Error subiendo a R2: %s", e)
            return StorageResult.failure(str(e))

    def _store_telegram(
        self,
        file_path=None,
        file_obj=None,
        filename="archivo.pdf",
        caption=None,
    ) -> StorageResult:
        """Sube el archivo al canal de Telegram de la agencia."""
        try:
            from apps.communications.services.telegram_unified import TelegramStorageService

            tg = TelegramStorageService(agencia=self._agencia)

            if not tg.is_configured:
                agencia_str = (
                    getattr(self._agencia, "nombre", "sin agencia") if self._agencia else "sistema"
                )
                return StorageResult.failure(
                    f"Telegram Storage no configurado para '{agencia_str}'"
                )

            target = file_path if file_path and os.path.exists(file_path) else file_obj
            if not target:
                return StorageResult.failure("Archivo no encontrado o buffer vacio para Telegram")

            file_id = tg.upload_file_sync(target, filename=filename, caption=caption or filename)

            if file_id:
                logger.info("[FileStorage] Subido a Telegram. file_id: %s", file_id)
                return StorageResult.telegram_success(file_id)
            else:
                return StorageResult.failure("Telegram no retorno file_id")

        except Exception as e:
            logger.error("[FileStorage] Error subiendo a Telegram: %s", e)
            return StorageResult.failure(str(e))

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    @staticmethod
    def _check_r2_config() -> bool:
        """Verifica que las credenciales de R2 esten configuradas (no vacias/placeholder)."""
        keys = [
            "R2_ENDPOINT_URL",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET_NAME",
        ]
        placeholders = {"PLACEHOLDER", "ROTATE_BEFORE_PROD", "", None}
        for key in keys:
            val = getattr(settings, key, None)
            if not val or any(p in str(val) for p in placeholders):
                logger.debug("[FileStorage] R2 no configurado: %s=%s", key, val)
                return False
        return True

    @staticmethod
    def _guess_content_type(filename: str) -> str:
        """Infiere el Content-Type basandose en la extension del archivo."""
        import mimetypes

        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"
