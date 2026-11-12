"""Estado do mapeamento e execução de ferramentas chamadas pela IA."""
from .constants import CHAVES, NOMES
from .interview_flow import lacunas_detalhadas, normalizar

def achar_processo(ent, nome, criar=True):
    # normalizar() ignora maiúsculas e acentos: "Admissão" e "admissao" são o mesmo processo.
    alvo = normalizar(nome).strip()
    for p in ent["processos"]:
        if normalizar(p["nome"]).strip() == alvo:
            return p
    if not criar:
        return None
    p = {"nome": nome.strip(), "campos": {}}
    ent["processos"].append(p)
    return p

def lacunas(ent):
    """Mesma regra de interview_flow.lacunas_detalhadas, com os nomes legíveis dos campos."""
    return [{"processo": d["processo"], "faltando": [NOMES[c] for c in d["campos"]]}
            for d in lacunas_detalhadas(ent)]

def executar_tool(ent, nome, args):
    """Executa uma ferramenta chamada pela IA. Retorna (resposta para a IA, texto para a tela)."""
    if nome == "definir_departamento":
        ent["departamento"] = args.get("nome", "").strip()
        if ent["titulo"].startswith("Entrevista "):
            ent["titulo"] = f"{ent['departamento']} - {ent['criado'][:10]}"
        return {"ok": True}, f"Departamento: {ent['departamento']}"

    if nome == "registrar_informacao":
        campo = args.get("campo")
        if campo not in CHAVES:
            return {"ok": False, "erro": "campo inválido"}, None
        p = achar_processo(ent, args.get("processo", "Processo"))
        atual = p["campos"].get(campo, {})
        if atual.get("manual"):  # não sobrescreve o que o usuário editou à mão
            return {"ok": False, "motivo": "campo editado manualmente pelo usuário"}, None
        valor = args.get("valor", "").strip()
        if atual.get("valor") == valor and bool(atual.get("implicito")) == bool(args.get("implicito")):
            return {"ok": True, "alterado": False}, None
        p["campos"][campo] = {"valor": valor, "implicito": bool(args.get("implicito"))}
        return {"ok": True}, f"{p['nome']} › {NOMES[campo].split(' (')[0]}"

    return {"erro": "ferramenta desconhecida"}, None
