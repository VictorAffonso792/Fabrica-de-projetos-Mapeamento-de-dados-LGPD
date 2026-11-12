/**
 * Ações do usuário: navegação, CRUD, mensagens, exportação e voz.
 * Os renderizadores são registrados na inicialização, evitando dependências circulares.
 */
import { $, state, NAMES, toast, api } from "./core.js";
let renderUI = () => { };
let renderChatUI = () => { };
export function definirRenderizadores({ render, renderChat }) {
  renderUI = render;
  renderChatUI = renderChat;
}
function navigate(view) {
  if (!NAMES[view])
    return;
  state.view = view;
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === "view-" + view));
  document.querySelectorAll(".nav-item[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  $("breadcrumb").textContent = NAMES[view];
  $("appShell").classList.remove("menu-open");
  window.scrollTo({ top: 0, behavior: "instant" });
  renderUI();
}
async function refreshItems() {
  try {
    state.items = await api("GET", "/api/entrevistas");
    renderUI();
  }
  catch (err) {
    toast(err.message, true);
  }
}
async function criar() {
  if (state.busy)
    return toast("Aguarde o envio atual antes de criar outra entrevista.", true);
  try {
    const result = await api("POST", "/api/entrevistas");
    state.ent = result.entrevista;
    state.selectedReport = state.ent.id;
    await refreshItems();
    navigate("entrevistas");
    toast("Entrevista criada. Você já pode responder à primeira pergunta.");
  }
  catch (err) {
    toast(err.message, true);
  }
}
async function abrir(id) {
  try {
    const result = await api("GET", "/api/entrevistas/" + encodeURIComponent(id));
    state.ent = result.entrevista;
    state.selectedReport = id;
    renderUI();
  }
  catch (err) {
    toast(err.message, true);
  }
}
async function mutate(action, payload) {
  if (!state.ent)
    return toast("Crie ou selecione uma entrevista primeiro.", true), false;
  if (state.busy)
    return toast("A entrevista está processando. Tente após a resposta.", true), false;
  const id = state.ent.id;
  try {
    const result = await api("POST", "/api/entrevistas/" + encodeURIComponent(id) + "/" + action, payload);
    if (state.ent && state.ent.id === id)
      state.ent = result.entrevista;
    await refreshItems();
    renderUI();
    return true;
  }
  catch (err) {
    toast(err.message, true);
    return false;
  }
}
async function enviar(event) {
  event.preventDefault();
  const field = $("entrada"), txt = field.value.trim();
  if (!txt)
    return;
  if (!state.ent)
    return toast("Crie uma nova entrevista primeiro.", true);
  if (state.busy)
    return toast("Aguarde a resposta anterior.", true);
  if (state.ent.controle_entrevista?.encerrada)
    return toast("Entrevista encerrada. Clique em Reabrir para continuar.", true);
  pararMicrofone();  // evita que o ditado contínuo reescreva a caixa com o texto já enviado
  const id = state.ent.id;
  state.busy = true;
  state.loading = true;
  field.value = "";
  state.ent.mensagens.push({ role: "user", texto: txt });
  $("enviar").disabled = true;
  renderChatUI();
  const start = performance.now();
  try {
    const result = await api("POST", "/api/entrevistas/" + encodeURIComponent(id) + "/mensagem", { texto: txt });
    if (state.ent && state.ent.id === id) {
      state.ent = result.entrevista;
      state.selectedReport = id;
    }
    await refreshItems();
    const time = ((performance.now() - start) / 1000).toFixed(1);
    toast("Mapeamento atualizado · " + time + "s");
  }
  catch (err) {
    if (state.ent && state.ent.id === id)
      state.ent.mensagens.pop();
    field.value = txt;
    toast(err.message, true);
  }
  finally {
    state.busy = false;
    state.loading = false;
    $("enviar").disabled = false;
    renderUI();
    field.focus();
  }
}
async function renomearEntrevista(it) {
  if (state.busy)
    return toast("Aguarde o processamento atual.", true);
  const title = prompt("Novo nome da entrevista:", it.titulo);
  if (!title || !title.trim())
    return;
  if (!state.ent || state.ent.id !== it.id)
    await abrir(it.id);
  const ok = await mutate("renomear", { titulo: title.trim() });
  if (ok)
    toast("Entrevista renomeada.");
}
async function excluirEntrevista(it) {
  if (state.busy)
    return toast("Aguarde o processamento atual.", true);
  if (!confirm("Excluir permanentemente '" + it.titulo + "'? Isso remove os arquivos JSON e MD."))
    return;
  try {
    await api("DELETE", "/api/entrevistas/" + encodeURIComponent(it.id));
    if (state.ent && state.ent.id === it.id)
      state.ent = null;
    if (state.selectedReport === it.id)
      state.selectedReport = "";
    await refreshItems();
    toast("Entrevista excluída.");
  }
  catch (err) {
    toast(err.message, true);
  }
}
async function recuperarBases() {
  if (!state.ent) return toast("Selecione uma entrevista.", true);
  const ok = await mutate("recuperar_bases", {});
  if (ok) toast("Sugestões do histórico conferidas. Consulte o mapeamento.");
}
async function reconstruir() {
  if (!state.ent)
    return toast("Selecione uma entrevista.", true);
  if (!confirm("Reconstruir o mapeamento a partir da transcrição? Edições manuais serão preservadas."))
    return;
  const ok = await mutate("mapear", {});
  if (ok)
    toast("Mapeamento reconstruído.");
}
async function adicionarProcesso() {
  if (!state.ent)
    return toast("Selecione uma entrevista.", true);
  const nome = prompt("Nome do processo:");
  if (!nome || !nome.trim())
    return;
  await mutate("processo", { acao: "adicionar", nome: nome.trim() });
}
async function editarProcesso(pi, nome) {
  const novo = prompt("Renomear processo:", nome);
  if (novo && novo.trim())
    await mutate("processo", { acao: "renomear", indice: pi, nome: novo.trim() });
}
async function removerProcesso(pi, nome) {
  if (confirm("Remover o processo '" + nome + "' e seus campos?"))
    await mutate("processo", { acao: "remover", indice: pi });
}
function baixarMd() {
  const id = $("reportInterview").value;
  if (!id)
    return toast("Selecione uma entrevista para exportar.", true);
  window.location.href = "/api/entrevistas/" + encodeURIComponent(id) + "/md";
}
// Reconhecimento de voz nativo (disponibilidade depende do navegador/permissões).
const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null, recording = false;
function pararMicrofone() {
  if (!recognition || !recording)
    return;
  recognition.onresult = null;  // descarta resultados que ainda cheguem depois do envio
  recognition.stop();
}
function microfone() {
  if (!Speech)
    return toast("Ditado por voz está disponível em navegadores Chrome/Edge compatíveis.", true);
  if (recording) {
    recognition.stop();
    return;
  }
  recognition = new Speech();
  recognition.lang = "pt-BR";
  recognition.continuous = true;
  recognition.interimResults = true;
  const start = $("entrada").value ? $("entrada").value + " " : "";
  recognition.onresult = event => {
    let phrase = ""; for (const result of event.results)
      phrase += result[0].transcript; $("entrada").value = start + phrase;
  };
  recognition.onerror = event => toast("Falha no microfone: " + event.error, true);
  recognition.onend = () => { recording = false; $("mic").classList.remove("on"); };
  try {
    recognition.start();
    recording = true;
    $("mic").classList.add("on");
  }
  catch (e) {
    toast(e.message, true);
  }
}
export { navigate, refreshItems, criar, abrir, mutate, enviar, renomearEntrevista, excluirEntrevista, reconstruir, recuperarBases, adicionarProcesso, editarProcesso, removerProcesso, baixarMd, microfone };

/** Encerramento explícito: servidor registra sem solicitar resposta ao Gemini. */
async function alternarEncerramento() {
  if (!state.ent || state.busy) return;
  const fechada = Boolean(state.ent.controle_entrevista?.encerrada);
  if (!fechada && !confirm("Encerrar esta entrevista agora? Pendências e sugestões de base legal permanecerão salvas para revisão.")) return;
  const ok = await mutate(fechada ? "reabrir" : "encerrar", {});
  if (ok) toast(fechada ? "Entrevista reaberta." : "Entrevista encerrada e salva.");
}
export { alternarEncerramento };
