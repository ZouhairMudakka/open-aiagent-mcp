from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv

# Load env first so downstream imports see API keys
load_dotenv(".env", override=False)

# Switched to LangGraph-based agent
from .agents.langgraph_agent import LangGraphAgent
from .settings import RuntimeSettings
from .llm import get_llm_client, OpenAIClient, AnthropicClient, GeminiClient, DeepSeekClient
from src.utils.logger import setup_logger
from src.tools.db_tool import db_tool
import langchain

langchain.debug = True

logger = setup_logger(level="DEBUG")

# Configure root logger so DEBUG messages propagate to console (override any prior config)
logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s", force=True)


app = FastAPI(title="Agentic AI MCP Sandbox", version="0.2.0")

# Ensure root logger stays at DEBUG even after Uvicorn config
@app.on_event("startup")
async def _configure_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if not root_logger.handlers:
        import sys
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        sh.setLevel(logging.DEBUG)
        root_logger.addHandler(sh)
    else:
        for h in root_logger.handlers:
            h.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    for h in logger.handlers:
        h.setLevel(logging.DEBUG)
    logger.debug("[startup] Root logger and handlers forced to DEBUG")

# global runtime settings (will be updated by /settings)
runtime_settings = RuntimeSettings()

# Single shared agent instance
agent = LangGraphAgent()

# Serve static web UI (index.html, chat.js, etc.)
app.mount("/ui", StaticFiles(directory="src/webui", html=True), name="webui")


# ---------------------------------------------------------------------------
# WebSocket endpoint for live token & event streaming
# ---------------------------------------------------------------------------


def _chunk_tokens(text: str) -> List[str]:
    """Very naive tokenizer that splits on whitespace but keeps spacing."""
    tokens: List[str] = []
    current = ""
    for char in text:
        current += char
        if char.isspace():
            tokens.append(current)
            current = ""
    if current:
        tokens.append(current)
    return tokens


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            prompt = data.get("prompt", "")
            if not prompt:
                await ws.send_json({"type": "error", "message": "Prompt missing"})
                continue

            logger.debug("[ws] prompt=%s", prompt)

            # Call agent asynchronously
            response_text = await agent.chat(prompt)

            logger.debug("[ws] response=%s", response_text)

            # Stream tokens
            for tok in _chunk_tokens(response_text):
                await ws.send_json({"type": "token", "token": tok})
                await asyncio.sleep(0.02)  # small delay for typing effect

            logger.debug("[ws] sent %d tokens", len(_chunk_tokens(response_text)))

            # Send tool events
            for evt in agent.events:
                await ws.send_json({"type": "tool", **evt})
                logger.debug("[ws] sent tool event=%s", evt)

            await ws.send_json({"type": "done"})
            logger.debug("[ws] done sent")
    except WebSocketDisconnect:
        return
    except Exception as exc:
        import traceback, logging
        logging.error("WS handler crashed:\n%s", traceback.format_exc())
        await ws.close()


class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    response: str


@app.post("/chat", response_model=PromptResponse)
async def chat(req: PromptRequest):
    try:
        logging.debug("[chat endpoint] Received prompt: %s", req.prompt)
        print("CHAT ENDPOINT RECEIVED", req.prompt)
        result = await agent.chat(req.prompt)
        logging.debug("[chat endpoint] Response: %s", result)
        print("CHAT ENDPOINT RESPONSE", result)
        return PromptResponse(response=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Agentic AI MCP Sandbox is running. Use POST /chat."}


# expose models route


@app.get("/models")
async def list_models(provider: str):
    # When listing models we don't yet know the user's choice, so we bypass
    # strict model validation with a harmless placeholder.
    try:
        placeholder = "placeholder-model"
        if provider == "openai":
            client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"), model=placeholder)
        elif provider in {"anthropic", "claude"}:
            client = AnthropicClient(api_key=os.getenv("ANTHROPIC_API_KEY"), model=placeholder)
        elif provider in {"gemini", "google"}:
            client = GeminiClient(api_key=os.getenv("GOOGLE_API_KEY"), model=placeholder)
        elif provider == "deepseek":
            client = DeepSeekClient(api_key=os.getenv("DEEPSEEK_API_KEY"), model=placeholder)
        else:
            raise HTTPException(status_code=400, detail="Unknown provider")
        models = client.list_models()
        logging.info("[models] provider=%s models_found=%d", provider, len(models))
        return models
    except Exception:
        # Likely missing API key or network issue; return empty list so UI can warn user
        return []


@app.get("/settings")
async def get_settings():
    return runtime_settings.to_dict()


class SettingsPatch(BaseModel):
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None


@app.patch("/settings")
async def patch_settings(s: SettingsPatch):
    if s.provider:
        runtime_settings.provider = s.provider
    if s.model:
        runtime_settings.model = s.model
    if s.temperature is not None:
        runtime_settings.temperature = s.temperature
    agent.settings_ref = runtime_settings
    logging.info("[settings] provider=%s model=%s temperature=%s", runtime_settings.provider, runtime_settings.model, runtime_settings.temperature)
    return runtime_settings.to_dict() 