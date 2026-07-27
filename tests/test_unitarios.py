import unittest
import sys
from unittest.mock import MagicMock, patch

# 1. Mock de librerías de terceros antes de importar los módulos del proyecto
mock_sentence_transformers = MagicMock()
mock_sentence_transformers.util = MagicMock()
sys.modules['sentence_transformers'] = mock_sentence_transformers

mock_fastapi = MagicMock()
sys.modules['fastapi'] = mock_fastapi
sys.modules['fastapi.middleware.cors'] = MagicMock()

mock_pydantic = MagicMock()
sys.modules['pydantic'] = mock_pydantic

mock_slowapi = MagicMock()
sys.modules['slowapi'] = mock_slowapi
sys.modules['slowapi.util'] = MagicMock()
sys.modules['slowapi.errors'] = MagicMock()

sys.modules['rank_bm25'] = MagicMock()
sys.modules['ollama'] = MagicMock()

mock_cachetools = MagicMock()
sys.modules['cachetools'] = mock_cachetools

# Mock torch y numpy
mock_torch = MagicMock()
sys.modules['torch'] = mock_torch
mock_numpy = MagicMock()
sys.modules['numpy'] = mock_numpy

# 2. Ahora podemos importar de forma segura
from preprocessing import (
    pre_corregir_rapido, preprocesar_consulta,
    preprocesar_para_embeddings, expandir_intencion, enmascarar_pii
)
from guardrails import validar_guardrail, OUT_OF_DOMAIN
from router import detectar_intencion_dura
from rag_engine import es_ruido_catalogo, es_respuesta_critica


class TestPreprocessing(unittest.TestCase):
    def test_pre_corregir_rapido(self):
        self.assertEqual(pre_corregir_rapido("komo conetarse al waifai"), "como conetarse al wifi")
        self.assertEqual(pre_corregir_rapido("orario d la biblio"), "horario d la biblioteca")

    def test_enmascarar_pii(self):
        # Email
        self.assertEqual(enmascarar_pii("micasa@example.edu"), "mic***@example.edu")
        # RUT
        self.assertEqual(enmascarar_pii("mi RUT es 19.827.364-k"), "mi RUT es 1982*****")
        # Teléfono
        self.assertEqual(enmascarar_pii("mi numero es +56 9 1234 5678"), "mi numero es +569*****")

    def test_preprocesar_para_embeddings(self):
        # El preprocesamiento de embeddings mantiene acentos (tildes)
        self.assertEqual(preprocesar_para_embeddings("¿Cómo puedo devolver un libro?"), "cómo puedo devolver un libro")

    def test_preprocesar_consulta(self):
        # Debe remover stopwords
        self.assertNotIn("puedo", preprocesar_consulta("como puedo devolver un libro"))
        self.assertIn("devolver", preprocesar_consulta("como puedo devolver un libro"))


class TestGuardrails(unittest.TestCase):
    def test_validar_guardrail_valido(self):
        pasa, msj = validar_guardrail("¿Cuál es el horario?")
        self.assertTrue(pasa)

    def test_validar_guardrail_invalido_fuera_dominio(self):
        pasa, msj = validar_guardrail("dónde pago mi matrícula")
        self.assertFalse(pasa)
        self.assertIn("servicios, recursos y normativas de la Biblioteca", msj)

    def test_validar_guardrail_invalido_corto(self):
        pasa, msj = validar_guardrail("medicina")
        self.assertFalse(pasa)
        self.assertIn("especificar tu consulta", msj)


class TestRouter(unittest.TestCase):
    def test_detectar_intencion_dura_salas(self):
        self.assertEqual(detectar_intencion_dura("como reservar sala de estudio"), "salas_estudio")
        self.assertEqual(detectar_intencion_dura("quiero reservar salas"), "salas_estudio")

    def test_detectar_intencion_dura_lockers(self):
        self.assertEqual(detectar_intencion_dura("como funcionan los lockers"), "lockers")
        self.assertEqual(detectar_intencion_dura("perdi la llave del locker"), "lockers")

    def test_detectar_intencion_dura_evitar_falsos_positivos(self):
        # Evitar falsos positivos de "llave" mezclado con salas
        self.assertEqual(detectar_intencion_dura("dónde pido la llave de la sala de estudio"), "salas_estudio")
        
        # Evitar falsos positivos con "estudio" genérico
        self.assertEqual(detectar_intencion_dura("puedo estudiar en la biblioteca?"), "rag_general")
        self.assertEqual(detectar_intencion_dura("cuál es el plan de estudio?"), "rag_general")
        
        # Evitar falsos positivos de "tesis" (documento) confundiéndose con salas de tesis
        self.assertEqual(detectar_intencion_dura("como puedo pedir una tesis"), "tesis")


class TestRAGEngine(unittest.TestCase):
    def test_es_respuesta_critica(self):
        self.assertTrue(es_respuesta_critica("la clave del wifi es campus2026"))
        self.assertTrue(es_respuesta_critica("el costo es de $12.000"))
        # No debe ser crítica después de nuestra reducción
        self.assertFalse(es_respuesta_critica("el horario de la biblioteca es de lunes a viernes"))

    def test_es_ruido_catalogo(self):
        # Pregunta sobre libro general no debe retornar multas
        self.assertTrue(es_ruido_catalogo("quiero buscar un libro", "Si no devuelves el libro tienes una multa."))
        # Pregunta sobre multas específicas sí debe retornar multas
        self.assertFalse(es_ruido_catalogo("tengo una multa por libro", "Si no devuelves el libro tienes una multa."))


if __name__ == "__main__":
    unittest.main()
