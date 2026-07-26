from django.test import TestCase

from apps.cms.models import Articulo, GuiaDestino, KBArticle, KBCategory, PostRedesSociales
from core.models.agencia import Agencia


class ArticuloModelTest(TestCase):
    """ArticuloModelTest."""

    def setUp(self):
        """setUp."""
        self.agencia = Agencia.objects.create(nombre="CMS Agency")
        self.articulo = Articulo.objects.create(
            titulo="Destino Caribe",
            slug="destino-caribe",
            contenido="Contenido de prueba",
            agencia=self.agencia,
        )

    def test_str(self):
        """test_str."""
        self.assertEqual(str(self.articulo), "Destino Caribe")

    def test_default_estado(self):
        """test_default_estado."""
        self.assertEqual(self.articulo.estado, Articulo.EstadoArticulo.BORRADOR)

    def test_slug_unique(self):
        """test_slug_unique."""
        with self.assertRaises(Exception):
            Articulo.objects.create(
                titulo="Otro", slug="destino-caribe", contenido="x", agencia=self.agencia
            )

    def test_ordering(self):
        """test_ordering."""
        a2 = Articulo.objects.create(
            titulo="Más nuevo", slug="mas-nuevo", contenido="x", agencia=self.agencia
        )
        articulos = list(Articulo.objects.all())
        self.assertEqual(articulos[0], a2)

    def test_publicacion(self):
        """test_publicacion."""

        self.articulo.estado = Articulo.EstadoArticulo.PUBLICADO
        self.articulo.save()
        self.assertEqual(self.articulo.estado, "PUB")


class GuiaDestinoModelTest(TestCase):
    """GuiaDestinoModelTest."""

    def setUp(self):
        """setUp."""
        self.agencia = Agencia.objects.create(nombre="Guia Agency")
        self.guia = GuiaDestino.objects.create(
            nombre="París",
            descripcion="Ciudad del amor",
            idioma="Francés",
            agencia=self.agencia,
        )

    def test_str(self):
        """test_str."""
        self.assertEqual(str(self.guia), "París")

    def test_default_idioma(self):
        """test_default_idioma."""
        guia2 = GuiaDestino.objects.create(
            nombre="Londres", descripcion="Capital UK", agencia=self.agencia
        )
        self.assertEqual(guia2.idioma, "Español")


class PostRedesSocialesModelTest(TestCase):
    """PostRedesSocialesModelTest."""

    def setUp(self):
        """setUp."""
        self.agencia = Agencia.objects.create(nombre="Social Agency")
        self.post = PostRedesSociales.objects.create(
            plataforma=PostRedesSociales.Plataforma.INSTAGRAM,
            contenido="Check this out!",
            agencia=self.agencia,
        )

    def test_default_not_published(self):
        """test_default_not_published."""
        self.assertFalse(self.post.publicado)

    def test_plataformas(self):
        """test_plataformas."""
        self.assertEqual(self.post.get_plataforma_display(), "Instagram")

    def test_str_without_articulo(self):
        """test_str_without_articulo."""
        self.assertIn("Instagram", str(self.post))
        self.assertIn("Promo", str(self.post))


class KBCategoryModelTest(TestCase):
    """KBCategoryModelTest."""

    def setUp(self):
        """setUp."""
        self.agencia = Agencia.objects.create(nombre="KB Agency")
        self.cat = KBCategory.objects.create(
            name="Facturación", slug="facturacion", agencia=self.agencia
        )

    def test_str(self):
        """test_str."""
        self.assertEqual(str(self.cat), "Facturación")

    def test_unique_together(self):
        """test_unique_together."""
        with self.assertRaises(Exception):
            KBCategory.objects.create(name="Duplicado", slug="facturacion", agencia=self.agencia)

    def test_misma_agencia_mismo_slug_duplicado(self):
        """test_misma_agencia_mismo_slug_duplicado."""
        with self.assertRaises(Exception):
            KBCategory.objects.create(name="Otro", slug="facturacion", agencia=self.agencia)

    def test_diferente_agencia_mismo_slug_permitido(self):
        """test_diferente_agencia_mismo_slug_permitido."""
        agencia2 = Agencia.objects.create(nombre="Otra Agency")
        cat2 = KBCategory.objects.create(name="Otro", slug="facturacion", agencia=agencia2)
        self.assertEqual(cat2.slug, "facturacion")


class KBArticleModelTest(TestCase):
    """KBArticleModelTest."""

    def setUp(self):
        """setUp."""
        self.agencia = Agencia.objects.create(nombre="KB Article Agency")
        self.articulo = KBArticle.objects.create(
            title="Cómo facturar",
            slug="como-facturar",
            content="Contenido de ayuda",
            agencia=self.agencia,
        )

    def test_str(self):
        """test_str."""
        self.assertEqual(str(self.articulo), "Cómo facturar")

    def test_defaults(self):
        """test_defaults."""
        self.assertFalse(self.articulo.is_public)
        self.assertFalse(self.articulo.is_published)
        self.assertEqual(self.articulo.view_count, 0)

    def test_unique_together(self):
        """test_unique_together."""
        with self.assertRaises(Exception):
            KBArticle.objects.create(
                title="Otro", slug="como-facturar", content="x", agencia=self.agencia
            )
