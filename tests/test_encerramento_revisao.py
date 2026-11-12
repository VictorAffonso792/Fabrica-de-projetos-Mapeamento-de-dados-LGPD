"""Casos reais: encerramento em loop e sugestões de base legal ignoradas."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from lgpd_agent import service, storage
from lgpd_agent.constants import CHAVES
from lgpd_agent.interview_flow import resumo_pendencias
from lgpd_agent.legal_suggestions import registrar_sugestoes
from test_mapping import entrevista


BASES = '''Para agilizar, seguem as bases legais sugeridas, sujeitas à validação jurídica:
Recrutamento e seleção\tProcedimentos preliminares ao contrato (art. 7º, V)
Admissão de funcionários\tCumprimento de obrigação legal (art. 7º, II)
Folha de pagamento\tCumprimento de obrigação legal (art. 7º, II)
Controle de ponto\tCumprimento de obrigação legal (art. 7º, II)
Gestão de benefícios\tExecução de contrato (art. 7º, V) e obrigação legal (art. 7º, II), conforme o benefício
Férias e afastamentos\tCumprimento de obrigação legal (art. 7º, II)
Desligamento\tCumprimento de obrigação legal (art. 7º, II)
Armazenamento de documentos\tCumprimento de obrigação legal (art. 7º, II), conforme o documento'''
NOMES = ["Recrutamento e seleção", "Admissão de funcionários", "Folha de pagamento", "Controle de ponto", "Gestão de benefícios", "Férias e afastamentos", "Desligamento", "Armazenamento de documentos"]


class TestEncerramentoERevisao(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.object(storage, "PASTA", Path(self.tmp.name))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.ent = entrevista()
        self.ent["processos"] = [{"nome": nome, "campos": {
            campo: {"valor": "Registrado", "implicito": False}
            for campo in CHAVES if campo != "base_legal"
        }} for nome in NOMES]
        storage.salvar(self.ent)

    def test_usuario_encerra_sem_gemini_e_com_pendencias(self):
        with patch.object(service, "turno_agente", side_effect=AssertionError("Não pode chamar Gemini")):
            ent = service.acao(self.ent["id"], "mensagem", {"texto": "Pode encerrar a entrevista. Não existem outras atividades."})
        self.assertTrue(ent["controle_entrevista"]["encerrada"])
        self.assertIn("Entrevista encerrada", ent["mensagens"][-1]["texto"])
        self.assertEqual(ent["controle_entrevista"]["situacao"], "encerrada_com_pendencias")
        self.assertEqual(len(resumo_pendencias(ent)[1]), 8)

    def test_nao_faz_perguntas_apos_encerramento(self):
        service.acao(self.ent["id"], "encerrar", {})
        with patch.object(service, "turno_agente", side_effect=AssertionError("Sem Gemini")):
            with self.assertRaisesRegex(ValueError, "encerrada"):
                service.acao(self.ent["id"], "mensagem", {"texto": "Outra coisa"})
        self.assertTrue(storage.carregar(self.ent["id"])["controle_entrevista"]["encerrada"])

    def test_botao_reabre_sem_gemini(self):
        service.acao(self.ent["id"], "encerrar", {})
        with patch.object(service, "turno_agente", side_effect=AssertionError("Sem Gemini")):
            ent = service.acao(self.ent["id"], "reabrir", {})
        self.assertFalse(ent["controle_entrevista"]["encerrada"])
        self.assertIn("reaberta", ent["mensagens"][-1]["texto"])

    def test_legal_bases_do_usuario_preliminares_sem_gemini(self):
        with patch.object(service, "turno_agente", side_effect=AssertionError("Não pode chamar Gemini")):
            ent = service.acao(self.ent["id"], "mensagem", {"texto": BASES})
        self.assertEqual(len(ent["processos"]), 8)
        for p in ent["processos"]:
            legal = p["campos"]["base_legal"]
            self.assertEqual(legal["validacao_juridica"], "pendente")
            self.assertEqual(legal["origem"], "sugestao_do_entrevistado")
        self.assertEqual(len(resumo_pendencias(ent)[0]), 0)
        self.assertEqual(len(resumo_pendencias(ent)[1]), 8)
        self.assertEqual(storage.resumo(ent)["preenchidos"], 96)
        self.assertEqual(storage.resumo(ent)["pendentes"], 0)
        self.assertEqual(storage.resumo(ent)["revisoes_juridicas"], 8)

    def test_termo_generico_nao_inventa_propostas(self):
        with patch.object(service, "turno_agente", side_effect=AssertionError("Sem Gemini")):
            self.assertEqual(registrar_sugestoes(self.ent, "Talvez o RH tenha base legal"), 0)
        self.assertTrue(all("base_legal" not in p["campos"] for p in self.ent["processos"]))

    def test_validacao_juridica_requer_acao_explicita(self):
        service.acao(self.ent["id"], "mensagem", {"texto": BASES})
        with self.assertRaises(ValueError):
            service.acao(self.ent["id"], "validar_base", {"processo": 0, "validado": "sim"})
        ent = service.acao(self.ent["id"], "validar_base", {"processo": 0, "validado": True})
        self.assertEqual(ent["processos"][0]["campos"]["base_legal"]["validacao_juridica"], "validado")
        self.assertEqual(len(resumo_pendencias(ent)[1]), 7)

    def test_reconstroi_sem_apagar_base_proposta_no_historico(self):
        self.ent["mensagens"].append({"role": "user", "texto": BASES})
        storage.salvar(self.ent)
        with patch.object(service, "atualizar_mapeamento", side_effect=lambda ent: None):
            ent = service.acao(self.ent["id"], "mapear", {})
        self.assertEqual(len(resumo_pendencias(ent)[1]), 8)
        self.assertIn("base_legal", ent["processos"][0]["campos"])

    def test_salva_status_encerrado_apos_validacao_juridica(self):
        service.acao(self.ent["id"], "mensagem", {"texto": BASES})
        service.acao(self.ent["id"], "encerrar", {})
        for i in range(8):
            ent = service.acao(self.ent["id"], "validar_base", {"processo": i, "validado": True})
        self.assertEqual(ent["controle_entrevista"]["situacao"], "encerrada")
        self.assertEqual(len(resumo_pendencias(ent)[1]), 0)


if __name__ == "__main__":
    unittest.main()
