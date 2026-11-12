/**
 * Estado compartilhado, comunicação HTTP e componentes HTML reutilizáveis.
 * Este arquivo não decide regras de LGPD: elas ficam no servidor Python.
 */
const $ = (id) => document.getElementById(id);
const state = { ent: null, items: [], campos: [], view: "dashboard", busy: false, loading: false, query: "", selectedReport: "" };
const FIELD_GROUPS = [
  ["Identificação e finalidade", ["finalidade", "justificativa"]],
  ["Titulares e categorias de dados", ["titulares", "dados_pessoais", "dados_sensiveis"]],
  ["Coleta e tratamento", ["coleta"]],
  ["Armazenamento e retenção", ["armazenamento", "retencao"]],
  ["Compartilhamento e transferências", ["compartilhamento", "transferencia_internacional"]],
  ["Segurança e base legal", ["seguranca", "base_legal"]]
];
const NAMES = { dashboard: "Visão geral", entrevistas: "Entrevistas", processos: "Mapeamento", relatorios: "Relatórios", configuracoes: "Configurações" };
const icon = (name, cls = "icon") => {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("class", cls);
  s.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", "#i-" + name);
  s.append(use);
  return s;
};
function el(tag, cls = "", value) {
  const d = document.createElement(tag);
  if (cls)
    d.className = cls;
  if (value !== undefined)
    d.textContent = value;
  return d;
}
function button(label, cls, onClick, symbol) {
  const b = el("button", cls);
  b.type = "button";
  if (symbol)
    b.append(icon(symbol));
  if (label)
    b.append(document.createTextNode(label));
  b.onclick = onClick;
  return b;
}
let toastTimer;
function toast(message, error = false) {
  const d = $("toast");
  d.textContent = message;
  d.className = "toast show" + (error ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => d.className = "toast", error ? 6000 : 3300);
}
async function api(method, url, payload) {
  let response;
  try {
    response = await fetch(url, {
      method, headers: { "Content-Type": "application/json" },
      body: payload === undefined ? undefined : JSON.stringify(payload)
    });
  }
  catch (err) {
    throw new Error("Sem conexão com o servidor local. Confira o terminal do VS Code.");
  }
  let data;
  try {
    data = await response.json();
  }
  catch {
    throw new Error("Resposta inválida do servidor.");
  }
  if (!response.ok)
    throw new Error(data.erro || "Não foi possível concluir a operação.");
  return data;
}
function count(p) {
  return state.campos.reduce((acc, item) => acc + (p.campos && p.campos[item[0]] && p.campos[item[0]].valor ? 1 : 0), 0);
}
function pct(p) { return state.campos.length ? Math.round(100 * count(p) / state.campos.length) : 0; }
function camposPendentes(p) { return state.campos.filter(([k]) => !p.campos || !p.campos[k] || !p.campos[k].valor); }
function avisoPendencias(p) {
  const pendentes = camposPendentes(p);
  const legal = p.campos?.base_legal;
  const revisaoLegal = legal?.validacao_juridica !== "validado";
  if (!pendentes.length && !revisaoLegal)
    return el("div", "pending-note ready", "Todos os campos documentados. Mantenha a revisão humana do registro.");
  const box = el("div", "pending-note"), oper = pendentes.filter(([k]) => k !== "base_legal"), jur = pendentes.some(([k]) => k === "base_legal");
  if (oper.length)
    box.append(el("div", "", "Informações pendentes: " + oper.map(([, v]) => v.split(" (")[0]).join(", ") + "."));
  if (jur)
    box.append(el("div", "", "Base legal ainda não informada — requer proposta e análise jurídica."));
  else if (revisaoLegal)
    box.append(el("div", "", "Sugestão de base legal documentada, mas ainda pendente de validação jurídica."));
  return box;
}
function empty(title, subtitle, symbol = "folder") {
  const d = el("div", "empty-state");
  d.append(icon(symbol), el("h3", "", title), el("p", "", subtitle));
  return d;
}
export { $, state, FIELD_GROUPS, NAMES, icon, el, button, toast, api, count, pct, camposPendentes, avisoPendencias, empty };
