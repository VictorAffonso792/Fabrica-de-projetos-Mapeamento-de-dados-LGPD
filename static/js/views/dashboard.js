/** Indicadores e lista de entrevistas recentes no painel inicial. */
import { $, state, el, button, icon, empty } from "../core.js";
import { abrir, navigate } from "../actions.js";
function renderDashboard() {
  const n = state.items.reduce((s, e) => s + (e.processos || 0), 0);
  const filled = state.items.reduce((s, e) => s + (e.preenchidos || 0), 0);
  const pending = state.items.reduce((s, e) => s + (e.pendentes || 0), 0);
  const legalReview = state.items.reduce((s, e) => s + (e.revisoes_juridicas || 0), 0);
  const percentage = filled + pending ? Math.round(100 * filled / (filled + pending)) : 0;
  const data = [
    ["Entrevistas", state.items.length, "Registros iniciados", "chat"],
    ["Processos mapeados", n, "Atividades identificadas", "list"],
    ["Campos preenchidos", filled, "Informações documentadas", "check"],
    ["Campos pendentes", pending, "Informações ainda não documentadas", "clock"],
    ["Revisões jurídicas", legalReview, "Bases legais aguardando validação", "shield"]
  ];
  const grid = $("statsGrid");
  grid.replaceChildren();
  for (const [label, value, caption, ico] of data) {
    const card = el("div", "stat-card"), top = el("div", "stat-top"), left = el("span", "", label), badge = el("span", "stat-icon");
    badge.append(icon(ico));
    top.append(left, badge);
    card.append(top, el("div", "stat-value", String(value)), el("div", "stat-foot", caption));
    grid.append(card);
  }
  $("sideTotal").textContent = state.items.length;
  const recent = $("recentes");
  recent.replaceChildren();
  if (!state.items.length)
    recent.append(empty("Nenhuma entrevista ainda", "Inicie sua primeira entrevista para acompanhar os indicadores.", "chat"));
  state.items.slice(0, 5).forEach(item => {
    const btn = button("", "recent-item", async () => { await abrir(item.id); navigate("entrevistas"); });
    const logo = el("span", "recent-icon");
    logo.append(icon("folder"));
    const label = el("span");
    label.style.minWidth = "0";
    label.style.flex = "1";
    label.append(el("span", "recent-name", item.titulo), el("span", "recent-sub", (item.departamento || "Departamento não informado") + " · " + item.processos + " processo(s) · " + item.atualizado));
    btn.append(logo, label, icon("arrow"));
    recent.append(btn);
  });
  const parent = $("progressoGeral");
  parent.replaceChildren();
  const box = el("div", "progress-box"), donut = el("div", "donut"), interior = el("div", "donut-inner");
  donut.style.setProperty("--percent", percentage + "%");
  interior.append(el("strong", "", percentage + "%"), el("span", "", "de preenchimento"));
  donut.append(interior);
  const meta = el("div", "progress-meta");
  const a = el("span"), b = el("span");
  a.append(el("span", "legend-dot"), document.createTextNode("Preenchidos: "), el("b", "", String(filled)));
  b.append(el("span", "legend-dot gray"), document.createTextNode("Pendentes: "), el("b", "", String(pending)));
  meta.append(a, b);
  box.append(donut, meta);
  parent.append(box);
}
export { renderDashboard };
