import requests
from typing import Any, Dict


class ZapierConnector:
    """Simple wrapper that sends tool calls to a Zapier MCP server."""

    def __init__(self, api_key: str | None, base_url: str = "https://nla.zapier.com/api/v1/mcp"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self):
        if not self.api_key:
            raise RuntimeError("ZAPIER_API_KEY env variable is not set")
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def call_tool(self, tool_name: str, payload: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/tools/{tool_name}/invoke"
        response = requests.post(url, json={"input": payload}, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json() 