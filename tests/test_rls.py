import pytest
from django.db import connection
from django.test import TestCase

pytestmark = pytest.mark.skip(reason="Tests requieren configuración completa o refactorización")


class RLSPolicyTest(TestCase):
    def test_rls_policies_exist(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename, policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                AND policyname IN ('tenant_isolation_policy', 'superadmin_bypass')
                ORDER BY tablename, policyname
            """)
            policies = cursor.fetchall()

        table_names = {t for t, p in policies}
        critical_tables = [
            "bookings_venta",
            "bookings_itemventa",
            "bookings_pagoventa",
            "bookings_proveedor",
            "core_auditlog",
        ]
        for table in critical_tables:
            self.assertIn(table, table_names, f"RLS policy missing for {table}")

    def test_tenant_isolation_policy_uses_agencia_id(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename, policyname, qual
                FROM pg_policies
                WHERE schemaname = 'public'
                AND policyname = 'tenant_isolation_policy'
                LIMIT 3
            """)
            policies = cursor.fetchall()

        for tablename, _policyname, qual in policies:
            self.assertIn(
                "agencia_id",
                qual or "",
                f"tenant_isolation_policy for {tablename} should use agencia_id",
            )

    def test_superadmin_bypass_policy_exists(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM pg_policies
                WHERE schemaname = 'public'
                AND policyname = 'superadmin_bypass'
            """)
            count = cursor.fetchone()[0]
        self.assertGreater(count, 0, "superadmin_bypass policy should exist")
