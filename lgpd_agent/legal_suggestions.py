"""Registra sugestões jurídicas textuais sem confundir proposta e parecer.

Apenas os nomes de processos cadastrados e hipóteses identificáveis são aceitos.
O usuário pode posteriormente confirmar a avaliação jurídica no painel.
"""
import re

from .interview_flow import normalizar

FUNDAMENTOS = re.compile(
    r"\bart\.?\s*(?:7|11)\s*[ºo°]?\b|\bobrigac[aã]o legal\b|"
    r"\bexecuc[aã]o de contrato\b|\bprocedimentos preliminares\b|"
    r"\bleg[ií]timo interesse\b|\bconsentimento\b|"
    r"\bexerc[ií]cio regular de direitos\b", re.IGNORECASE)


def extrair_sugestoes(ent, texto):
    """Retorna (processo, proposta) só de linhas com fundamento verificável.

    Não interpreta texto avulso como certeza nem cria processos novos.
    """
    encontrados = {}
    for linha in texto.splitlines():
        original = linha.strip().strip("| ")
        if not original:
            continue
        for processo in ent.get("processos", []):
            nome = processo.get("nome", "").strip()
            if not nome or not normalizar(original).startswith(normalizar(nome)):
                continue
            resto = original[len(nome):].strip(" \t|:–—-")
            if resto and FUNDAMENTOS.search(resto) and len(resto) <= 1200:
                encontrados[nome] = resto
            break
    return encontrados


def registrar_sugestoes(ent, texto):
    """Registra propostas explicitamente enviadas; nunca valida automaticamente."""
    encontrados = extrair_sugestoes(ent, texto)
    quantidade = 0
    for processo in ent.get("processos", []):
        proposta = encontrados.get(processo["nome"])
        if not proposta:
            continue
        campos = processo.setdefault("campos", {})
        anterior = campos.get("base_legal", {})
        if anterior.get("validacao_juridica") == "validado" or (anterior.get("manual") and anterior.get("validacao_juridica") != "pendente"):
            continue
        if anterior.get("valor") == proposta:
            continue
        campos["base_legal"] = {
            "valor": proposta,
            "implicito": False,
            "origem": "sugestao_do_entrevistado",
            "validacao_juridica": "pendente",
        }
        quantidade += 1
    return quantidade


def recuperar_do_historico(ent):
    """Recupera propostas de entrevistas antigas quando uma ação pede revisão."""
    total = 0
    for mensagem in ent.get("mensagens", []):
        if mensagem.get("role") == "user":
            total += registrar_sugestoes(ent, mensagem.get("texto", ""))
    return total
