import threading
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.crm.models import Cliente
from apps.finance.models import Factura
from apps.finance.models.core_finance import generar_numero_factura_atomico
from apps.finance.models.currencies import Moneda
from core.models.agencia import Agencia


@pytest.mark.django_db(transaction=True)
def test_invoice_generation_concurrency():
    """
    Verifica que la generación paralela de facturas bajo alta concurrencia
    sea completamente segura, secuencial y libre de IntegrityErrors por clave única.
    """
    # 1. Crear setup inicial de datos
    agencia = Agencia.objects.create(nombre="Agencia Facturacion", activa=True)
    moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dólar", simbolo="$")
    cliente = Cliente.objects.create(nombres="Cliente Concurrente", agencia=agencia)

    factura_date = date(2026, 6, 15)
    prefix = f"F-{factura_date.strftime('%Y%m%d')}"

    results = []
    errors = []

    def create_invoice_thread(thread_idx):
        try:
            # Cada hilo ejecuta su propia transacción e inserción
            with transaction.atomic():
                num = generar_numero_factura_atomico(Factura, factura_date, prefix=prefix)

                # Crear la factura de prueba
                Factura.objects.create(
                    numero_factura=num,
                    agencia=agencia,
                    cliente=cliente,
                    moneda=moneda,
                    fecha_emision=factura_date,
                    monto_total=Decimal("100.00"),
                    subtotal=Decimal("100.00"),
                )
                results.append(num)
        except IntegrityError as ie:
            errors.append(f"Thread {thread_idx}: IntegrityError de duplicidad detectado: {ie}")
        except Exception as e:
            errors.append(f"Thread {thread_idx}: Error inesperado: {e}")
        finally:
            from django.db import connections

            connections.close_all()

    # Lanzamos 15 hilos que compiten simultáneamente por el número correlativo inicial
    n_threads = 15
    threads = []
    for i in range(n_threads):
        t = threading.Thread(target=create_invoice_thread, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verificaciones
    assert not errors, f"Se detectaron colisiones de concurrencia: {errors}"
    assert (
        len(results) == n_threads
    ), f"Se esperaban {n_threads} facturas, se crearon {len(results)}"

    # Verificar que todos los números generados son únicos
    assert len(set(results)) == n_threads, f"Números duplicados generados: {results}"

    # Verificar secuencialidad estricta (desde -0001 hasta -0015)
    for idx in range(1, n_threads + 1):
        expected_num = f"{prefix}-{idx:04d}"
        assert expected_num in results, f"Falta número correlativo en la secuencia: {expected_num}"
