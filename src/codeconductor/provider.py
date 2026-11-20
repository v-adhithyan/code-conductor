"""OpenAI-compatible ChatGPT API adapter."""

import json
import os
from typing import Any

import httpx


class ProviderError(RuntimeError):
    pass


class OpenAIProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("CODECONDUCTOR_MODEL", "gpt-4o-mini")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set. Add it to your environment or .env file.")

    def complete_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                },
                timeout=90,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object")
            return result
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            detail = ""
            if isinstance(exc, httpx.HTTPStatusError):
                detail = f" API response: {exc.response.text[:1000]}"
            raise ProviderError(f"ChatGPT request failed: {exc}.{detail}") from exc
