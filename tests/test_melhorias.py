"""Melhorias: pergunta natural, perguntas agrupadas, relatório sem duplicidade e configuração."""
import json
import unittest
from unittest.mock import patch

from lgpd_agent import agent, config
from lgpd_agent.constants import CHAVES
from lgpd_agent.interview_flow import controle, definir_proxima_resposta
from lgpd_agent.report import markdown
from test_mapping import entrevista


def processo_vazio(nome="Recrutamento"):
    e = entrevista()
    e["processos"] = [{"nome": nome, "campos": {}}]
    return e


class TestPerguntaNatural(unittest.TestCase):
    def test_usa_texto_do_gemini(self):
        e = processo_vazio()
        with patch.object(agent, "PERGUNTAS_NATURAIS", True), \
             patch.object(agent, "gemini", return_value=[{"text": "Entendi! E para que serve esse processo?"}]):
            self.assertEqual(agent.formular_pergunta(e, "fazemos recrutamento", "Base?"),
                             "Entendi! E para que serve esse processo?")

    def test_fallback_em_erro_json_ou_sem_pergunta(self):
        e = processo_vazio()
        for retorno in (RuntimeError("503"), [{"text": '{"a": 1}'}], [{"text": "Ok."}], [{"text": ""}]):
            kwargs = {"side_effect": retorno} if isinstance(retorno, Exception) else {"return_value": retorno}
            with patch.object(agent, "PERGUNTAS_NATURAIS", True), patch.object(agent, "gemini", **kwargs):
                self.assertEqual(agent.formular_pergunta(e, "x", "Pergunta fixa?"), "Pergunta fixa?")

    def test_desligado_nao_chama_api(self):
        with patch.object(agent, "PERGUNTAS_NATURAIS", False), \
             patch.object(agent, "gemini", side_effect=AssertionError("não chamar")):
            self.assertEqual(agent.formular_pergunta(processo_vazio(), "x", "Fixa?"), "Fixa?")

    def test_turno_completo_faz_duas_chamadas(self):
        e = processo_vazio()
        e["mensagens"].append({"role": "user", "texto": "Cuidamos do recrutamento"})
        extracao = [{"functionCall": {"name": "registrar_mapeamento",
                                      "args": {"resposta": "ok", "departamento": "", "atualizacoes": []}}}]
        natural = [{"text": "Legal! Para que serve o recrutamento e por que precisam desses dados?"}]
        with patch.object(agent, "PERGUNTAS_NATURAIS", True), \
             patch.object(agent, "gemini", side_effect=[extracao, natural]) as gm:
            agent.turno_agente(e)
        self.assertEqual(gm.call_count, 2)
        self.assertEqual(e["mensagens"][-1]["texto"], natural[0]["text"])
        self.assertEqual(e["mensagens"][-1]["metricas"]["chamadas_turno"], 2)


class TestPerguntasAgrupadas(unittest.TestCase):
    def test_primeira_pergunta_cobre_o_grupo(self):
        e = processo_vazio()
        texto = definir_proxima_resposta(e, "oi")
        self.assertIn("finalidade", texto)
        self.assertIn("necessários", texto)
        self.assertEqual(controle(e)["pergunta_atual"]["campos"], ["finalidade", "justificativa"])

    def test_resposta_parcial_pergunta_o_que_faltou(self):
        e = processo_vazio()
        definir_proxima_resposta(e, "oi")
        e["processos"][0]["campos"]["finalidade"] = {"valor": "Contratar", "implicito": False}
        texto = definir_proxima_resposta(e, "serve para contratar", 1)
        self.assertEqual(controle(e)["pergunta_atual"]["campos"], ["justificativa"])
        self.assertIn("Por que essas categorias", texto)
        self.assertEqual(controle(e)["adiadas"], {})

    def test_nao_sei_adia_o_grupo_inteiro(self):
        e = processo_vazio()
        definir_proxima_resposta(e, "oi")
        definir_proxima_resposta(e, "não sei")
        self.assertEqual(len(controle(e)["adiadas"]), 2)
        self.assertEqual(controle(e)["pergunta_atual"]["campos"], ["titulares", "dados_pessoais", "dados_sensiveis"])

    def test_menos_perguntas_por_processo(self):
        e = processo_vazio()
        perguntas = 0
        while True:
            definir_proxima_resposta(e, "resposta")
            alvo = controle(e)["pergunta_atual"]
            if not alvo:
                break
            perguntas += 1
            for campo in alvo["campos"]:
                e["processos"][0]["campos"][campo] = {"valor": "ok", "implicito": False}
        self.assertEqual(perguntas, 6)  # antes eram 11


class TestRelatorioEConfig(unittest.TestCase):
    def test_base_legal_nao_aparece_nas_lacunas(self):
        e = processo_vazio()
        e["processos"][0]["campos"] = {c: {"valor": "ok"} for c in CHAVES if c != "base_legal"}
        md = markdown(e)
        self.assertIn("Revisão jurídica necessária", md)
        self.assertNotIn("## Lacunas", md)

    def test_numero_invalido_no_env_usa_padrao(self):
        with patch.object(config, "configurar", return_value="abc"):
            self.assertEqual(config._inteiro("PORTA", 8000, 1, 65535), 8000)
        with patch.object(config, "configurar", return_value="999"):
            self.assertEqual(config._inteiro("GEMINI_TIMEOUT", 45, 10, 120), 120)


if __name__ == "__main__":
    unittest.main()
