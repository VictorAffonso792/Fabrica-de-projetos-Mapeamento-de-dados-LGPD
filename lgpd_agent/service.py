"""Casos de uso e serialização por entrevista (sem bloquear outras entrevistas)."""
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime

from .agent import atualizar_mapeamento, turno_agente
from .constants import ABERTURA, CHAVES
from .mapping import achar_processo
from .interview_flow import (controle, solicita_encerramento, encerrar_entrevista, reabrir_entrevista,
                             resumo_pendencias)
from .legal_suggestions import registrar_sugestoes, recuperar_do_historico
from .storage import carregar, salvar

_GUARDA = threading.Lock()


_MENSAGENS_INDICE = {
    "processo": ("Processo inválido.", "Processo não encontrado. Atualize a página e tente novamente."),
    "mensagem": ("Mensagem inválida.", "Mensagem não encontrada. Atualize a página e tente novamente."),
}


def _item(lista, indice, tipo="processo"):
    """Valida o índice vindo do navegador: rejeita negativos, texto e posições inexistentes."""
    invalido, inexistente = _MENSAGENS_INDICE[tipo]
    try:
        i = int(indice)
    except (TypeError, ValueError):
        raise ValueError(invalido) from None
    if i < 0 or i >= len(lista):
        raise ValueError(inexistente)
    return i
_TRAVAS = {}


@contextmanager
def trava_entrevista(id_):
    with _GUARDA:
        trava = _TRAVAS.setdefault(id_, threading.RLock())
    with trava:
        yield


def criar():
    """Abre imediatamente sem chamada Gemini; 1ª pergunta é fixa e adequada."""
    agora = datetime.now()
    id_ = agora.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    ent = {"id": id_, "titulo": f"Entrevista {agora:%d/%m/%Y %H:%M}",
           "departamento": "", "criado": agora.strftime("%d/%m/%Y %H:%M"), "atualizado": "",
           "mensagens": [{"role": "user", "texto": ABERTURA},
                         {"role": "model", "texto": "Olá! Sou seu assistente de mapeamento LGPD. Qual é o seu departamento e quais são as principais atividades realizadas nele?"}],
           "processos": [], "desatualizado": False,
           "controle_entrevista": {"pergunta_atual": None, "adiadas": {}, "outros_processos_perguntado": False, "sem_outros_processos": False, "encerrada": False}}
    with trava_entrevista(id_):
        return salvar(ent), None


def acao(id_, nome, corpo):
    with trava_entrevista(id_):
        ent = carregar(id_)
        if nome == "renomear":
            titulo = str(corpo.get("titulo", "")).strip()[:180]
            if titulo:
                ent["titulo"] = titulo
        elif nome == "mensagem":
            texto = str(corpo.get("texto", "")).strip()
            if not texto or len(texto) > 12000:
                raise ValueError("A mensagem deve conter de 1 a 12.000 caracteres.")
            if controle(ent)["encerrada"]:
                raise ValueError("Esta entrevista está encerrada. Clique em Reabrir para continuar.")
            ent["mensagens"].append({"role": "user", "texto": texto})
            # Encerrar não requer conexão externa nem deve gerar perguntas.
            if solicita_encerramento(texto):
                texto_ia = encerrar_entrevista(ent)
                ent["mensagens"].append({"role": "model", "texto": texto_ia, "tools": []})
            else:
                qtd = registrar_sugestoes(ent, texto)
                if qtd:
                    ent["mensagens"].append({"role": "model", "texto":
                        f"Registrei {qtd} sugestão(ões) de base legal como preliminares. "
                        "Elas estão documentadas, mas continuam aguardando validação jurídica. "
                        "Você pode encerrar a entrevista sem aprová-las.", "tools": []})
                else:
                    turno_agente(ent)  # só persiste se Gemini concluir sem erro
        elif nome == "encerrar":
            if not controle(ent)["encerrada"]:
                ent["mensagens"].append({"role": "model", "texto": encerrar_entrevista(ent), "tools": []})
        elif nome == "reabrir":
            recuperar_do_historico(ent)  # recupera sugestões antigas não registradas
            if controle(ent)["encerrada"]:
                ent["mensagens"].append({"role": "model", "texto": reabrir_entrevista(ent), "tools": []})
        elif nome == "validar_base":
            indice = _item(ent["processos"], corpo.get("processo"))
            valor = corpo.get("validado")
            if not isinstance(valor, bool):
                raise ValueError("A confirmação da revisão jurídica deve ser verdadeira ou falsa.")
            processo = ent["processos"][indice]
            info = processo.get("campos", {}).get("base_legal", {})
            if not info.get("valor"):
                raise ValueError("Registre uma proposta de base legal antes de validar.")
            info["validacao_juridica"] = "validado" if valor else "pendente"
            processo["campos"]["base_legal"] = info
        elif nome == "editar":
            i = _item(ent["mensagens"], corpo.get("indice"), "mensagem")
            if i < 1 or ent["mensagens"][i]["role"] != "user":
                raise ValueError("Só é possível editar mensagens do líder do setor.")
            texto = str(corpo.get("texto", "")).strip()
            if not texto:
                raise ValueError("A resposta não pode ficar vazia.")
            ent["mensagens"][i].update(texto=texto[:12000], editado=True)
            ent["desatualizado"] = True
        elif nome == "mapear":
            atualizar_mapeamento(ent)
            recuperar_do_historico(ent)
        elif nome == "recuperar_bases":
            recuperar_do_historico(ent)
        elif nome == "campo":
            if corpo.get("campo") not in CHAVES:
                raise ValueError("Campo inválido.")
            p = ent["processos"][_item(ent["processos"], corpo.get("processo"))]
            valor = str(corpo.get("valor", "")).strip()
            if len(valor) > 12000:
                raise ValueError("Campo muito longo.")
            if valor:
                anterior = p["campos"].get(corpo["campo"], {})
                info = {"valor": valor, "implicito": False, "manual": True}
                if corpo["campo"] == "base_legal":
                    # Editar uma proposta não significa que o jurídico aprovou.
                    info["validacao_juridica"] = "pendente" if valor != anterior.get("valor") else anterior.get("validacao_juridica", "pendente")
                p["campos"][corpo["campo"]] = info
            else:
                p["campos"].pop(corpo["campo"], None)
            controle(ent)["adiadas"] = {}
        elif nome == "processo":
            tipo = corpo.get("acao")
            if tipo in ("adicionar", "renomear"):
                nome_processo = str(corpo.get("nome", "")).strip()[:180]
                if not nome_processo:
                    raise ValueError("Informe o nome do processo.")
                if tipo == "adicionar":
                    achar_processo(ent, nome_processo)
                else:
                    ent["processos"][_item(ent["processos"], corpo.get("indice"))]["nome"] = nome_processo
            elif tipo == "remover":
                ent["processos"].pop(_item(ent["processos"], corpo.get("indice")))
            else:
                raise ValueError("Ação de processo inválida.")
        else:
            raise FileNotFoundError(nome)
        c = controle(ent)
        if c["encerrada"]:
            op, jur = resumo_pendencias(ent)
            c["situacao"] = "encerrada_com_pendencias" if (op or jur) else "encerrada"
        return salvar(ent)
