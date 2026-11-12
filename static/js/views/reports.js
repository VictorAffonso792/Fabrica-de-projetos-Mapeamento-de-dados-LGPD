/** Seleção da entrevista a exportar como relatório Markdown. */
import { $, state, el } from "../core.js";
function renderReports() {
  const select = $("reportInterview"), value = state.selectedReport || (state.ent && state.ent.id) || "";
  select.replaceChildren();
  const initial = el("option", "", "Selecione uma entrevista");
  initial.value = "";
  select.append(initial);
  state.items.forEach(it => { const opt = el("option", "", it.titulo + " · " + (it.departamento || "Sem departamento")); opt.value = it.id; select.append(opt); });
  select.value = state.items.some(x => x.id === value) ? value : "";
  $("baixarMd").disabled = !select.value;
}
export { renderReports };
