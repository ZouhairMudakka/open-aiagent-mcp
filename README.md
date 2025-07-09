# Agentic AI Framework with MCP Support

![Agentic AI Logo](logo.png)

Welcome to **Agentic AI**, an open-source Python framework that makes it easy to build advanced AI agents with first-class **Model Context Protocol (MCP)** integration and a plug-in tool system.  
The project is intentionally lightweight, transparent, and extensible so that researchers, hobbyists, and companies alike can experiment with multi-agent architectures, reasoning strategies, and external toolchains such as **Zapier** or **n8n**.

---

## ✨ Key Features

* **Modular Architecture** – Clean folder layout (see below) inspired by the included project diagram.
* **MCP-Native** – Agents speak MCP out of the box so they can interoperate with any compliant server, including Zapier AI Actions and n8n MCP nodes.
* **Tool Registry** – Register new capabilities (search, calculations, retrieval, etc.) in a single line of code.
* **FastAPI Sandbox** – Spin up a local HTTP API (`python run_server.py` or `uvicorn src.app:app --reload`) with interactive docs at `http://localhost:8000/docs`.
* **Live Web UI** – Built-in chat front-end at `http://localhost:8000/ui` that streams tokens in real time via WebSockets.
* **Hot-Reload Settings** – Tweak provider/model/temperature at runtime via the `/settings` REST endpoint (no restart required).
* **Config-as-YAML** – Tweak model names, prompts, logging levels, and more without touching the code.
* **Batteries Included** – Sample prompts, simple reasoning engine, and working Zapier/n8n connectors so you can see end-to-end flows immediately.
* **Multi-Provider LLM Support** – Swap between OpenAI, Anthropic (Claude), Google Gemini, or DeepSeek just by changing an env var or YAML config—no code edits required.

---

## 🗂️ Project Structure
```
Open-AIAgent-MCP/
├── config/                # YAML configs for models, logging, prompts, etc.
├── src/                   # All Python source code
│   ├── app.py             # FastAPI entrypoint (mounts /ws & /ui)
│   ├── settings.py        # RuntimeSettings dataclass + REST helpers
│   ├── agents/            # Reasoning, planning, multi-step orchestration
│   │   ├── coordinator.py
│   │   ├── planner.py
│   │   ├── reasoning_engine.py
│   │   └── base_agent.py
│   ├── llm/               # Provider adapters (OpenAI, Anthropic, Gemini, DeepSeek)
│   ├── tools/             # Re-usable tool wrappers (DB, Search, etc.)
│   ├── db/                # SQLAlchemy models + session helpers
│   ├── communication/     # Message bus / agent-to-agent channels
│   ├── mcp/               # MCP protocol helpers & connectors
│   │   └── connectors/
│   │       ├── zapier_connector.py
│   │       └── n8n_connector.py
│   ├── utils/             # Logging, rate limiting, token counting, etc.
│   └── webui/             # Static chat UI (HTML/JS/CSS served at /ui)
├── scripts/               # Windows helper scripts (restart-server.ps1, etc.)
├── examples/              # Notebooks and CLI chatbot demo
├── env.example            # Sample .env with documented keys
├── requirements.txt       # Python dependencies
├── run_server.py          # Helper to launch FastAPI quickly
├── setup.py               # Editable install support
└── LICENSE
```

The tree above mirrors the structure shown in the reference image.

---

## 🚀 Quick Start

```bash
# 1. Clone repository
$ git clone https://github.com/ZouhairMudakka/open-aiagent-mcp.git
$ cd open-aiagent-mcp

# 2. Create virtualenv (optional but recommended)
$ python -m venv .venv && source .venv/bin/activate  # PowerShell: .venv\Scripts\Activate.ps1

# 3. Install dependencies
$ pip install -r requirements.txt

# 3b. (Optional) Postgres
$ docker run --name agentic-postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:16
$ echo "DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/postgres" > .env

# 4. Launch local API (runs on http://localhost:8000)
$ python run_server.py
```

Open your browser at `http://localhost:8000/docs` to explore the interactive Swagger UI, or go straight to `http://localhost:8000/ui` for the live chat interface.

---

## 🌐 Deployment Options

You’re not limited to `localhost`—the framework is cloud-ready out of the box. Pick a path that fits your scale and comfort level:

### 1. One-Click PaaS (Render, Railway, Fly.io)
1. **Create** a new web service and point it at your GitHub fork.
2. **Build command:** `pip install -r requirements.txt`
3. **Start command:** `uvicorn src.app:app --host 0.0.0.0 --port $PORT`
4. **Add environment variables** (e.g., `OPENAI_API_KEY`, `DATABASE_URL`) in the platform dashboard.

### 2. Docker & Docker Compose (works anywhere)
Create a `Dockerfile` in the project root:

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Optional `docker-compose.yml` for Postgres:

```yaml
version: "3.9"
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db]
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
volumes:
  postgres_data:
```

### 3. VM / Bare-Metal (NGINX + Gunicorn)
1. SSH into your server; install Python 3.11, Postgres, and NGINX.
2. Clone the repo and start Gunicorn for production robustness:

```bash
pip install gunicorn uvicorn
gunicorn -k uvicorn.workers.UvicornWorker -c gunicorn_conf.py src.app:app
```

Example `gunicorn_conf.py`:

```python
bind = "0.0.0.0:8000"
workers = 4
timeout = 120
```

Configure NGINX as a reverse proxy with SSL (Let’s Encrypt) and set up a **Supervisor** or `systemd` unit to keep the service running.

### 4. Kubernetes (for teams & scale)
Build the Docker image → push to a registry → apply a Deployment + Service (or Helm chart). Pair with managed Postgres (e.g., Amazon RDS) and add an HPA if you expect traffic spikes.

**Key environment variables:**

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
LLM_PROVIDER=openai   # or anthropic | gemini | deepseek
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
ZAPIER_API_KEY=...
N8N_API_KEY=...
N8N_BASE_URL=https://your-n8n-domain/mcp  # if using n8n
```

---

## 🧠 Switching LLM Providers

The framework loads its model info from `config/agent_config.yaml` **or** falls back to environment variables. Two ways to change provider:

1. **.env / shell vars (quick test)**
   ```bash
   # Anthropic Claude Sonnet
   export LLM_PROVIDER=anthropic
   export ANTHROPIC_API_KEY=sk-ant-...
   python run_server.py
   ```

2. **YAML config (committed to repo)**
   ```yaml
   # config/agent_config.yaml
   model:
     provider: gemini   # openai | anthropic | gemini | deepseek
     name: gemini-pro
     temperature: 0.5
   ```

No other change is required—the unified `get_llm_client()` factory selects the correct adapter under `src/llm/` at runtime.

---

### CLI Chatbot Test

```bash
python examples/chatbot_cli.py
#    you> /echo hello
#    bot> hello

# Database tool examples
you> /db {"action": "add", "data": "hello"}
you> /db {"action": "list"}
```

Behind the scenes the `/db` tool operates on a local SQLite file located at `data/sample.db`. Actions supported: `add`, `delete`, `update`, `list`.

---

## 🛠️ Using the Agent

```python
from src.agents.base_agent import Agent

agent = Agent()
response = agent.chat("Translate 'hello world' into Arabic and schedule via Zapier")
print(response)
```

### Zapier & n8n Connectors

The connectors live in `src/mcp/connectors`.  
Both classes expose a `call_tool()` method that converts agent requests into
HTTP calls against the respective MCP server endpoints. Configure your API keys
in the `.env` file or environment variables:

```
ZAPIER_API_KEY=your_key_here
N8N_API_KEY=your_key_here
```

---

## 🤝 Contributing

Contributions of all kinds are warmly welcomed!  
Please open an issue or submit a pull request—small or large. We follow the
standard [Contributor Covenant](https://www.contributor-covenant.org/) code of
conduct.

1. Fork the repo & create your branch (`git checkout -b feature/amazing`)
2. Commit your changes (`git commit -m 'Add amazing feature'`)
3. Push to the branch (`git push origin feature/amazing`)
4. Open a pull request and describe your change

---

## 📝 License

This project is licensed under the **Creative Commons
Attribution-NonCommercial 4.0 International** license.

Personal and academic use is free. **Commercial use requires a separate
license—contact [hello@mudakka.com](mailto:hello@mudakka.com).**

See the full license text in the `LICENSE` file. 

## 🖼️ Architecture Overview

```mermaid
graph TD
    subgraph Client
        A1["Browser UI (\"/ui\")"] -- WebSocket --> A2["/ws"]
        A1 -- REST --> A3["/settings"]
        A4["CLI / scripts"] -- HTTP --> B["FastAPI App"]
    end
    A2 -->|token stream| A1
    B --> C[Coordinator]
    C --> D1["Agent 1"]
    C --> D2["Agent 2+"]
    subgraph Message_Bus
        D1 -- "pub/sub" --> D2
    end
    D1 & D2 --> E["Tool Registry"]
    E --> F["DBTool (SQLAlchemy)"]
    F --> I[("PostgreSQL | SQLite")]
    E --> G["Zapier Connector"]
    G --> J["Zapier MCP Server"]
    E --> H["n8n Connector"]
    H --> K["n8n MCP Server"]
```

The flow:
1. User sends a request to the FastAPI endpoint (`/chat`).
2. FastAPI forwards the prompt to the **Coordinator**, which selects or spins-up an **Agent**.
3. The Agent reasons/plans, then invokes tools via the **Tool Registry**.
4. Tools can hit the local **DBTool** (backed by SQLAlchemy/Postgres) or external MCP servers like Zapier & n8n.
5. Multiple agents exchange messages over an in-memory **Message Bus**.

---

## 🚧 Further Development & Possibilities

1. **Tooling**
   • Wrap more APIs as MCP tools (e-mail, calendars, vector search, etc.).  
   • Publish a public registry so agents discover tools dynamically.

2. **Reasoning & Memory**
   • Plug in advanced planning trees or RAG pipelines.  
   • Add vector-store memory of past conversations.

3. **Scalability**
   • Swap the in-memory message bus for Redis or NATS to span multiple processes.  
   • Containerise with Docker Compose for API + Postgres + worker pool.

4. **Security & Auth**
   • OIDC / API-key auth on FastAPI routes.  
   • Secret management via Vault or AWS SM.

5. **CI/CD & Testing**
   • Add pytest suites for agents, tools, and DB layer.  
   • GitHub Actions workflow with lint, type-check & unit tests.

6. **Frontend**
   • Minimal React/Next.js or Streamlit client that streams agent tokens.

---

## 🎯 Example Use Cases

| Domain            | Scenario                                                                                  |
|-------------------|-------------------------------------------------------------------------------------------|
| Customer Support  | Multi-agent team triages tickets: one agent classifies, another drafts responses, Zapier tools update Zendesk & Slack |
| Data Engineering  | Agents orchestrate ETL: Planner breaks tasks, DBTool writes staging data, n8n workflows trigger downstream jobs |
| Real-estate CRM   | Chatbot logs prospects into Postgres, schedules viewings via Google Calendar (Zapier) & notifies sales via n8n |
| Marketing Ops     | Agent analyzes campaign metrics, then uses Zapier Email & Sheets tools to send weekly KPI digests |
| Dev Productivity  | Agents trigger CI/CD or GitHub issue automations via custom n8n MCP workflows |

Feel free to open issues or PRs with ideas — the roadmap is community-driven! 

> 🔗 Useful resources: [Zapier MCP docs](https://zapier.com/mcp), [Build n8n MCP server template](https://n8n.io/workflows/3770-build-your-own-n8n-workflows-mcp-server/), and [n8n MCP Client Tool node docs](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/).

---

## 🔑 API Keys & External MCP Setup

### Zapier Natural Language Actions (NLA)
1. Log in to Zapier → https://nla.zapier.com/.
2. Click **Generate an API Key** (or reuse an existing one).
3. Copy the key into your `.env` → `ZAPIER_API_KEY=sk_live_...`
4. Make sure each Zap you want to expose is marked **“Use as Action in AI”**; that exposes it as an MCP tool.
5. Optional: set `ZAPIER_BASE_URL` if you’re on a dedicated Zapier domain.

Test:
```python
from src.mcp.connectors.zapier_connector import ZapierConnector
print(ZapierConnector().list_tools())
```

### n8n MCP
1. Deploy n8n ≥ v1.18 with the MCP plugin enabled (or use n8n.cloud where it’s pre-enabled).
2. Create an **API Key** under *Settings → API* and set `N8N_API_KEY` in `.env`.
3. Build workflows with an **MCP Trigger** node so that they appear as tools.
4. If self-hosting, set `N8N_BASE_URL=https://your-n8n-domain/mcp`.

Test:
```python
from src.mcp.connectors.n8n_connector import N8NConnector
print(N8NConnector().list_workflows())
```

--- 

## 🖥 Interactive Web Chat

The repository now ships with a minimal yet powerful static web interface located in `src/webui/`.  
Once the server is running simply open `http://localhost:8000/ui` in your browser and start chatting.

Key aspects:
* **Token Streaming** – The UI receives tokens over a WebSocket (`/ws`) and displays them with a sleek typing effect.
* **Tool Events** – When the agent invokes a tool, the UI shows a highlighted message describing the call and its arguments.
* **Settings Panel** – The client calls the `/settings` endpoints to read & patch runtime options (provider, model, temperature) without restarting the server.

Feel free to replace the HTML/CSS/JS with anything you like—FastAPI just serves the directory. 