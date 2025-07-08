# Agentic AI Framework with MCP Support

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