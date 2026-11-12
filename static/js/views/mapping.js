/** Formulário editável com os doze campos do registro LGPD. */
import { $, state, FIELD_GROUPS, el, button, icon, empty, count, pct, avisoPendencias } from "../core.js";
import { mutate, editarProcesso, removerProcesso } from "../actions.js";
function renderProcesses() {
  const ent = state.ent, container = $("mapa");
  container.replaceChildren();
  $("processEntName").textContent = ent ? ent.titulo : "Nenhuma entrevista selecionada";
  $("processEntDesc").textContent = ent ? (ent.departamento || "Departamento não definido") + " · " + ent.processos.length + " processo(s) identificado(s)" : "Selecione uma entrevista na aba Entrevistas.";
  $("addProcesso").disabled = !ent;
  $("atualizarMapaCompleto").disabled = !ent;
  $("recuperarBases").disabled = !ent;
  if (!ent) {
    container.append(empty("Selecione uma entrevista", "Abra o histórico para consultar os processos.", "list"));
    return;
  }
  if (ent.desatualizado) {
    const note = el("div", "notice");
    note.append(icon("info"), document.createTextNode("O mapeamento precisa ser reconstruído para considerar as respostas editadas."));
    container.append(note);
  }
  if (!ent.processos.length) {
    container.append(empty("Sem processos mapeados", "Converse com a IA ou cadastre um processo manualmente.", "list"));
    return;
  }
  ent.processos.forEach((p, pi) => {
    const card = el("div", "panel process-card"), head = el("div", "process-title"), letter = el("div", "process-letter", (p.nome || "P")[0].toUpperCase()), name = el("div", "process-name");
    name.append(el("h2", "", p.nome), el("small", "", count(p) + " de " + state.campos.length + " campos preenchidos"));
    const actions = el("div", "process-actions"), r = button("", "icon-btn", () => editarProcesso(pi, p.nome), "pen"), d = button("", "icon-btn", () => removerProcesso(pi, p.nome), "trash");
    r.title = "Renomear processo";
    r.setAttribute("aria-label", "Renomear " + p.nome);
    d.title = "Excluir processo";
    d.setAttribute("aria-label", "Remover " + p.nome);
    actions.append(r, d);
    head.append(letter, name, actions);
    card.append(head);
    const prog = el("div", "process-top-progress"), bar = el("div", "bar"), fill = el("span");
    fill.style.width = pct(p) + "%";
    bar.append(fill);
    prog.append(bar, el("span", "", pct(p) + "% preenchido"));
    card.append(prog, avisoPendencias(p));
    const groups = el("div", "field-groups");
    FIELD_GROUPS.forEach(([title, keys], gi) => {
      const detail = el("details", "field-group");
      if (gi === 0 || (pi === 0 && gi === 1))
        detail.open = true;
      const summary = el("summary");
      summary.append(icon("chevron"), document.createTextNode(title));
      const filled = keys.filter(key => p.campos && p.campos[key] && p.campos[key].valor).length;
      summary.append(el("span", "group-counter", filled + "/" + keys.length));
      detail.append(summary);
      const fields = el("div", "field-group-fields");
      keys.forEach(key => {
        const item = state.campos.find(([k]) => k === key);
        if (!item)
          return;
        const info = (p.campos && p.campos[key]) || {}, row = el("div"), lab = el("label", "field-label"), ta = el("textarea", "field-input");
        const uid = "field-" + pi + "-" + key;
        lab.setAttribute("for", uid);
        lab.append(document.createTextNode(item[1]));
        if (info.implicito)
          lab.append(el("span", "tag inferred", "Inferido pela IA"));
        if (info.manual)
          lab.append(el("span", "tag edited", "Editado manualmente"));
        if (key === "base_legal" && info.valor)
          lab.append(el("span", "tag " + (info.validacao_juridica === "validado" ? "edited" : "inferred"),
            info.validacao_juridica === "validado" ? "Validada" : "Sugestão não validada"));
        ta.id = uid;
        ta.rows = 2;
        ta.placeholder = key === "base_legal" ? "Pendente de validação jurídica — preencher após análise" : "Não informado — clique para editar";
        ta.value = info.valor || "";
        ta.addEventListener("change", async () => {
          if (ta.value === (info.valor || ""))
            return;
          const ok = await mutate("campo", { processo: pi, campo: key, valor: ta.value });
          if (!ok) {
            ta.value = info.valor || "";
          }
        });
        row.append(lab, ta);
        if (key === "base_legal" && info.valor) {
          const checked = info.validacao_juridica === "validado";
          const legalActions = el("div", "legal-validation");
          legalActions.append(el("span", "", checked ? "Revisão jurídica registrada." : "A sugestão ainda não foi validada pelo responsável jurídico."));
          const mark = button(checked ? "Desfazer validação" : "Registrar validação jurídica", "btn btn-outline btn-sm", async () => {
            if (!checked && !confirm("Confirma que o responsável jurídico realmente validou esta base legal? O sistema não realiza validação automática.")) return;
            await mutate("validar_base", { processo: pi, validado: !checked });
          }, "check");
          legalActions.append(mark);
          row.append(legalActions);
        }
        fields.append(row);
      });
      detail.append(fields);
      groups.append(detail);
    });
    card.append(groups);
    container.append(card);
  });
}
export { renderProcesses };
