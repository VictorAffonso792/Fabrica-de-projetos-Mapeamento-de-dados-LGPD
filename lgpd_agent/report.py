"""Exporta entrevistas e mapeamento para Markdown."""
from .constants import CHAVES, NOMES
from .mapping import lacunas
from .interview_flow import resumo_pendencias

def markdown(ent):
    """Gera a documentação da entrevista em Markdown."""
    l = [f"# {ent['titulo']}", "",
         f"- **Departamento:** {ent.get('departamento') or 'não informado'}",
         f"- **Criada em:** {ent['criado']}", f"- **Atualizada em:** {ent['atualizado']}", "",
         "## Mapeamento de dados (registro das operações de tratamento)", ""]
    if not ent["processos"]:
        l += ["_Nenhum processo mapeado ainda._", ""]
    for p in ent["processos"]:
        l += [f"### {p['nome']}", "", "| Campo | Informação |", "|---|---|"]
        for c in CHAVES:
            info = p["campos"].get(c)
            if info and info.get("valor"):
                marca = " _(implícito)_" if info.get("implicito") else ""
                marca += " _(editado manualmente)_" if info.get("manual") else ""
                if c == "base_legal":
                    marca += " _(validada pelo responsável)_" if info.get("validacao_juridica") == "validado" else " _(sugestão pendente de revisão jurídica)_"
                valor = info["valor"].replace("|", "/").replace("\n", " ")
                l.append(f"| {NOMES[c]} | {valor}{marca} |")
            else:
                l.append(f"| {NOMES[c]} | **não informado** |")
        l.append("")
    operacionais, juridicas = resumo_pendencias(ent)
    if juridicas:
        l += ["## Revisão jurídica necessária", "", "As bases legais abaixo requerem validação jurídica. Algumas podem conter **sugestões preliminares**, que não representam parecer ou aprovação:", ""]
        l += [f"- **{x['processo']}**: base legal pendente de validação." for x in juridicas]
        l.append("")
    # A base legal já aparece em "Revisão jurídica necessária"; aqui ficam só as lacunas operacionais.
    base = NOMES["base_legal"]
    pend = [{"processo": x["processo"], "faltando": [n for n in x["faltando"] if n != base]}
            for x in lacunas(ent)]
    pend = [x for x in pend if x["faltando"]]
    if pend:
        l += ["## Lacunas (perguntar ao líder do setor)", ""]
        l += [f"- **{x['processo']}:** {', '.join(n.split(' (')[0] for n in x['faltando'])}" for x in pend]
        l.append("")
    l += ["## Transcrição da entrevista", ""]
    for m in ent["mensagens"][1:]:
        quem = "Entrevistador (IA)" if m["role"] == "model" else "Líder do setor"
        editado = " _(editado)_" if m.get("editado") else ""
        l += [f"**{quem}:**{editado} {m['texto']}", ""]
    return "\n".join(l)
