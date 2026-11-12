/** Liga botões e formulários aos serviços. Único ponto de inicialização da interface. */
import { $, state, toast, api } from "./core.js";
import { definirRenderizadores, navigate, criar, abrir, enviar, renomearEntrevista, reconstruir, recuperarBases, adicionarProcesso, baixarMd, microfone, refreshItems, alternarEncerramento } from "./actions.js";
import { render, renderList, renderChat } from "./views/index.js";
definirRenderizadores({ render, renderChat });
async function init() {
  document.querySelectorAll(".nav-item[data-view]").forEach(b => b.addEventListener("click", () => navigate(b.dataset.view)));
  $("abrirMenu").onclick = () => $("appShell").classList.add("menu-open");
  $("fecharMenu").onclick = () => $("appShell").classList.remove("menu-open");
  $("novoTopo").onclick = criar;
  $("heroIniciar").onclick = () => navigate("entrevistas");
  $("encerrarEntrevista").onclick = alternarEncerramento;
  $("verTodas").onclick = () => navigate("entrevistas");
  $("renomearBtn").onclick = () => state.ent && renomearEntrevista(state.ent);
  $("irMapeamento").onclick = () => navigate("processos");
  $("escolherEntrevista").onclick = () => navigate("entrevistas");
  $("atualizarMapa").onclick = $("atualizarMapaCompleto").onclick = reconstruir;
  $("recuperarBases").onclick = recuperarBases;
  $("addProcesso").onclick = adicionarProcesso;
  $("baixarMd").onclick = baixarMd;
  $("mic").onclick = microfone;
  $("form").addEventListener("submit", enviar);
  $("entrada").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      $("form").requestSubmit();
    }
  });
  $("searchInterviews").addEventListener("input", e => { state.query = e.target.value; renderList(); });
  $("reportInterview").addEventListener("change", e => { state.selectedReport = e.target.value; $("baixarMd").disabled = !e.target.value; });
  try {
    const config = await api("GET", "/api/config");
    state.campos = config.campos;
    await refreshItems();
    navigate("dashboard");
  }
  catch (err) {
    toast(err.message, true);
  }
}
init();
