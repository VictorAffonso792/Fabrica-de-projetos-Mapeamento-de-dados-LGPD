/** Ponto central que atualiza todas as telas após alterações de dados. */
import { renderDashboard } from "./dashboard.js";
import { renderList, renderChat, renderLive } from "./interviews.js";
import { renderProcesses } from "./mapping.js";
import { renderReports } from "./reports.js";
export { renderList, renderChat };
export function render() {
  renderDashboard();
  renderList();
  renderChat();
  renderLive();
  renderProcesses();
  renderReports();
}
