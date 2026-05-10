"""Punto de entrada de modelos (Fase 2 de modularización).

Carga modelos desde submódulos temáticos.

⚠️ REFACTOR (Mayo 2026): Se eliminaron TODAS las importaciones de `apps.*` para romper
la dependencia circular crítica (apps -> core.models -> apps).

REGLAS:
1. Los modelos físicamente en `apps/` deben importarse desde sus propias apps.
2. Usar referencias lazy ('app.ModelName') en ForeignKeys y migraciones.
3. `core/` es la BASE (utilidades compartidas), NO debe importar de `apps/`.
"""

from .agencia import Agencia, UsuarioAgencia, AgenciaBranding, AgenciaConfiguracion
from .migration_checks import MigrationCheck
from .audit import AuditLog
from .ai import AIUsageLog
from .historial_boletos import HistorialCambioBoleto, AnulacionBoleto
from .magic_link import MagicLinkToken

__all__ = [
    'Agencia', 'UsuarioAgencia', 'AgenciaBranding', 'AgenciaConfiguracion',
    'MigrationCheck', 'AuditLog',
    'AIUsageLog',
    'HistorialCambioBoleto', 'AnulacionBoleto',
    'MagicLinkToken',
]
