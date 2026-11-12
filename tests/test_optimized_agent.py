"""Testes das otimizações usando respostas simuladas (nenhuma credencial necessária)."""
import json
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lgpd_agent import agent, service, storage
from test_mapping import entrevista


class TestAgenteEstruturado(unittest.TestCase):
    def test_uma_chamada_e_varias_atualizacoes(self):
        e = entrevista()
        reply = {"resposta": "Como vocês armazenam esses dados?", "departamento": "Recursos Humanos",
                 "atualizacoes": [
                     {"processo": "Recrutamento", "campo": "finalidade", "valor": "Selecionar candidatos", "implicito": False},
                     {"processo": "Recrutamento", "campo": "titulares", "valor": "Candidatos", "implicito": False},
                     {"processo": "Recrutamento", "campo": "base_legal", "valor": "Hipótese a validar", "implicito": True}]}
        with patch.object(agent, "gemini", return_value=[{"text": json.dumps(reply)}]) as gem, \
             patch.object(agent, "formular_pergunta", side_effect=lambda ent, ultima, base: base):
            agent.turno_agente(e)
        self.assertEqual(gem.call_count, 1)
        self.assertEqual(e["departamento"], "Recursos Humanos")
        self.assertEqual(e["processos"][0]["campos"]["titulares"]["valor"], "Candidatos")
        # Texto genérico não deve ser usado para marcar base legal como preenchida.
        self.assertNotIn("base_legal", e["processos"][0]["campos"])
        self.assertIn("dados", e["mensagens"][-1]["texto"].lower())

    def test_resposta_invalida_nao_altera_estado(self):
        e = entrevista()
        antes = json.dumps(e)
        with patch.object(agent, "gemini", return_value=[{"text": "texto inválido"}]):
            with self.assertRaises(RuntimeError):
                agent.turno_agente(e)
        self.assertEqual(json.dumps(e), antes)

    def test_campo_editado_nao_sobrescreve(self):
        e = entrevista()
        e["processos"] = [{"nome": "Recrutamento", "campos": {"finalidade": {"valor": "Manual", "manual": True}}}]
        resp = {"resposta": "Qual é o prazo de retenção?", "departamento": "", "atualizacoes": [
            {"processo": "Recrutamento", "campo": "finalidade", "valor": "IA", "implicito": False}]}
        with patch.object(agent, "gemini", return_value=[{"text": json.dumps(resp)}]):
            agent.turno_agente(e)
        self.assertEqual(e["processos"][0]["campos"]["finalidade"]["valor"], "Manual")

    def test_contexto_mais_curto_preserva_mapeamento(self):
        e = entrevista()
        e["mensagens"] += [{"role": "user", "texto": f"Mensagem {i}"} for i in range(22)]
        e["processos"] = [{"nome": "Compras", "campos": {"finalidade": {"valor": "Contratações"}}}]
        dados = json.loads(agent.contexto(e))
        self.assertEqual(len(dados["mensagens_recentes"]), 10)
        self.assertEqual(dados["processos"][0]["nome"], "Compras")


class TestConcorrencia(unittest.TestCase):
    def test_ids_diferentes_nao_compartilham_trava(self):
        entrou=threading.Event()
        terminou=threading.Event()
        def primeiro():
            with service.trava_entrevista("processo-a"):
                entrou.set()
                terminou.wait(timeout=2)
        thread=threading.Thread(target=primeiro)
        thread.start()
        self.assertTrue(entrou.wait(1))
        inicio=time.perf_counter()
        with service.trava_entrevista("processo-b"):
            pass
        duracao=time.perf_counter()-inicio
        terminou.set()
        thread.join(timeout=2)
        self.assertLess(duracao, 0.5)

    def test_criacao_nao_chama_api(self):
        with TemporaryDirectory() as tmp, patch.object(storage,"PASTA",Path(tmp)), patch.object(service,"turno_agente",side_effect=AssertionError("não chamar")):
            ent, error=service.criar()
            self.assertIsNone(error)
            self.assertEqual(len(ent["mensagens"]), 2)
            self.assertEqual(len(storage.listar()), 1)

    def test_resposta_com_erro_nao_salva_mensagem(self):
        with TemporaryDirectory() as tmp, patch.object(storage,"PASTA",Path(tmp)):
            ent,_=service.criar()
            with patch.object(service,"turno_agente",side_effect=RuntimeError("Gemini indisponível")):
                with self.assertRaises(RuntimeError):
                    service.acao(ent["id"],"mensagem",{"texto":"Minha resposta"})
            no_disco=storage.carregar(ent["id"])
            self.assertEqual(len(no_disco["mensagens"]),2)


if __name__ == "__main__": unittest.main()
