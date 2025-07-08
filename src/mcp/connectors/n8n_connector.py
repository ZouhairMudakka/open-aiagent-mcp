import os
import requests
from typing import Any, Dict, List


class N8NConnector:
    """Minimal client for n8n MCP server (community edition preview).

    Requires n8n instance configured with the MCP plugin. Docs: https://docs.n8n.io/integrations/mcp
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("N8N_API_KEY")
        self.base_url = (base_url or os.getenv("N8N_BASE_URL", "https://api.n8n.cloud/mcp")).rstrip("/")

    # ------------------------------------------------------------------
    def _headers(self):
        if not self.api_key:
            raise RuntimeError("N8N_API_KEY env variable is not set")
        return {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

    # ------------------------------------------------------------------
    def call_tool(self, workflow_name: str, payload: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/workflows/{workflow_name}/invoke"
        response = requests.post(url, json={"input": payload}, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def list_workflows(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/workflows"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json() 