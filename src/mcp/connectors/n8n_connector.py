import requests
from typing import Any, Dict


class N8NConnector:
    """Minimal client for n8n MCP server."""

    def __init__(self, api_key: str | None, base_url: str = "https://api.n8n.cloud/mcp"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self):
        if not self.api_key:
            raise RuntimeError("N8N_API_KEY env variable is not set")
        return {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

    def call_tool(self, workflow_name: str, payload: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/workflows/{workflow_name}/invoke"
        response = requests.post(url, json={"input": payload}, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json() 