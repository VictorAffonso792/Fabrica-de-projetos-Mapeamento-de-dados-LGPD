"""Motor de entrevista: perguntas, pendências jurídicas e encerramento real.

A IA extrai fatos; o Python verifica o estado e decide o próximo passo.  Um
mapeamento pode ser encerrado com pendências (sem fingir 100% de validação).
"""
import re
import unicodedata

from .constants import CHAVES, NOMES

CAMPOS_OPERACIONAIS = tuple(c for c in CHAVES if c != "base_legal")

PERGUNTAS = {
    "finalidade": "Qual é a finalidade principal da atividade '{processo}'?",
    "titulares": "De quais pessoas são os dados tratados na atividade '{processo}'?",
    "dados_pessoais": "Quais dados pessoais específicos são usados em '{processo}'?",
    "dados_sensiveis": "Em '{processo}', são tratados dados sensíveis, como saúde ou biometria? Se não, diga 'não'.",
    "justificativa": "Por que essas categorias de dados são necessárias em '{processo}'?",
    "coleta": "Como os dados são coletados em '{processo}'? Por exemplo, por formulário, mensagem ou pessoalmente.",
    "armazenamento": "Onde e como os dados de '{processo}' são armazenados?",
    "retencao": "Por quanto tempo os dados de '{processo}' ficam armazenados e como são descartados?",
    "compartilhamento": "Com quem os dados de '{processo}' são compartilhados, dentro e fora da empresa?",
    "transferencia_internacional": "Os dados de '{processo}' são enviados ou acessados de outro país? Se não, diga 'não'.",
    "seguranca": "Quais medidas protegem os dados de '{processo}'? Se não houver nenhuma, pode informar isso.",
}


# Campos perguntados juntos, na ordem da entrevista (mesmos grupos da tela de Mapeamento).
GRUPOS = (
    ("finalidade", "justificativa"),
    ("titulares", "dados_pessoais", "dados_sensiveis"),
    ("coleta",),
    ("armazenamento", "retencao"),
    ("compartilhamento", "transferencia_internacional"),
    ("seguranca",),
)

PERGUNTAS_GRUPO = {
    ("finalidade", "justificativa"):
        "Qual é a finalidade principal da atividade '{processo}' e por que os dados usados nela são necessários?",
    ("titulares", "dados_pessoais", "dados_sensiveis"):
        "Na atividade '{processo}', de quais pessoas são os dados, quais dados pessoais vocês usam e há algum dado "
        "sensível, como saúde ou biometria? Se não houver dado sensível, pode dizer 'não'.",
    ("armazenamento", "retencao"):
        "Onde os dados de '{processo}' ficam armazenados, por quanto tempo são guardados e como são descartados?",
    ("compartilhamento", "transferencia_internacional"):
        "Com quem os dados de '{processo}' são compartilhados, dentro e fora da empresa? Algum deles é enviado "
        "ou acessado de outro país?",
}


ORDEM_CAMPOS = {campo: i for i, campo in enumerate(c for g in GRUPOS for c in g)}
ORDEM_CAMPOS["base_legal"] = len(ORDEM_CAMPOS)


def grupo_de(campo):
    return next((g for g in GRUPOS if campo in g), (campo,))


def montar_pergunta(processo, campos):
    """Usa a pergunta do grupo quando todos os campos dele estão pendentes; senão junta as individuais."""
    chave = tuple(campos)
    if chave in PERGUNTAS_GRUPO:
        return PERGUNTAS_GRUPO[chave].format(processo=processo)
    return " ".join(PERGUNTAS[c].format(processo=processo) for c in campos)


def normalizar(texto):
    valor = unicodedata.normalize("NFKD", str(texto).casefold())
    return "".join(c for c in valor if not unicodedata.combining(c))


def chave_alvo(processo, campo):
    return f"{normalizar(processo).strip()}::{campo}"


def base_legal_pendente(info):
    """Uma proposta textual não equivale à validação jurídica."""
    if not info or not info.get("valor"):
        return True
    estado = info.get("validacao_juridica")
    if estado == "validado":
        return False
    if estado == "pendente":
        return True
    # Inclusive edições manuais antigas precisam ser confirmadas: preenchimento
    # de texto não é evidência de validação jurídica.
    return True


def campo_contabilizado(processo, campo):
    """Campo documentado pode estar sujeito a revisão; não significa aprovação."""
    return bool(processo.get("campos", {}).get(campo, {}).get("valor"))


def lacunas_detalhadas(ent):
    return [{"processo": p["nome"], "campos": [c for c in CHAVES if not campo_contabilizado(p, c)]}
            for p in ent.get("processos", [])]


def resumo_pendencias(ent):
    detalhes = lacunas_detalhadas(ent)
    operacionais = [{"processo": d["processo"], "campo": c}
                   for d in detalhes for c in d["campos"] if c != "base_legal"]
    juridicas = [{"processo": p["nome"], "campo": "base_legal"}
                for p in ent.get("processos", [])
                if base_legal_pendente(p.get("campos", {}).get("base_legal"))]
    return operacionais, juridicas


def controle(ent):
    c = ent.setdefault("controle_entrevista", {})
    c.setdefault("pergunta_atual", None)
    c.setdefault("adiadas", {})
    c.setdefault("outros_processos_perguntado", False)
    c.setdefault("sem_outros_processos", False)
    c.setdefault("encerrada", False)
    return c


def solicita_encerramento(texto):
    """Comando de encerramento do entrevistado, sem confundir com dúvida."""
    s = normalizar(texto).strip()
    if re.search(r"\b(nao|nunca)\s+(pode|quero|vamos|devemos)\s+(encerrar|finalizar)\b", s):
        return False
    padroes = (
        r"\b(pode|podemos|quero|desejo|vamos|autorizo|confirmo|solicito)\b.{0,40}\b(encerrar|finalizar|encerramento)\b",
        r"\b(encerrar|finalizar)\s+(a\s+)?(entrevista|mapeamento|coleta)\b",
        r"\b(nao|nenhuma)\s+(sao|e)\s+necessari[ao]s?\s+novas?\s+perguntas?\b",
    )
    return any(re.search(p, s) for p in padroes)


def _pede_status(texto):
    t = normalizar(texto)
    return ("?" in t and any(w in t for w in ("falta", "conclu", "termin", "complet", "mape", "penden", "12", "status", "processo"))) or any(
        w in t for w in ("11/12", "11 de 12", "por que falta", "pq falta", "quantos campos", "esta completo", "ja terminou"))


def _nega_outros_processos(texto):
    t = normalizar(texto).strip(" .!?\n\t")
    curtas = {"nao", "nenhum", "nenhuma", "nao tem", "nao existe", "acredito que nao",
              "so isso", "por enquanto nao", "isso e tudo"}
    if t in curtas:
        return True
    padroes = ("nao ha outras atividades", "nao existem outras atividades", "nao tem outras atividades",
               "todas as principais atividades", "nenhuma outra atividade", "sem outras atividades",
               "nao ha mais processos", "nao existem outros processos")
    return any(x in t for x in padroes) and not ("?" in texto)


def _resumo_status(operacional, juridico):
    partes = []
    if operacional:
        grupos = {}
        for d in operacional:
            grupos.setdefault(d["processo"], []).append(NOMES[d["campo"]].split(" (")[0])
        partes.append("Ainda faltam informações: " + "; ".join(
            f"{nome}: {', '.join(campos)}" for nome, campos in grupos.items()) + ".")
    if juridico:
        nomes = ", ".join(x["processo"] for x in juridico)
        partes.append("Revisão jurídica da base legal pendente em: " + nomes + ". "
                      "As sugestões documentadas não equivalem à aprovação jurídica.")
    if not partes:
        partes.append("Todos os campos estão documentados, sujeitos à revisão humana do registro.")
    return " ".join(partes)


def _esta_preenchido(ent, alvo):
    if not alvo or not isinstance(alvo, dict):
        return True
    for p in ent.get("processos", []):
        if normalizar(p["nome"]) == normalizar(alvo.get("processo", "")):
            return campo_contabilizado(p, alvo.get("campo", ""))
    return False


def resumo_encerramento(ent):
    operacional, juridico = resumo_pendencias(ent)
    if not ent.get("processos"):
        return "Entrevista encerrada sem processos cadastrados. Você pode reabri-la para continuar."
    resultado = ["Entrevista encerrada e registrada. Não farei novas perguntas."]
    if operacional:
        resultado.append(f"Restam {len(operacional)} informação(ões) operacional(is) não confirmada(s).")
    else:
        resultado.append("A coleta operacional foi finalizada.")
    if juridico:
        resultado.append(f"{len(juridico)} processo(s) exigem revisão jurídica da base legal, mesmo quando há sugestões registradas.")
    else:
        resultado.append("Não há bases legais pendentes no registro.")
    resultado.append("Essas pendências continuam visíveis no mapeamento e no relatório. Se precisar continuar, use 'Reabrir entrevista'.")
    return " ".join(resultado)


def encerrar_entrevista(ent):
    c = controle(ent)
    c["encerrada"] = True
    c["pergunta_atual"] = None
    c["sem_outros_processos"] = True
    operacional, juridico = resumo_pendencias(ent)
    c["situacao"] = "encerrada_com_pendencias" if (operacional or juridico) else "encerrada"
    return resumo_encerramento(ent)


def reabrir_entrevista(ent):
    c = controle(ent)
    c["encerrada"] = False
    c["pergunta_atual"] = None
    c["adiadas"] = {}
    c["outros_processos_perguntado"] = False
    c["sem_outros_processos"] = False
    c["situacao"] = "em_andamento"
    return "Entrevista reaberta. Você pode continuar respondendo ou editar o mapeamento."


def definir_proxima_resposta(ent, mensagem_usuario, quantidade_atualizacoes=0):
    """Próxima ação baseada em dados persistidos, não no texto livre da IA."""
    c = controle(ent)
    if c["encerrada"]:
        return resumo_encerramento(ent)

    # Encerramento explícito tem precedência mesmo com 11/12 campos.
    if solicita_encerramento(mensagem_usuario):
        return encerrar_entrevista(ent)

    anterior = c.get("pergunta_atual")
    pediu_status = _pede_status(mensagem_usuario)
    if anterior:
        campos_ant = anterior.get("campos") or [anterior["campo"]]
        alvos = [{"processo": anterior["processo"], "campo": campo} for campo in campos_ant]
        respondidos = [a for a in alvos if _esta_preenchido(ent, a)]
        for alvo in alvos:
            k = chave_alvo(alvo["processo"], alvo["campo"])
            if alvo in respondidos:
                c["adiadas"].pop(k, None)
            # Pergunta em grupo respondida em parte: o que faltou é perguntado sozinho em seguida.
            # Só adia quando ninguém do grupo foi respondido (ex.: "não sei").
            elif not pediu_status and (len(alvos) == 1 or not respondidos):
                c["adiadas"][k] = True
        c["pergunta_atual"] = None

    operacional, juridico = resumo_pendencias(ent)
    if not ent.get("processos"):
        c["situacao"] = "aguardando_processos"
        return "Quais atividades do seu departamento utilizam dados pessoais? Pode citar alguns exemplos?"

    if operacional:
        c["situacao"] = "coleta_pendente"
        c["sem_outros_processos"] = False
        c["outros_processos_perguntado"] = False
        if pediu_status:
            return _resumo_status(operacional, juridico) + " Para continuar, diga 'próximo campo' ou preencha diretamente no painel."
        disponiveis = [d for d in operacional if chave_alvo(d["processo"], d["campo"]) not in c["adiadas"]]
        if disponiveis:
            # Ordem da entrevista: processo por processo, grupo por grupo (termina um grupo antes do próximo).
            ordem_proc = {normalizar(p["nome"]): i for i, p in enumerate(ent["processos"])}
            disponiveis.sort(key=lambda d: (ordem_proc.get(normalizar(d["processo"]), 0), ORDEM_CAMPOS[d["campo"]]))
            proximo = disponiveis[0]
            mesmo_processo = {d["campo"] for d in disponiveis
                              if normalizar(d["processo"]) == normalizar(proximo["processo"])}
            campos = [x for x in grupo_de(proximo["campo"]) if x in mesmo_processo]
            c["pergunta_atual"] = {"processo": proximo["processo"], "campo": campos[0], "campos": campos}
            prefixo = "Informações registradas. " if quantidade_atualizacoes else ""
            return prefixo + montar_pergunta(proximo["processo"], campos)
        return ("Ainda existem informações operacionais não confirmadas. " + _resumo_status(operacional, juridico)
                + " Você pode preenchê-las no painel ou informar novos dados; não vou repetir perguntas automaticamente.")

    # Conclui a etapa operacional, mas nunca inventa validação jurídica.
    c["situacao"] = "revisao_juridica" if juridico else "revisao_humana"
    status = _resumo_status(operacional, juridico)
    if c.get("outros_processos_perguntado") and _nega_outros_processos(mensagem_usuario):
        return encerrar_entrevista(ent)
    if not c["outros_processos_perguntado"]:
        c["outros_processos_perguntado"] = True
        return ("A coleta das informações operacionais está completa. " + status
                + "\n\nExiste outra atividade com dados pessoais que precisamos registrar?")
    if c.get("sem_outros_processos"):
        return resumo_encerramento(ent)
    return status + " Se quiser encerrar, diga 'pode encerrar' ou use o botão Encerrar entrevista."
