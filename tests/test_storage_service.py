"""Testes de persistência e regras das ações da aplicação."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lgpd_agent import service, storage
from test_mapping import entrevista


class TestArmazenamento(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch_pasta = patch.object(storage, "PASTA", Path(self.temp.name))
        self.patch_pasta.start()
        self.addCleanup(self.patch_pasta.stop)
        self.addCleanup(self.temp.cleanup)

    def test_salvar_carregar_listar_excluir(self):
        e = entrevista()
        storage.salvar(e)
        self.assertTrue((Path(self.temp.name) / (e["id"] + ".json")).exists())
        self.assertTrue((Path(self.temp.name) / (e["id"] + ".md")).exists())
        self.assertEqual(storage.carregar(e["id"])["titulo"], "Entrevista de teste")
        self.assertEqual(len(storage.listar()), 1)
        storage.excluir(e["id"])
        self.assertEqual(storage.listar(), [])

    def test_caminho_invalido_bloqueado(self):
        with self.assertRaises(FileNotFoundError):
            storage.caminho("../../.env")

    def test_criacao_imediata_sem_gemini(self):
        with patch.object(service, "turno_agente", side_effect=AssertionError("Gemini não deve ser chamado")):
            e, erro = service.criar()
        self.assertIsNone(erro)
        self.assertEqual(storage.carregar(e["id"])["processos"], [])
        self.assertEqual(e["mensagens"][1]["role"], "model")
        self.assertIn("departamento", e["mensagens"][1]["texto"])
        self.assertEqual(len(storage.listar()), 1)

    def test_edicao_de_mensagem_e_marcacao(self):
        e = entrevista()
        storage.salvar(e)
        editada = service.acao(e["id"], "editar", {"indice": 2, "texto": "Sou do financeiro"})
        self.assertTrue(editada["desatualizado"])
        self.assertTrue(editada["mensagens"][2]["editado"])
        with self.assertRaises(ValueError):
            service.acao(e["id"], "editar", {"indice": 50, "texto": "invalido"})

    def test_nao_cria_campos_desconhecidos(self):
        e = entrevista()
        e["processos"] = [{"nome": "RH", "campos": {}}]
        storage.salvar(e)
        with self.assertRaises(ValueError):
            service.acao(e["id"], "campo", {"processo": 0, "campo": "qualquer", "valor": "x"})


if __name__ == "__main__":
    unittest.main()
