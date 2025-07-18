const chatLog = document.getElementById("chat-log");
const form = document.getElementById("chat-form");
const input = document.getElementById("prompt-input");

// Auto-resize textarea
if (input && input.tagName === 'TEXTAREA') {
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = input.scrollHeight + 'px';
  });

  // Enter / Shift+Enter handling
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit'));
    }
  });
}

// Settings elements
const providerSel = document.getElementById("provider-sel");
const modelSel = document.getElementById("model-sel");
const tempRange = document.getElementById("temp-range");
const tempVal = document.getElementById("temp-val");

const PROVIDERS = ["openai", "anthropic", "gemini", "deepseek"];

// Populate provider dropdown
providerSel.innerHTML = PROVIDERS.map((p) => `<option value="${p}">${p}</option>`).join("");

function loadSettings() {
  fetch("/settings")
    .then((r) => r.json())
    .then((s) => {
      providerSel.value = s.provider;
      tempRange.value = s.temperature ?? 0.7;
      tempVal.textContent = tempRange.value;
      return fetch(`/models?provider=${s.provider}`);
    })
    .then((r) => r.json())
    .then((models) => {
      populateModels(models);
    });
}

function populateModels(models) {
  modelSel.innerHTML = models.map((m) => `<option value="${m}">${m}</option>`).join("");
  if (models.length) {
    modelSel.value = models[0];
    // Auto-sync with backend so first message works without extra click
    pushSettings();
  }
}

function pushSettings() {
  const body = {
    provider: providerSel.value,
    model: modelSel.value,
    temperature: parseFloat(tempRange.value),
  };
  fetch("/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

providerSel.addEventListener("change", () => {
  fetch(`/models?provider=${providerSel.value}`)
    .then((r) => r.json())
    .then((models) => {
      populateModels(models);
      pushSettings();
    });
});

modelSel.addEventListener("change", pushSettings);

tempRange.addEventListener("input", () => {
  tempVal.textContent = tempRange.value;
});

tempRange.addEventListener("change", pushSettings);

loadSettings();

let ws;

function renderMarkdown(md) {
  if (window.marked) {
    marked.setOptions({ breaks: true, gfm: true });
    let pre = md;
    // Ensure newline before headings when glued to previous sentence
    pre = pre.replace(/\s+(#{1,6}\s)/g, '\n\n$1');
    // Ensure newline before numbered list items
    pre = pre.replace(/\s+(\d+\.\s)/g, '\n$1');
    // Ensure newline *after* headings before first list item
    pre = pre.replace(/(#{1,6}[^\n]+)\s*(\d+\.\s)/g, '$1\n\n$2');
    // Collapse triple hashes without newline afterwards into heading
    return marked.parse(pre);
  }
  // Fallback – escape HTML
  return md.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
}

function appendMessage(text, cls = "assistant") {
  // Row wrapper
  const row = document.createElement("div");
  row.className = `msg-row ${cls}`;
  row.style.display = "flex";
  row.style.gap = "0.5rem";
  row.style.alignItems = "flex-end";
  row.style.marginBottom = "0.5rem";
  if (cls === "user") {
    row.style.justifyContent = "flex-end";
  }

  // Avatar symbol
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = cls === "user" ? "🧑" : "🤖";
  if (cls !== "user") {
    row.appendChild(avatar);
  }

  // Bubble
  const bubble = document.createElement("div");
  bubble.className = `message ${cls}`;

  const html = renderMarkdown(text);
  bubble.innerHTML = html;

  // Timestamp
  const ts = document.createElement('span');
  ts.className = 'timestamp';
  ts.textContent = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  ts.style.fontSize = '0.75rem';
  ts.style.color = '#9ca3af';

  row.appendChild(bubble);
  if (cls === "user") {
    row.appendChild(ts);
    row.appendChild(avatar);
  }
  if (cls !== "user") {
    row.appendChild(ts);
  }

  chatLog.appendChild(row);
  chatLog.scrollTop = chatLog.scrollHeight;
  return bubble;
}

function appendToolEvent(evt) {
  const el = document.createElement("div");
  el.className = "tool-event";
  el.textContent = `🔧 ${evt.tool} → ${JSON.stringify(evt.payload)} → ${JSON.stringify(
    evt.result
  )}`;
  chatLog.appendChild(el);
  chatLog.scrollTop = chatLog.scrollHeight;

  // Also write a structured entry to the Agent Workspace panel
  logWorkspace(`Tool: ${evt.tool}`, evt);
}

function connectWS() {
  ws = new WebSocket(`${location.origin.replace("http", "ws")}/ws`);
  ws.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (data.type === "token") {
      // On first token, remove typing indicator and ensure a span for text
      if (typingEl) removeTypingIndicator();
      assistantSpan.textContent += data.token;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else if (data.type === "tool") {
      appendToolEvent(data);
    } else if (data.type === "done") {
      assistantSpan = null;
    }
  };
  ws.onclose = () => {
    setTimeout(connectWS, 1000);
  };
  ws.onerror = (e) => console.error("WebSocket error", e);
}

connectWS();

let assistantSpan = null;
let typingEl = null;
let assistantBuffer = "";

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const prompt = input.value.trim();
  if (!prompt) return;

  clearSuggestions();

  appendMessage(prompt, "user");
  // Create assistant message container with typing indicator placeholder
  assistantSpan = appendMessage("", "assistant");
  const formattedDiv = document.createElement("div");
  const pendingSpan = document.createElement("span");
  assistantSpan.appendChild(formattedDiv);
  assistantSpan.appendChild(pendingSpan);

  typingEl = document.createElement("div");
  typingEl.className = "typing-indicator";
  typingEl.innerHTML = '<span></span><span></span><span></span>';
  assistantSpan.appendChild(typingEl);
  assistantBuffer = "";

  ws.send(JSON.stringify({ prompt }));
  input.value = "";
});

function removeTypingIndicator() {
  if (typingEl && typingEl.parentElement) {
    typingEl.parentElement.removeChild(typingEl);
  }
  typingEl = null;
}

ws.onmessage = (ev) => {
  const data = JSON.parse(ev.data);
  if (data.type === "token") {
    // On first token, remove typing indicator and ensure a span for text
    if (typingEl) removeTypingIndicator();
    assistantBuffer += data.token;
    // find last completed paragraph (double newline)
    const splitIdx = assistantBuffer.lastIndexOf("\n\n");
    const formattedDiv = assistantSpan.children[0];
    const pendingSpan = assistantSpan.children[1];
    if (splitIdx !== -1) {
      const completed = assistantBuffer.slice(0, splitIdx + 2);
      const pending = assistantBuffer.slice(splitIdx + 2);
      formattedDiv.innerHTML = renderMarkdown(completed);
      pendingSpan.textContent = pending;
    } else {
      pendingSpan.textContent = assistantBuffer;
    }
    chatLog.scrollTop = chatLog.scrollHeight;
  } else if (data.type === "tool") {
    appendToolEvent(data);
  } else if (data.type === "done") {
    if (assistantSpan) {
      const formattedDiv = assistantSpan.children[0];
      const pendingSpan = assistantSpan.children[1];
      formattedDiv.innerHTML = renderMarkdown(assistantBuffer.trim());
      pendingSpan.textContent = "";
    }
    assistantSpan = null;
  }
};

const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebar = document.getElementById("sidebar");
const container = document.getElementById("container");
sidebarToggle.addEventListener("click", () => {
  sidebar.classList.toggle("open");
  sidebar.classList.toggle("closed");
  container.classList.toggle("shifted");
});

const agentsLink = document.getElementById("agents-link");
const agentsPanel = document.getElementById("agents-panel");
const agentsClose = document.getElementById("agents-close");

const workspaceLink = document.getElementById("workspace-link");
const workspacePanel = document.getElementById("workspace-panel");
const workspaceClose = document.getElementById("workspace-close");
const workspaceLog = document.getElementById("workspace-log");

// New helper: log details to the Agent Workspace panel
function logWorkspace(title, content) {
  if (!workspaceLog) return;
  const wrapper = document.createElement("div");
  wrapper.style.marginBottom = "0.75rem";

  const heading = document.createElement("strong");
  heading.textContent = title;
  wrapper.appendChild(heading);

  const pre = document.createElement("pre");
  pre.style.whiteSpace = "pre-wrap";
  pre.style.fontSize = "0.75rem";
  pre.textContent = typeof content === "string" ? content : JSON.stringify(content, null, 2);
  wrapper.appendChild(pre);

  workspaceLog.appendChild(wrapper);
  workspaceLog.scrollTop = workspaceLog.scrollHeight;
}

// mic button placeholder alerts
document.getElementById("mic-btn").addEventListener("click", () => {
  alert("Voice input feature is not yet implemented.");
});

const SUGGESTED_PROMPTS = [
  "List all items from the database.",
  "Process new WhatsApp leads.",
  "Summarize unread Outlook emails.",
  "Monitor #leads Slack channel."
];

function renderSuggestions() {
  if (document.getElementById("suggestions")) return; // already rendered
  const wrap = document.createElement("div");
  wrap.id = "suggestions";
  wrap.className = "suggestions-grid";
  SUGGESTED_PROMPTS.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "suggest-btn";
    btn.textContent = p;
    btn.addEventListener("click", () => {
      input.value = p;
      form.dispatchEvent(new Event("submit"));
    });
    wrap.appendChild(btn);
  });
  chatLog.appendChild(wrap);
}

function clearSuggestions() {
  const el = document.getElementById("suggestions");
  if (el) el.remove();
}

// initial suggestions
renderSuggestions();

// Theme toggle
const themeToggle = document.getElementById("theme-toggle");
themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("dark");
  themeToggle.textContent = document.body.classList.contains("dark") ? "☀️" : "🌙";
});

// Settings modal placeholder
const settingsBtn = document.getElementById("settings-btn");
const settingsModal = document.getElementById("settings-modal");
const settingsClose = document.getElementById("settings-close");
settingsBtn.addEventListener("click", () => { settingsModal.classList.remove("hidden"); });
settingsClose.addEventListener("click", () => { settingsModal.classList.add("hidden"); });

// New chat button (close current conversation)
const newChatBtn = document.getElementById("new-chat-btn");
if (newChatBtn) {
  newChatBtn.addEventListener("click", () => {
    handleNewChat();
  });
}

// Update listening class for red background buttons
function updateMicVisual() {
  if (!recognitionRef.current) return;
  if (isListening) {
    micBtn.classList.add('listening');
  } else {
    micBtn.classList.remove('listening');
  }
}

const micBtn = document.getElementById('mic-btn');

if (micBtn) {
  micBtn.addEventListener('click', () => {
    // toggleListening already called elsewhere, but ensure style sync after small delay
    setTimeout(updateMicVisual, 50);
  });
}

// ===== Sidebar Navigation Logic =====
function setActivePanel(panelName) {
  // panelName can be 'agents', 'workspace', or null
  if (panelName === 'agents') {
    // open Agents, close Workspace
    agentsPanel.classList.remove('hidden');
    agentsPanel.classList.add('open');

    workspacePanel.classList.remove('open');
    workspacePanel.classList.add('hidden');

    container.classList.add('agent-shift');
    setActiveSidebarItem(agentsLink);
  } else if (panelName === 'workspace') {
    workspacePanel.classList.remove('hidden');
    workspacePanel.classList.add('open');

    agentsPanel.classList.remove('open');
    agentsPanel.classList.add('hidden');

    container.classList.add('agent-shift');
    setActiveSidebarItem(workspaceLink);
  } else {
    // close all
    agentsPanel.classList.remove('open');
    agentsPanel.classList.add('hidden');

    workspacePanel.classList.remove('open');
    workspacePanel.classList.add('hidden');

    container.classList.remove('agent-shift');
    setActiveSidebarItem(null);
  }
}

function setActiveSidebarItem(el) {
  document.querySelectorAll('.sidebar-list li').forEach(li => li.classList.remove('active'));
  if (el) el.classList.add('active');
}

// Attach click handlers (replace old ones)
if (agentsLink) {
  agentsLink.addEventListener('click', () => setActivePanel('agents'));
}
if (workspaceLink) {
  workspaceLink.addEventListener('click', () => setActivePanel('workspace'));
}
if (agentsClose) {
  agentsClose.addEventListener('click', () => setActivePanel(null));
}
if (workspaceClose) {
  workspaceClose.addEventListener('click', () => setActivePanel(null));
}
// ===== End Sidebar Navigation ===== 