"""Tests para Tasks app."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.tasks.models import ComentarioTarea, Tarea
from core.models.agencia import Agencia


class TareaModelTest(TestCase):
    """Tarea Model Test."""
    def setUp(self):
        """SetUp."""
        self.user = get_user_model().objects.create_user(username="tarea_user")
        self.agencia = Agencia.objects.create(nombre="Task Agency")
        self.tarea = Tarea.objects.create(
            titulo="Test Tarea",
            descripcion="Descripción de prueba",
            prioridad="alta",
            asignado_a=self.user,
            creado_por=self.user,
            agencia=self.agencia,
        )

    def test_str(self):
        """Str."""
        self.assertEqual(str(self.tarea), "Test Tarea")

    def test_default_estado(self):
        """Default estado."""
        self.assertEqual(self.tarea.estado, "pendiente")

    def test_default_prioridad(self):
        """Default prioridad."""
        t = Tarea.objects.create(titulo="Default", creado_por=self.user, agencia=self.agencia)
        self.assertEqual(t.prioridad, "media")

    def test_estados_disponibles(self):
        """Estados disponibles."""
        estados = dict(Tarea.ESTADOS)
        self.assertIn("pendiente", estados)
        self.assertIn("completada", estados)
        self.assertIn("cancelada", estados)

    def test_prioridades_disponibles(self):
        """Prioridades disponibles."""
        prioridades = dict(Tarea.PRIORIDADES)
        self.assertIn("baja", prioridades)
        self.assertIn("urgente", prioridades)

    def test_asignado_nullable(self):
        """Asignado nullable."""
        t = Tarea.objects.create(titulo="Sin asig", creado_por=self.user, agencia=self.agencia)
        self.assertIsNone(t.asignado_a)

    def test_vencimiento_nullable(self):
        """Vencimiento nullable."""
        self.assertIsNone(self.tarea.fecha_vencimiento)

    def test_created_at_auto(self):
        """Created at auto."""
        self.assertIsNotNone(self.tarea.created_at)

    def test_updated_at_auto(self):
        """Updated at auto."""
        self.assertIsNotNone(self.tarea.updated_at)


class ComentarioTareaModelTest(TestCase):
    """Comentario Tarea Model Test."""
    def setUp(self):
        """Setup."""
        self.user = get_user_model().objects.create_user(username="comment_user")
        self.agencia = Agencia.objects.create(nombre="Comment Agency")
        self.tarea = Tarea.objects.create(
            titulo="Tarea con comentarios", creado_por=self.user, agencia=self.agencia
        )
        self.comentario = ComentarioTarea.objects.create(
            tarea=self.tarea, usuario=self.user, texto="Test comment", agencia=self.agencia
        )

    def test_str(self):
        """Str."""
        self.assertIn("comment_user", str(self.comentario))

    def test_ordering(self):
        """Ordering."""
        c2 = ComentarioTarea.objects.create(
            tarea=self.tarea, usuario=self.user, texto="Second", agencia=self.agencia
        )
        comentarios = list(self.tarea.comentarios.all())
        self.assertEqual(comentarios[0], self.comentario)
        self.assertEqual(comentarios[1], c2)

    def test_relacion_tarea(self):
        """Relacion tarea."""
        self.assertEqual(self.comentario.tarea, self.tarea)


class TareasViewsTest(TestCase):
    """Tareas Views Test."""
    def setUp(self):
        """Setup."""
        self.user = get_user_model().objects.create_user(
            username="tasks_view", password="pass1234"
        )
        self.agencia = Agencia.objects.create(nombre="Tasks Agency")
        self.client.login(username="tasks_view", password="pass1234")

    def test_board_requires_login(self):
        """Board requires login."""
        self.client.logout()
        response = self.client.get(reverse("tasks:board"))
        self.assertEqual(response.status_code, 302)

    def test_board_renders(self):
        """Board renders."""
        response = self.client.get(reverse("tasks:board"))
        self.assertEqual(response.status_code, 200)

    def test_board_shows_tasks_by_status(self):
        """Board shows tasks by status."""
        Tarea.objects.create(
            titulo="Pendiente 1", estado="pendiente", creado_por=self.user, agencia=self.agencia
        )
        Tarea.objects.create(
            titulo="Completada 1", estado="completada", creado_por=self.user, agencia=self.agencia
        )
        response = self.client.get(reverse("tasks:board"))
        self.assertContains(response, "Pendiente 1")
        self.assertContains(response, "Completada 1")

    def test_create_task_get(self):
        """Create task get."""
        response = self.client.get(reverse("tasks:create"))
        self.assertEqual(response.status_code, 200)

    def test_create_task_post(self):
        """Create task post."""
        response = self.client.post(
            reverse("tasks:create"),
            {"titulo": "Nueva Tarea", "prioridad": "alta", "estado": "pendiente"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tarea.objects.filter(titulo="Nueva Tarea").exists())

    def test_detail_view(self):
        """Detail view."""
        tarea = Tarea.objects.create(
            titulo="Detalle Test", creado_por=self.user, agencia=self.agencia
        )
        response = self.client.get(reverse("tasks:detail", args=[tarea.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detalle Test")

    def test_update_view(self):
        """Update view."""
        tarea = Tarea.objects.create(
            titulo="Para Update", creado_por=self.user, agencia=self.agencia
        )
        response = self.client.post(
            reverse("tasks:update", args=[tarea.pk]),
            {"titulo": "Updated", "prioridad": "urgente", "estado": "en_progreso"},
        )
        tarea.refresh_from_db()
        self.assertEqual(tarea.titulo, "Updated")
        self.assertEqual(tarea.estado, "en_progreso")

    def test_delete_view(self):
        """Delete view."""
        tarea = Tarea.objects.create(
            titulo="Para Delete", creado_por=self.user, agencia=self.agencia
        )
        response = self.client.post(reverse("tasks:delete", args=[tarea.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Tarea.objects.filter(pk=tarea.pk).exists())

    def test_add_comment(self):
        """Add comment."""
        tarea = Tarea.objects.create(
            titulo="Commentable", creado_por=self.user, agencia=self.agencia
        )
        response = self.client.post(
            reverse("tasks:comment", args=[tarea.pk]),
            {"texto": "Un comentario de prueba"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ComentarioTarea.objects.filter(tarea=tarea, texto="Un comentario de prueba").exists()
        )

    def test_detail_shows_comments(self):
        """Detail shows comments."""
        tarea = Tarea.objects.create(
            titulo="Con Comments", creado_por=self.user, agencia=self.agencia
        )
        ComentarioTarea.objects.create(
            tarea=tarea, usuario=self.user, texto="Mi comentario", agencia=self.agencia
        )
        response = self.client.get(reverse("tasks:detail", args=[tarea.pk]))
        self.assertContains(response, "Mi comentario")
