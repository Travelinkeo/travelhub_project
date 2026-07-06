"""
Utilidades de numeración secuencial atómica.

Usa NumberingSequence + select_for_update() para serializar la generación
de números correlativos (facturas, asientos contables, etc.) sin SQL nativo.
"""

import logging

from django.db import transaction

from core.models.numbering import NumberingSequence

logger = logging.getLogger(__name__)


def generar_numero_secuencial(prefix: str, model_class=None, field_name: str = None) -> str:
    """
    Genera un número secuencial atómico para un prefijo dado.

    Usa NumberingSequence.select_for_update() para adquirir un lock a nivel
    de base de datos sobre la fila del prefijo, garantizando exclusión mutua
    sin SQL nativo.

    Args:
        prefix: Prefijo único (ej: 'F-20260608', 'AS-20260608').
        model_class: Opcional — clase del modelo para verificar existencia.
        field_name: Opcional — nombre del campo numérico (default: 'numero_factura').

    Returns:
        str: Número formateado (ej: 'F-20260608-0001').
    """
    with transaction.atomic():
        # Adquirir lock ORM sobre la fila de este prefijo
        seq, created = NumberingSequence.objects.select_for_update().get_or_create(
            prefix=prefix,
            defaults={"last_number": 0},
        )

        if not created:
            # Verificar si hay registros existentes con este prefijo
            if model_class is not None:
                field = field_name or "numero_factura"
                filtro = {f"{field}__startswith": prefix}
                ultimo = model_class.objects.filter(**filtro).order_by(f"-{field}").first()
                if ultimo:
                    sufijo_existente = _extraer_sufijo(getattr(ultimo, field))
                    if sufijo_existente > seq.last_number:
                        # Hay un número en DB mayor que nuestro contador — sincronizar
                        seq.last_number = sufijo_existente

        seq.last_number += 1
        seq.save(update_fields=["last_number"])

        numero = f"{prefix}-{seq.last_number:04d}"
        logger.debug("Número secuencial generado: %s (prefix=%s)", numero, prefix)
        return numero


def _extraer_sufijo(valor: str) -> int:
    """Extrae el sufijo numérico de un string como 'F-20260608-0042'."""
    try:
        return int(valor.split("-")[-1])
    except (ValueError, IndexError):
        return 0
