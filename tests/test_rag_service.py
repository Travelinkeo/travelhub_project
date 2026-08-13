from django.test import TestCase

from apps.automation.services.rag_service import RAGKnowledgeService
from apps.cms.models import KBArticle, KnowledgeChunk
from core.models import Agencia


class RAGServiceTestCase(TestCase):
    """Pruebas unitarias para el servicio RAG de Base de Conocimiento."""

    def setUp(self):
        self.agencia = Agencia.objects.create(nombre="Travelinkeo Test")
        self.article = KBArticle.objects.create(
            agencia=self.agencia,
            title="Manual de Comandos Sabre GDS",
            slug="manual-sabre-gds",
            content="Para dividir un PNR en Sabre se utiliza el comando 0SPLIT. Para guardar la división se usa 6AGENTE.",
        )

    def test_kb_article_indexing(self):
        indexed = RAGKnowledgeService.index_kb_article(self.article)
        self.assertGreater(indexed, 0)

        chunks = KnowledgeChunk.objects.filter(
            source_type="WIKI", source_reference_id=str(self.article.id)
        )
        self.assertTrue(chunks.exists())

    def test_search_relevant_chunks(self):
        RAGKnowledgeService.index_kb_article(self.article)
        result = RAGKnowledgeService.search_relevant_chunks(
            "dividir PNR Sabre", agencia=self.agencia
        )
        self.assertIn("Manual de Comandos Sabre GDS", result)
        self.assertIn("0SPLIT", result)

    def test_email_indexing(self):
        indexed = RAGKnowledgeService.index_email_content(
            subject="Actualización de Política de Equipaje Avianca",
            body="A partir de hoy, la franquicia de equipaje de mano en Avianca es de 10 kg en clase ejecutiva.",
            source_email="boletin@avianca.com",
            agencia=self.agencia,
        )
        self.assertGreater(indexed, 0)
        res = RAGKnowledgeService.search_relevant_chunks("equipaje Avianca", agencia=self.agencia)
        self.assertIn("Actualización de Política de Equipaje Avianca", res)
        self.assertIn("10 kg", res)
