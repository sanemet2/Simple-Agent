from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class OpenRouterClient:
    api_key: str
    model: str

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost/simple-openrouter-agent",
                "X-Title": "Simple OpenRouter Agent",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc
