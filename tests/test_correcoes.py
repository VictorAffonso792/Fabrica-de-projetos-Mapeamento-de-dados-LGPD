"""Regressões das correções: tools, troca de modelo, índices, acentos e erros amigáveis."""
import io
import json
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lgpd_agent import agent, gemini, mapping, service, storage
from test_mapping import entrevista


def erro_http(codigo):
    return urllib.error.HTTPError("url", codigo, "erro", {}, io.BytesIO(b"{}"))


class TestTools(unittest.TestCase):
    def test_turno_usa_function_calling(self):
        e = entrevista()
        chamada = [{"functionCall": {"name": "registrar_mapeamento", "args": {
            "resposta": "Entendi.", "departamento": "RH", "atualizacoes": [
                {"processo": "Recrutamento", "campo": "finalidade", "valor": "Contratar", "implicito": False}]}}}]
        with patch.object(agent, "gemini", return_value=chamada) as gm, \
             patch.object(agent, "formular_pergunta", side_effect=lambda ent, ultima, base: base):
            agent.turno_agente(e)
        payload = gm.call_args_list[0][0][0]
        self.assertEqual(payload["tools"][0]["functionDeclarations"][0]["name"], "registrar_mapeamento")
        self.assertEqual(payload["toolConfig"]["functionCallingConfig"]["mode"], "ANY")
        self.assertEqual(e["departamento"], "RH")
        self.assertEqual(e["processos"][0]["campos"]["finalidade"]["valor"], "Contratar")


class TestTrocaDeModelo(unittest.TestCase):
    def _rodar(self, erros):
        sequencia = list(erros)
        def falso(modelo, payload):
            if sequencia:
                raise erro_http(sequencia.pop(0))
            return [{"text": "ok de " + modelo}]
        with patch.object(gemini, "chamar_modelo", side_effect=falso), patch.object(gemini.time, "sleep"):
            return gemini.gemini({})

    def test_503_troca_para_reserva(self):
        self.assertIn(gemini.FALLBACK, self._rodar([503, 503])[0]["text"])

    def test_429_troca_para_reserva(self):
        self.assertIn(gemini.FALLBACK, self._rodar([429])[0]["text"])

    def test_todos_sobrecarregados_mensagem_clara(self):
        with self.assertRaisesRegex(RuntimeError, "sobrecarregados"):
            self._rodar([503] * 4)

    def test_401_nao_troca(self):
        with self.assertRaisesRegex(RuntimeError, "negado"):
            self._rodar([401])


class TestIndicesEAcentos(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(storage, "PASTA", Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)
        self.ent, _ = service.criar()
        service.acao(self.ent["id"], "processo", {"acao": "adicionar", "nome": "Folha"})

    def test_indice_negativo_rejeitado(self):
        for acao, corpo in [("processo", {"acao": "remover", "indice": -1}),
                            ("processo", {"acao": "renomear", "indice": -1, "nome": "X"}),
                            ("campo", {"processo": -1, "campo": "finalidade", "valor": "x"}),
                            ("validar_base", {"processo": -1, "validado": True})]:
            with self.assertRaisesRegex(ValueError, "não encontrado"):
                service.acao(self.ent["id"], acao, corpo)
        self.assertEqual(len(storage.carregar(self.ent["id"])["processos"]), 1)

    def test_indice_texto_rejeitado(self):
        with self.assertRaisesRegex(ValueError, "inválido"):
            service.acao(self.ent["id"], "processo", {"acao": "remover", "indice": "abc"})

    def test_processo_com_e_sem_acento_e_o_mesmo(self):
        e = {"processos": [{"nome": "Admissão", "campos": {}}]}
        self.assertIs(mapping.achar_processo(e, "admissao"), e["processos"][0])
        self.assertEqual(len(e["processos"]), 1)


if __name__ == "__main__":
    unittest.main()
