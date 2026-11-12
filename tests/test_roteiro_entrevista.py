"""Regressões da entrevista real: loops, conclusão prematura e 11/12."""
import json
import unittest
from unittest.mock import patch

from lgpd_agent import agent
from lgpd_agent.constants import CHAVES
from lgpd_agent.interview_flow import (definir_proxima_resposta, resumo_pendencias,
                                       controle, lacunas_detalhadas)
from test_mapping import entrevista


def estado_11_12():
    e = entrevista()
    e["departamento"] = "Atendimento"
    for nome in ("Gestão de Funcionários", "Gestão de Clientes"):
        e["processos"].append({"nome": nome, "campos": {
            campo: {"valor": "Informação de teste", "implicito": False}
            for campo in CHAVES if campo != "base_legal"
        }})
    e["processos"][0]["campos"]["dados_sensiveis"]["valor"] = "Exames de saúde"
    e["processos"][1]["campos"]["dados_sensiveis"]["valor"] = "Nenhum"
    return e


def resposta_ia(e, texto, atualizacoes=None, departamento=""):
    e["mensagens"].append({"role": "user", "texto": texto})
    fake = {"resposta": "Tudo concluído! Quer mais alguma coisa?", "departamento": departamento,
            "atualizacoes": atualizacoes or []}
    # A pergunta natural é testada em test_melhorias.py; aqui valida-se o roteiro fixo.
    with patch.object(agent, "gemini", return_value=[{"text": json.dumps(fake, ensure_ascii=False)}]) as gm, \
         patch.object(agent, "formular_pergunta", side_effect=lambda ent, ultima, base: base):
        agent.turno_agente(e)
    assert gm.call_count == 1
    return e["mensagens"][-1]["texto"]


class TestRoteiroSemRepeticao(unittest.TestCase):
    def test_dois_processos_11_de_12_nao_finalizam(self):
        e = estado_11_12()
        r = resposta_ia(e, "Não há outros processos")
        self.assertIn("base legal", r.lower())
        self.assertIn("jurídica", r.lower())
        self.assertNotIn("mapeamento concluído", r.lower())
        self.assertEqual(len(resumo_pendencias(e)[1]), 2)
        r2 = resposta_ia(e, "não")
        self.assertIn("revisão", r2)
        self.assertNotIn("concluído com sucesso", r2)
        r3 = resposta_ia(e, "Por que está 11/12?")
        self.assertIn("base legal", r3.lower())
        self.assertNotIn("Como os dados são coletados", r3)

    def test_modelo_nao_decide_proxima_pergunta(self):
        e = estado_11_12()
        del e["processos"][0]["campos"]["coleta"]
        r = resposta_ia(e, "oi")
        self.assertIn("Como os dados são coletados", r)
        # Sem resposta nova: adia e não pergunta exatamente a mesma coisa.
        r2 = resposta_ia(e, "não sei")
        self.assertNotIn("Como os dados são coletados em", r2)
        self.assertIn("não vou repetir", r2.lower())

    def test_status_exibe_pendencias_sem_repetir_pergunta(self):
        e = estado_11_12()
        del e["processos"][0]["campos"]["coleta"]
        r = resposta_ia(e, "Por que ainda falta um campo?")
        self.assertIn("Como os dados são coletados", r)  # Nome do campo pendente no resumo
        self.assertNotIn("Como os dados são coletados em '", r)  # Não reapresenta pergunta
        self.assertIsNone(controle(e)["pergunta_atual"])
        r2 = resposta_ia(e, "próximo campo")
        self.assertIn("Como os dados são coletados em '", r2)

    def test_ultima_resposta_curta_direcionada_ao_alvo(self):
        e = estado_11_12()
        del e["processos"][0]["campos"]["transferencia_internacional"]
        primeira = resposta_ia(e, "Qual o próximo campo?")
        self.assertIn("enviados ou acessados", primeira)
        atual = [{"processo": "Gestão de Funcionários", "campo": "transferencia_internacional",
                  "valor": "Não existe transferência internacional", "implicito": False}]
        segunda = resposta_ia(e, "não", atual)
        self.assertNotIn("enviados ou acessados", segunda)
        self.assertNotIn("mapeamento concluído", segunda.lower())
        self.assertEqual(e["processos"][0]["campos"]["transferencia_internacional"]["valor"], atual[0]["valor"])

    def test_nao_regrava_informacoes_iguais_e_nao_repergunta(self):
        e = estado_11_12()
        dados = [{"processo": "Gestão de Clientes", "campo": "coleta",
                  "valor": "Informação de teste", "implicito": False}]
        resposta_ia(e, "está completo?", dados)
        self.assertFalse(any("Como os dados são coletados" in m["texto"] for m in e["mensagens"] if m["role"] == "model"))
        self.assertEqual(e["mensagens"][-1]["tools"], [])

    def test_nao_aceita_base_legal_generica_como_campo(self):
        e = estado_11_12()
        sugestao = [{"processo": "Gestão de Clientes", "campo": "base_legal",
                     "valor": "Hipótese a validar", "implicito": True}]
        resposta_ia(e, "pode concluir?", sugestao)
        self.assertNotIn("base_legal", e["processos"][1]["campos"])

    def test_dados_sensiveis_exigem_revisao_juridica(self):
        e = estado_11_12()
        proposta = [{"processo": "Gestão de Funcionários", "campo": "base_legal",
                     "valor": "Art. 11, cumprimento de obrigação legal - sujeita a revisão", "implicito": True}]
        resposta_ia(e, "tem como preencher tudo?", proposta)
        self.assertNotIn("base_legal", e["processos"][0]["campos"])

    def test_atualizacao_manual_precisa_de_validacao_explicita(self):
        e = estado_11_12()
        info = {"valor": "Base proposta após análise", "manual": True}
        e["processos"][0]["campos"]["base_legal"] = info
        op, jur = resumo_pendencias(e)
        self.assertEqual(len(jur), 2)  # escrever proposta não significa validar
        info["validacao_juridica"] = "validado"
        op, jur = resumo_pendencias(e)
        self.assertEqual(len(jur), 1)
        self.assertEqual(jur[0]["processo"], "Gestão de Clientes")

    def test_compatibilidade_com_json_sem_controle(self):
        e = estado_11_12()
        self.assertNotIn("controle_entrevista", e)
        r = resposta_ia(e, "oi")
        self.assertIn("base legal", r.lower())
        self.assertIn("controle_entrevista", e)


if __name__ == "__main__":
    unittest.main()
