const chatLog = document.getElementById("chat-log");
const form = document.getElementById("chat-form");
const input = document.getElementById("prompt-input");

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

function appendMessage(text, cls = "assistant") {
  const el = document.createElement("div");
  el.className = `message ${cls}`;
  el.textContent = text;
  chatLog.appendChild(el);
  chatLog.scrollTop = chatLog.scrollHeight;
  return el;
}

function appendToolEvent(evt) {
  const el = document.createElement("div");
  el.className = "tool-event";
  el.textContent = `🔧 ${evt.tool} → ${JSON.stringify(evt.payload)} → ${JSON.stringify(
    evt.result
  )}`;
  chatLog.appendChild(el);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function connectWS() {
  ws = new WebSocket(`${location.origin.replace("http", "ws")}/ws`);
  ws.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (data.type === "token") {
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

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const prompt = input.value.trim();
  if (!prompt) return;

  appendMessage(prompt, "user");
  assistantSpan = appendMessage("", "assistant");

  ws.send(JSON.stringify({ prompt }));
  input.value = "";
}); 