from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .agents.base_agent import Agent

app = FastAPI(title="Agentic AI MCP Sandbox", version="0.1.0")
agent = Agent()


class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    response: str


@app.post("/chat", response_model=PromptResponse)
async def chat(req: PromptRequest):
    try:
        result = agent.chat(req.prompt)
        return PromptResponse(response=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Agentic AI MCP Sandbox is running. Use POST /chat."} 