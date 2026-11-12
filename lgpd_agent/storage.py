"""Persistência local compatível com JSON antigos e gravações atômicas."""
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from .config import PASTA
from .constants import CHAVES
from .report import markdown
from .interview_flow import resumo_pendencias


def caminho(id_):
    if not isinstance(id_, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", id_):
        raise FileNotFoundError(id_)
    return PASTA / f"{id_}.json"


def carregar(id_):
    return json.loads(caminho(id_).read_text(encoding="utf-8"))


def _escrever_atomico(arquivo, conteudo):
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(arquivo.parent),
                                         prefix=".gravando-", suffix=".tmp", delete=False) as f:
            temporario = Path(f.name)
            f.write(conteudo)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporario, arquivo)
    finally:
        if temporario and temporario.exists():
            temporario.unlink()


def salvar(ent):
    PASTA.mkdir(parents=True, exist_ok=True)
    ent["atualizado"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    _escrever_atomico(caminho(ent["id"]), json.dumps(ent, ensure_ascii=False, indent=2))
    _escrever_atomico(PASTA / f"{ent['id']}.md", markdown(ent))
    return ent


def resumo(e):
    processos = e.get("processos", [])
    preenchidos = sum(bool(p.get("campos", {}).get(c, {}).get("valor")) for p in processos for c in CHAVES)
    total = len(processos) * len(CHAVES)
    oper, jur = resumo_pendencias(e)
    return {"id": e["id"], "titulo": e.get("titulo", "Entrevista"),
            "departamento": e.get("departamento", ""), "atualizado": e.get("atualizado", ""),
            "processos": len(processos), "preenchidos": preenchidos,
            "pendentes": total - preenchidos, "progresso": round(100 * preenchidos / total) if total else 0,
            "desatualizado": bool(e.get("desatualizado")),
            "revisoes_juridicas": len(jur),
            "situacao": (e.get("controle_entrevista") or {}).get("situacao", "em_andamento"),
            "encerrada": bool((e.get("controle_entrevista") or {}).get("encerrada"))}


def listar():
    if not PASTA.exists():
        return []
    itens = []
    for arq in PASTA.glob("*.json"):
        try:
            itens.append(resumo(json.loads(arq.read_text(encoding="utf-8"))))
        except (ValueError, KeyError, OSError) as e:
            print(f"[armazenamento] arquivo inválido ignorado: {arq.name} ({type(e).__name__})")
    return sorted(itens, key=lambda x: x["id"], reverse=True)


def excluir(id_):
    caminho(id_).unlink()
    md = PASTA / f"{id_}.md"
    if md.exists():
        md.unlink()
