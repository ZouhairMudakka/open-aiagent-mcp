# Agentic AI Framework with MCP Support

![Agentic AI Logo](logo.png)

Welcome to **Agentic AI**, an open-source Python framework that makes it easy to build advanced AI agents with first-class **Model Context Protocol (MCP)** integration and a plug-in tool system.  
The project is intentionally lightweight, transparent, and extensible so that researchers, hobbyists, and companies alike can experiment with multi-agent architectures, reasoning strategies, and external toolchains such as **Zapier** or **n8n**.

---

## ✨ Key Features

* **Modular Architecture** – Clean folder layout (see below) inspired by the included project diagram.
* **MCP-Native** – Agents speak MCP out of the box so they can interoperate with any compliant server, including Zapier AI Actions and n8n MCP nodes.
* **Tool Registry** – Register new capabilities (search, calculations, retrieval, etc.) in a single line of code.
* **FastAPI Sandbox** – Spin up a local HTTP API (`uvicorn src.app:app --reload`) and talk to your agent from the browser at `http://localhost:8000`.
* **Config-as-YAML** – Tweak model names, prompts, logging levels, and more without touching the code.
* **Batteries Included** – Sample prompts, simple reasoning engine, and working Zapier/n8n connectors so you can see end-to-end flows immediately.

---

## 🗂️ Project Structure
```
Agentic_AI_Project/
├── config/                # YAML configs for models, logging, prompts, etc.
├── src/                   # All Python source code
│   ├── llm/               # LLM client helpers (OpenAI, Claude, etc.)
│   ├── tools/             # Re-usable tool wrappers (search, calc, retrieval)
│   ├── agents/            # Reasoning, planning, multi-step orchestration
│   │   └── base_agent.py  # Core Agent class (MCP aware)
│   ├── mcp/               # MCP protocol helpers & connectors
│   │   └── connectors/
│   │       ├── zapier_connector.py
│   │       └── n8n_connector.py
│   ├── communication/     # Message bus / agent-to-agent channels
│   ├── utils/             # Logging, rate limiting, caching, etc.
│   └── app.py             # FastAPI entrypoint
├── data/                  # Runtime data & caches (auto-created)
├── examples/              # Notebooks and scripts that showcase usage
├── LICENSE                # CC BY-NC 4.0 license (personal use)
├── requirements.txt       # Python deps
└── run_server.py          # Helper script to launch FastAPI quickly
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

Open your browser at `http://localhost:8000/docs` to explore the interactive Swagger UI.

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
    A["Browser / CLI"] -->|HTTP| B["FastAPI App"]
    B --> C[Coordinator]
    C --> D1["Agent 1"]
    C --> D2["Agent 2+"]
    %% intra-agent comms
    subgraph Message_Bus
        D1 -- "pub/sub" --> D2
    end
    D1 --> E["Tool Registry"]
    D2 --> E
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