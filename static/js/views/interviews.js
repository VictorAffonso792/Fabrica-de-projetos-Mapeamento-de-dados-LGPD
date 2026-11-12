/** Histórico, mensagens, edição e mapa resumido da entrevista. */
import { $, state, el, button, icon, empty, count, pct, avisoPendencias, toast } from "../core.js";
import { abrir, navigate, mutate, renomearEntrevista, excluirEntrevista } from "../actions.js";
function renderList() {
  const list = $("lista");
  list.replaceChildren();
  const query = state.query.toLocaleLowerCase("pt-BR");
  const filtered = state.items.filter(it => (it.titulo + " " + (it.departamento || "")).toLocaleLowerCase("pt-BR").includes(query));
  if (!filtered.length) {
    list.append(empty(query ? "Nenhum resultado" : "Sem entrevistas", query ? "Tente outro termo." : "Clique em Nova entrevista para começar.", "chat"));
    return;
  }
  filtered.forEach(it => {
    const row = el("div", "interview-item" + (state.ent && state.ent.id === it.id ? " current" : ""));
    const op = button("", "interview-open", async () => { await abrir(it.id); navigate("entrevistas"); });
    op.append(el("div", "interview-title", it.titulo), el("div", "interview-details", (it.departamento || "Sem departamento") + " · " + it.processos + " processo(s)"));
    const foot = el("div", "interview-bottom"), bar = el("div", "small-progress"), inside = el("span");
    inside.style.width = (it.progresso || 0) + "%";
    bar.append(inside);
    foot.append(bar, el("span", "tiny-perc", (it.progresso || 0) + "%"));
    const badges = el("div", "interview-badges");
    badges.append(el("span", "interview-state " + (it.encerrada ? "closed" : "ongoing"), it.encerrada ? "Encerrada" : "Em andamento"));
    if (it.revisoes_juridicas) badges.append(el("span", "interview-juridical", it.revisoes_juridicas + " revisão(ões) jurídica(s)"));
    op.append(foot, badges);
    const actions = el("div", "item-actions"), ren = button("", "icon-btn", () => renomearEntrevista(it), "pen"), del = button("", "icon-btn", () => excluirEntrevista(it), "trash");
    ren.title = "Renomear";
    ren.setAttribute("aria-label", "Renomear " + it.titulo);
    del.title = "Excluir";
    del.setAttribute("aria-label", "Excluir " + it.titulo);
    actions.append(ren, del);
    row.append(op, actions);
    list.append(row);
  });
}
function renderChat() {
  const feed = $("chat"), ent = state.ent;
  $("titulo").textContent = ent ? ent.titulo : "Assistente de privacidade";
  $("subtitulo").textContent = ent ? (ent.departamento || "Entrevista em andamento") + " · registro assistido por IA" : "Selecione uma entrevista para começar";
  $("renomearBtn").disabled = !ent;
  const fechada = Boolean(ent?.controle_entrevista?.encerrada);
  $("encerrarEntrevista").disabled = !ent || state.busy;
  $("encerrarEntrevista").textContent = fechada ? "Reabrir entrevista" : "Encerrar entrevista";
  $("encerrarEntrevista").classList.toggle("closed-action", fechada);
  $("statusEntrevista").textContent = !ent ? "" : fechada ? "Encerrada" : "Em andamento";
  $("statusEntrevista").className = "interview-status " + (fechada ? "closed" : "active");
  $("avisoEncerrada").hidden = !fechada;
  $("chatCompose").hidden = fechada;
  feed.replaceChildren();
  if (!ent) {
    feed.append(empty("Sua conversa começa aqui", "Inicie ou selecione uma entrevista no histórico.", "chat"));
    return;
  }
  ent.mensagens.forEach((m, i) => {
    if (i === 0)
      return;
    const mine = m.role === "user";
    const row = el("div", "message-row" + (mine ? " mine" : ""));
    const avatar = el("span", "bubble-avatar", mine ? "EU" : "IA"), wrap = el("div", "msg-wrap"), content = el("div", "msg", m.texto);
    wrap.append(content);
    if (Array.isArray(m.tools) && m.tools.length) {
      const tools = el("div", "message-tools");
      m.tools.slice(0, 16).forEach(t => tools.append(el("span", "tool", "✓ " + t)));
      wrap.append(tools);
    }
    const meta = el("div", "message-meta");
    if (m.editado)
      meta.append(document.createTextNode("Resposta editada · "));
    if (mine) {
      const b = button("Editar resposta", "", () => editMessage(i, m.texto, wrap));
      meta.append(b);
    }
    if (meta.childNodes.length)
      wrap.append(meta);
    row.append(avatar, wrap);
    feed.append(row);
  });
  if (state.busy && state.loading) {
    const row = el("div", "message-row"), avatar = el("span", "bubble-avatar", "IA"), wrap = el("div", "thinking", "Analisando sua resposta");
    for (let i = 0; i < 3; i++)
      wrap.append(el("i"));
    row.append(avatar, wrap);
    feed.append(row);
  }
  feed.scrollTop = feed.scrollHeight;
}
function editMessage(index, original, wrap) {
  if (state.busy)
    return toast("Aguarde o fim da resposta atual.", true);
  wrap.replaceChildren();
  const bar = el("div", "inline-editor"), textarea = el("textarea");
  textarea.value = original;
  const actions = el("div");
  actions.style.display = "grid";
  actions.style.gap = "4px";
  actions.append(button("Salvar", "btn btn-primary", async () => {
    if (!textarea.value.trim())
      return toast("Informe uma resposta.", true);
    await mutate("editar", { indice: index, texto: textarea.value });
  }), button("Cancelar", "btn", renderChat));
  bar.append(textarea, actions);
  wrap.append(bar);
  textarea.focus();
}
function renderLive() {
  const box = $("mapaResumo");
  box.replaceChildren();
  const ent = state.ent;
  if (!ent) {
    box.append(empty("Nenhum processo selecionado", "Escolha uma entrevista para ver o preenchimento ao vivo.", "list"));
    return;
  }
  if (ent.desatualizado) {
    const note = el("div", "notice");
    note.append(icon("info"), document.createTextNode("Respostas editadas. Reconstrua o mapeamento para aplicar as correções."));
    box.append(note);
  }
  if (!ent.processos.length) {
    box.append(empty("Aguardando identificação", "A IA criará processos conforme você responder.", "list"));
    return;
  }
  ent.processos.forEach(p => {
    const card = el("div", "live-proc");
    card.append(el("strong", "", p.nome), el("div", "live-sub", count(p) + " de " + state.campos.length + " campos preenchidos"));
    const bar = el("div", "bar"), fill = el("span");
    fill.style.width = pct(p) + "%";
    bar.append(fill);
    card.append(bar, avisoPendencias(p));
    const facts = el("ul", "live-facts");
    state.campos.filter(([key]) => p.campos[key] && p.campos[key].valor).slice(0, 3).forEach(([key, label]) => {
      const li = el("li");
      li.append(icon("check"), document.createTextNode(label.split(" (")[0]));
      facts.append(li);
    });
    card.append(facts);
    box.append(card);
  });
}
export { renderList, renderChat, renderLive };
