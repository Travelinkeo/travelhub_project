"""Tests de regresión para verificar fixes del Plan de Remediación."""

import threading

import pytest
from django.core.cache import cache


@pytest.mark.django_db
def test_rate_limit_atomico():
    """Verifica que cache.incr() sea atómico bajo concurrencia."""
    key = "test_atomic_incr"
    cache.delete(key)
    cache.set(key, 0, timeout=60)

    n = 50
    results = []

    def incr_concurrent():
        try:
            val = cache.incr(key)
            results.append(val)
        except Exception as e:
            results.append(e)

    threads = [threading.Thread(target=incr_concurrent) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = cache.get(key)
    assert final == n, f"Expected {n} increments, got {final}. Race condition detected."
    assert len(results) == n


@pytest.mark.django_db
def test_rate_limit_add_atomico():
    """Verifica que cache.add() (SETNX) sea atómico."""
    key = "test_atomic_add"
    cache.delete(key)

    n = 20
    successes = []

    def add_concurrent():
        if cache.add(key, "locked", timeout=60):
            successes.append(True)

    threads = [threading.Thread(target=add_concurrent) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) == 1, f"Expected 1 add success, got {len(successes)}. Race condition."
