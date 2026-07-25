"""Tests para Cms."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cms.models import Articulo, GuiaDestino, KBArticle, KBCategory, PostRedesSociales
from core.models.agencia import Agencia


class ArticuloModelTest(TestCase):
    """Articulo Model Test."""
    def setUp(self):
        """SetUp."""
        self.agencia = Agencia.objects.create(nombre="CMS Agency")
        self.articulo = Articulo.objects.create(
            titulo="Destino Caribe",
            slug="destino-caribe",
            contenido="Contenido de prueba",
            agencia=self.agencia,
        )

    def test_str(self):
        """Str."""
        self.assertEqual(str(self.articulo), "Destino Caribe")

    def test_default_estado(self):
        """Default estado."""
        self.assertEqual(self.articulo.estado, Articulo.EstadoArticulo.BORRADOR)

    def test_slug_unique(self):
        """Slug unique."""
        with self.assertRaises(Exception):
            Articulo.objects.create(
                titulo="Otro", slug="destino-caribe", contenido="x", agencia=self.agencia
            )

    def test_ordering(self):
        """Ordering."""
        a2 = Articulo.objects.create(
            titulo="Más nuevo", slug="mas-nuevo", contenido="x", agencia=self.agencia
        )
        articulos = list(Articulo.objects.all())
        self.assertEqual(articulos[0], a2)

    def test_publicacion(self):
        """Publicacion."""
        from datetime import datetime

        self.articulo.estado = Articulo.EstadoArticulo.PUBLICADO
        self.articulo.save()
        self.assertEqual(self.articulo.estado, "PUB")


class GuiaDestinoModelTest(TestCase):
    """Guia Destino Model Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="Guia Agency")
        self.guia = GuiaDestino.objects.create(
            nombre="París",
            descripcion="Ciudad del amor",
            idioma="Francés",
            agencia=self.agencia,
        )

    def test_str(self):
        """Str."""
        self.assertEqual(str(self.guia), "París")

    def test_default_idioma(self):
        """Default idioma."""
        guia2 = GuiaDestino.objects.create(
            nombre="Londres", descripcion="Capital UK", agencia=self.agencia
        )
        self.assertEqual(guia2.idioma, "Español")


class PostRedesSocialesModelTest(TestCase):
    """Post Redes Sociales Model Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="Social Agency")
        self.post = PostRedesSociales.objects.create(
            plataforma=PostRedesSociales.Plataforma.INSTAGRAM,
            contenido="Check this out!",
            agencia=self.agencia,
        )

    def test_default_not_published(self):
        """Default not published."""
        self.assertFalse(self.post.publicado)

    def test_plataformas(self):
        """Plataformas."""
        self.assertEqual(self.post.get_plataforma_display(), "Instagram")

    def test_str_without_articulo(self):
        """Str without articulo."""
        self.assertIn("Instagram", str(self.post))
        self.assertIn("Promo", str(self.post))


class KBCategoryModelTest(TestCase):
    """Kbcategory Model Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="KB Agency")
        self.cat = KBCategory.objects.create(
            name="Facturación", slug="facturacion", agencia=self.agencia
        )

    def test_str(self):
        """Str."""
        self.assertEqual(str(self.cat), "Facturación")

    def test_unique_together(self):
        """Unique together."""
        with self.assertRaises(Exception):
            KBCategory.objects.create(
                name="Duplicado", slug="facturacion", agencia=self.agencia
            )

    def test_misma_agencia_mismo_slug_duplicado(self):
        """Misma agencia mismo slug duplicado."""
        with self.assertRaises(Exception):
            KBCategory.objects.create(
                name="Otro", slug="facturacion", agencia=self.agencia
            )

    def test_diferente_agencia_mismo_slug_permitido(self):
        """Diferente agencia mismo slug permitido."""
        agencia2 = Agencia.objects.create(nombre="Otra Agency")
        cat2 = KBCategory.objects.create(
            name="Otro", slug="facturacion", agencia=agencia2
        )
        self.assertEqual(cat2.slug, "facturacion")


class KBArticleModelTest(TestCase):
    """Kbarticle Model Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="KB Article Agency")
        self.articulo = KBArticle.objects.create(
            title="Cómo facturar",
            slug="como-facturar",
            content="Contenido de ayuda",
            agencia=self.agencia,
        )

    def test_str(self):
        """Str."""
        self.assertEqual(str(self.articulo), "Cómo facturar")

    def test_defaults(self):
        """Defaults."""
        self.assertFalse(self.articulo.is_public)
        self.assertFalse(self.articulo.is_published)
        self.assertEqual(self.articulo.view_count, 0)

    def test_unique_together(self):
        """Unique together."""
        with self.assertRaises(Exception):
            KBArticle.objects.create(
                title="Otro", slug="como-facturar", content="x", agencia=self.agencia
            )
