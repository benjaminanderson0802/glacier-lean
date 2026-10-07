const names = {codex: 'Codex', ollama: 'Ollama', opencode: 'OpenCode', gemini: 'Gemini', git: 'Git'};

async function showTools() {
  const list = document.querySelector('#tools');
  try {
    const tools = await window.__TAURI__.core.invoke('available_tools');
    list.innerHTML = tools.map(tool => `<li class="${tool.installed ? 'yes' : 'no'}">${names[tool.name] || tool.name}: ${tool.installed ? 'Ready' : 'Not found'}</li>`).join('');
  } catch (_) {
    list.innerHTML = '<li>Tool check is not available in this window.</li>';
  }
}

document.querySelector('#check-again').addEventListener('click', () => window.location.reload());
window.showStartupError = (message) => {
  const notice = document.querySelector('#startup-error');
  notice.textContent = message.includes('Python 3.12')
    ? "Python 3.12 is required to run Glacier's local engine. Install Python 3.12 and restart Glacier. The backend source is included with the app; Python itself is not."
    : message;
  notice.hidden = false;
};
showTools();
