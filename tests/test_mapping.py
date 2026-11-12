"""Testes de regras de negócio sem rede."""
import json
import unittest
from unittest.mock import patch

from lgpd_agent import agent, mapping
from lgpd_agent.constants import CAMPOS, CHAVES
from lgpd_agent.report import markdown


def entrevista():
    return {
        "id": "20261111-120000", "titulo": "Entrevista de teste",
        "departamento": "", "criado": "11/11/2026 12:00",
        "atualizado": "11/11/2026 12:00",
        "mensagens": [
            {"role": "user", "texto": "Olá"},
            {"role": "model", "texto": "Qual é o seu departamento?"},
            {"role": "user", "texto": "Sou do RH"},
        ],
        "processos": [], "desatualizado": False,
    }


class TestMapeamento(unittest.TestCase):
    def test_campos_lgpd(self):
        self.assertEqual(len(CAMPOS), 12)
        self.assertIn("base_legal", CHAVES)

    def test_registro_e_consulta_de_lacunas(self):
        e = entrevista()
        resposta, _ = mapping.executar_tool(e, "definir_departamento", {"nome": "RH"})
        self.assertTrue(resposta["ok"])
        self.assertEqual(e["departamento"], "RH")
        mapping.executar_tool(e, "registrar_informacao", {
            "processo": "Recrutamento", "campo": "finalidade", "valor": "Contratar pessoas", "implicito": False
        })
        self.assertEqual(mapping.lacunas(e)[0]["processo"], "Recrutamento")
        self.assertNotIn("Finalidade (por que o processo existe)", mapping.lacunas(e)[0]["faltando"])
        self.assertEqual(len(mapping.lacunas(e)[0]["faltando"]), 11)

    def test_campo_manual_nao_e_sobrescrito_pela_ia(self):
        e = entrevista()
        p = mapping.achar_processo(e, "RH")
        p["campos"]["finalidade"] = {"valor": "Manual", "manual": True}
        retorno, _ = mapping.executar_tool(e, "registrar_informacao", {
            "processo": "RH", "campo": "finalidade", "valor": "Automático", "implicito": False
        })
        self.assertFalse(retorno["ok"])
        self.assertEqual(p["campos"]["finalidade"]["valor"], "Manual")

    def test_reconstrucao_preserva_edicoes_manuais(self):
        e = entrevista()
        p = mapping.achar_processo(e, "Recrutamento")
        p["campos"]["finalidade"] = {"valor": "Valor confirmado", "implicito": False, "manual": True}
        e["desatualizado"] = True
        resposta = {"processos": [{"nome": "Recrutamento", "campos": [
            {"campo": "finalidade", "valor": "Valor do Gemini", "implicito": True},
            {"campo": "titulares", "valor": "Candidatos", "implicito": False}
        ]}]}
        with patch.object(agent, "gemini", return_value=[{"text": json.dumps(resposta)}]):
            agent.atualizar_mapeamento(e)
        self.assertEqual(e["processos"][0]["campos"]["finalidade"]["valor"], "Valor confirmado")
        self.assertEqual(e["processos"][0]["campos"]["titulares"]["valor"], "Candidatos")
        self.assertFalse(e["desatualizado"])

    def test_relatorio_markdown(self):
        e = entrevista()
        p = mapping.achar_processo(e, "Recrutamento")
        p["campos"]["finalidade"] = {"valor": "Seleção", "implicito": False, "manual": True}
        md = markdown(e)
        self.assertIn("## Transcrição da entrevista", md)
        self.assertIn("Seleção _(editado manualmente)_", md)
        self.assertIn("Lacunas", md)


if __name__ == "__main__":
    unittest.main()
