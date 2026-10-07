const names = {codex: 'Codex', ollama: 'Ollama (local AI models)', opencode: 'OpenCode', gemini: 'Gemini CLI', git: 'Git'};

async function showTools() {
  const list = document.querySelector('#tools');
  try {
    const tools = await window.__TAURI__.core.invoke('available_tools');
    list.innerHTML = tools.map(tool => `<li class="${tool.installed ? 'yes' : 'no'}"><span class="dot"></span>${names[tool.name] || tool.name}<span class="when">${tool.installed ? 'Ready' : 'Not found'}</span></li>`).join('');
  } catch (_) {
    list.innerHTML = '<li><span class="dot"></span>Tool check is not available in this window.</li>';
  }
}

document.querySelector('#check-again').addEventListener('click', () => window.location.reload());
window.showStartupError = (message) => {
  const notice = document.querySelector('#startup-error');
  notice.textContent = message;
  notice.hidden = false;
  document.querySelector('#starting').hidden = true;
};
showTools();
