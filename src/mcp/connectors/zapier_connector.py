import os
import requests
from typing import Any, Dict, List


class ZapierConnector:
    """Simple wrapper for the Zapier Natural Language Actions (NLA) MCP server.

    Docs: https://nla.zapier.com/api/v1/  (obtain key at https://nla.zapier.com/app/zapier/auth/key)
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("ZAPIER_API_KEY")
        self.base_url = (base_url or os.getenv("ZAPIER_BASE_URL", "https://nla.zapier.com/api/v1/mcp")).rstrip("/")

    # ------------------------------------------------------------------
    def _headers(self):
        if not self.api_key:
            raise RuntimeError("ZAPIER_API_KEY env variable is not set")
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    # ------------------------------------------------------------------
    def call_tool(self, tool_name: str, payload: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/tools/{tool_name}/invoke"
        response = requests.post(url, json={"input": payload}, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return metadata for all available tools in Zapier account."""
        url = f"{self.base_url}/tools"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json() 