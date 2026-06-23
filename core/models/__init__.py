"""Punto de entrada de modelos (Fase 2 de modularización).

Carga modelos desde submódulos temáticos.

⚠️ REFACTOR (Mayo 2026): Se eliminaron TODAS las importaciones de `apps.*` para romper
la dependencia circular crítica (apps -> core.models -> apps).

REGLAS:
1. Los modelos físicamente en `apps/` deben importarse desde sus propias apps.
2. Usar referencias lazy ('app.ModelName') en ForeignKeys y migraciones.
3. `core/` es la BASE (utilidades compartidas), NO debe importar de `apps/`.
"""

from .aeropuerto import Aeropuerto
from .agencia import Agencia, AgenciaBranding, AgenciaConfiguracion, UsuarioAgencia
from .ai import AIUsageLog
from .audit import AuditLog
from .cron_api_key import CronApiKey
from .feature_flags import FeatureFlag
from .historial_boletos import AnulacionBoleto, HistorialCambioBoleto
from .magic_link import MagicLinkToken
from .migration_checks import MigrationCheck

__all__ = [
    "Agencia",
    "UsuarioAgencia",
    "AgenciaBranding",
    "AgenciaConfiguracion",
    "MigrationCheck",
    "AuditLog",
    "AIUsageLog",
    "CronApiKey",
    "FeatureFlag",
    "HistorialCambioBoleto",
    "AnulacionBoleto",
    "MagicLinkToken",
    "Aeropuerto",
]
