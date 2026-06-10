from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models.agencia import Agencia, UsuarioAgencia

User = get_user_model()


class AgenciaModelTest(TestCase):
    def test_create_agencia(self):
        agencia = Agencia.objects.create(
            nombre="Test Agency",
            email_principal="test@agency.com",
        )
        self.assertEqual(agencia.nombre, "Test Agency")
        self.assertTrue(agencia.activa)

    def test_agencia_slug_auto_generated(self):
        agencia = Agencia.objects.create(
            nombre="Mi Agencia de Viajes", email_principal="test2@agency.com"
        )
        self.assertIsNotNone(agencia.subdominio_slug)

    def test_usuario_agencia_creation(self):
        user = User.objects.create_user(
            username="testuser", email="test@test.com", password="test123"
        )
        agencia = Agencia.objects.create(nombre="Test", email_principal="test3@agency.com")
        ua = UsuarioAgencia.objects.create(
            usuario=user,
            agencia=agencia,
            rol="admin",
        )
        self.assertEqual(ua.rol, "admin")
        self.assertTrue(ua.activo)


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username="newuser", email="new@test.com", password="pass123"
        )
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, "new@test.com")

    def test_get_or_create_user(self):
        user, created = User.objects.get_or_create(
            email="magic@test.com", defaults={"username": "magic@test.com", "is_active": True}
        )
        self.assertTrue(created)
        self.assertEqual(user.email, "magic@test.com")

        user2, created2 = User.objects.get_or_create(
            email="magic@test.com", defaults={"username": "magic@test.com", "is_active": True}
        )
        self.assertFalse(created2)
        self.assertEqual(user.id, user2.id)
