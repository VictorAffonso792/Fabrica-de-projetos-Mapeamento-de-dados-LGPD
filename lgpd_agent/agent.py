"""Extração com Gemini + roteiro auditável: sem conclusão prematura do mapeamento."""
import json
import re
import time

from .constants import CHAVES
from .config import PERGUNTAS_NATURAIS
from .gemini import gemini, texto_de
from .interview_flow import (controle, definir_proxima_resposta, lacunas_detalhadas,
                             resumo_pendencias, normalizar)
from .mapping import achar_processo, executar_tool
from .prompts import (PROMPT_ENTREVISTA, PROMPT_MAPEAMENTO, PROMPT_PERGUNTA, SCHEMA_MAPEAMENTO,
                      TOOLS_TURNO, TOOL_CONFIG_TURNO)


def contexto(ent):
    """Estado do mapa, pendências objetivas, alvo da pergunta e conversa recente."""
    processos = []
    for p in ent.get("processos", []):
        processos.append({"nome": p["nome"], "campos": {
            k: {"valor": v.get("valor", ""), "manual": bool(v.get("manual"))}
            for k, v in p.get("campos", {}).items() if k in CHAVES and v.get("valor")
        }})
    msgs = ent.get("mensagens", [])
    recentes = [{"autor": "IA" if x["role"] == "model" else "Líder", "texto": x["texto"]}
               for x in msgs[-10:]]
    c = ent.get("controle_entrevista") or {}
    return json.dumps({
        "departamento": ent.get("departamento", ""), "processos": processos,
        "campos_pendentes": lacunas_detalhadas(ent),
        "pergunta_alvo": c.get("pergunta_atual"),
        "ultima_resposta_usuario": msgs[-1]["texto"] if msgs and msgs[-1]["role"] == "user" else "",
        "mensagens_recentes": recentes,
    }, ensure_ascii=False)


def _base_legal_confiavel(item, ent, atualizacoes):
    """Não contabiliza texto genérico como base legal preenchida.

    A proposta nunca substitui uma avaliação jurídica. Para tratamento sensível,
    a sugestão automática é deliberadamente bloqueada.
    """
    if item["campo"] != "base_legal":
        return True
    if not item.get("implicito"):
        return False
    valor = normalizar(item["valor"])
    if any(t in valor for t in ("a definir", "a validar", "pendente", "analisar", "nao informad", "revisar", "hipotese a")):
        return False
    if not (re.search(r"\bart\.?\s*(7|11)\b", valor)
            or any(t in valor for t in ("obrigacao legal", "execucao de contrato", "consentimento",
                                    "legitimo interesse", "exercicio regular de direitos",
                                    "protecao da vida", "tutela da saude"))):
        return False
    p = achar_processo(ent, item["processo"], criar=False)
    sensiveis = p.get("campos", {}).get("dados_sensiveis", {}).get("valor", "") if p else ""
    if not sensiveis:
        for upd in atualizacoes:
            if (normalizar(upd.get("processo", "")) == normalizar(item["processo"])
                    and upd.get("campo") == "dados_sensiveis"):
                sensiveis = upd["valor"]
    resposta = normalizar(sensiveis).strip()
    ausencia = any(resposta.startswith(s) for s in ("nao", "nenhum", "inexistente", "sem dados sensiveis"))
    if resposta and not ausencia:
        return False
    return True


def _dados_do_turno(partes):
    """Lê os argumentos da ferramenta registrar_mapeamento chamada pelo Gemini.

    Se o modelo responder em texto JSON (compatibilidade), usa o texto.
    """
    for parte in partes:
        if isinstance(parte, dict) and isinstance(parte.get("functionCall"), dict):
            chamada = parte["functionCall"]
            if chamada.get("name") == "registrar_mapeamento":
                return chamada.get("args") or {}
    return json.loads(texto_de(partes))


def formular_pergunta(ent, ultima, pergunta_base):
    """O Python escolhe O QUE perguntar; o Gemini escolhe COMO perguntar.

    Se a chamada falhar ou a resposta parecer fora do formato, usa a pergunta fixa do roteiro.
    """
    if not PERGUNTAS_NATURAIS:
        return pergunta_base
    entrada = json.dumps({"departamento": ent.get("departamento", ""),
                          "ultima_resposta_do_lider": ultima[-1500:],
                          "pergunta_obrigatoria": pergunta_base}, ensure_ascii=False)
    try:
        texto = texto_de(gemini({
            "system_instruction": {"parts": [{"text": PROMPT_PERGUNTA}]},
            "contents": [{"role": "user", "parts": [{"text": entrada}]}],
        }))
    except Exception as erro:  # a pergunta fixa garante que a entrevista continue
        print(f"[turno] pergunta natural indisponível ({type(erro).__name__}); usando roteiro fixo")
        return pergunta_base
    if not texto or len(texto) > 600 or texto.lstrip().startswith(("{", "[")) or "?" not in texto:
        return pergunta_base
    return texto


def turno_agente(ent):
    """Um pedido estruturado; o controle de perguntas fica no servidor Python."""
    inicio = time.perf_counter()
    payload = {
        "system_instruction": {"parts": [{"text": PROMPT_ENTREVISTA}]},
        "contents": [{"role": "user", "parts": [{"text": contexto(ent)}]}],
        "tools": TOOLS_TURNO,
        "toolConfig": TOOL_CONFIG_TURNO,
    }
    partes = gemini(payload)
    try:
        dados = _dados_do_turno(partes)
    except (ValueError, TypeError) as erro:
        raise RuntimeError("O Gemini devolveu uma resposta inválida. Tente reenviar a mensagem.") from erro
    if not isinstance(dados, dict) or not isinstance(dados.get("resposta"), str):
        raise RuntimeError("O Gemini retornou uma resposta incompleta. Tente novamente.")
    updates = dados.get("atualizacoes", [])
    if not isinstance(updates, list) or len(updates) > 80:
        raise RuntimeError("O Gemini retornou atualizações inválidas.")
    validadas = []
    for item in updates:
        if not isinstance(item, dict):
            raise RuntimeError("O Gemini retornou dados de mapeamento inválidos.")
        if not all(isinstance(item.get(k), str) for k in ("processo", "campo", "valor")):
            raise RuntimeError("O Gemini retornou campos inválidos.")
        if (item["campo"] not in CHAVES or not item["processo"].strip()
                or not item["valor"].strip() or not isinstance(item.get("implicito"), bool)):
            continue
        validadas.append(item)

    registros = []
    depto = dados.get("departamento", "")
    if isinstance(depto, str) and depto.strip() and normalizar(depto) != normalizar(ent.get("departamento", "")):
        _, evento = executar_tool(ent, "definir_departamento", {"nome": depto[:120]})
        if evento:
            registros.append(evento)

    for item in validadas:
        if not _base_legal_confiavel(item, ent, validadas):
            continue
        _, evento = executar_tool(ent, "registrar_informacao", item)
        if evento:
            registros.append(evento)

    ultima = next((m["texto"] for m in reversed(ent.get("mensagens", [])) if m["role"] == "user"), "")
    texto = definir_proxima_resposta(ent, ultima, len(registros))
    chamadas = 1
    if controle(ent).get("pergunta_atual"):  # há uma pergunta nova do roteiro para fazer
        texto = formular_pergunta(ent, ultima, texto)
        chamadas += int(PERGUNTAS_NATURAIS)
    duracao = round(time.perf_counter() - inicio, 3)
    ent["mensagens"].append({
        "role": "model", "texto": texto, "tools": registros,
        "metricas": {"duracao_s": duracao, "chamadas_turno": chamadas},
    })
    op, jur = resumo_pendencias(ent)
    print(f"[turno] duracao={duracao:.2f}s chamadas_logicas={chamadas} atualizacoes={len(registros)} pendencias_operacionais={len(op)} pendencias_juridicas={len(jur)}")


def atualizar_mapeamento(ent):
    """Reconstrói com IA sem apagar edições manuais; reinicia alvo de pergunta."""
    transcricao = "\n".join(
        f"{'Entrevistador' if m['role'] == 'model' else 'Líder do setor'}: {m['texto']}"
        for m in ent["mensagens"][1:])
    partes = gemini({
        "system_instruction": {"parts": [{"text": PROMPT_MAPEAMENTO}]},
        "contents": [{"role": "user", "parts": [{"text": transcricao}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA_MAPEAMENTO},
    })
    try:
        novo = json.loads(texto_de(partes))
    except (ValueError, TypeError) as erro:
        raise RuntimeError("Não foi possível interpretar a reconstrução do mapeamento.") from erro
    if not isinstance(novo, dict) or not isinstance(novo.get("processos"), list):
        raise RuntimeError("Formato de mapeamento inválido.")
    antigos = ent["processos"]
    reconstruido = {**ent, "processos": []}
    for item in novo["processos"]:
        if not isinstance(item, dict) or not isinstance(item.get("nome"), str) or not item["nome"].strip():
            continue
        p = achar_processo(reconstruido, item["nome"])
        for c in item.get("campos", []):
            if (isinstance(c, dict) and c.get("campo") in CHAVES
                    and isinstance(c.get("valor"), str) and c["valor"].strip()):
                item_legal = {"campo": c["campo"], "processo": item["nome"],
                              "valor": c["valor"], "implicito": bool(c.get("implicito"))}
                if _base_legal_confiavel(item_legal, reconstruido, [
                    {"processo": item["nome"], **x} for x in item.get("campos", []) if isinstance(x, dict)
                ]):
                    p["campos"][c["campo"]] = {"valor": c["valor"], "implicito": bool(c.get("implicito"))}
    for velho in antigos:
        manuais = {k: v for k, v in velho["campos"].items()
                   if v.get("manual") or (k == "base_legal" and v.get("origem") == "sugestao_do_entrevistado")}
        if manuais:
            achar_processo(reconstruido, velho["nome"])["campos"].update(manuais)
    ent["processos"] = reconstruido["processos"]
    c = controle(ent)
    c["pergunta_atual"] = None
    c["adiadas"] = {}
    c["outros_processos_perguntado"] = False
    c["sem_outros_processos"] = False
    ent["desatualizado"] = False
