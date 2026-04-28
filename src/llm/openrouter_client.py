import json
import re
from typing import Any, Dict, List, Optional

import requests

from ..config import (
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SEC,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    *,
    response_format: Optional[str] = "json",
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://rusichi-game.bot",
        "X-Title": "Rusichi Text Adventure",
    }
    payload: Dict[str, Any] = {
        "model": model or OPENROUTER_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
    }

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=LLM_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return {"message": {"content": content}}


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    snippet = text[start : end + 1].strip()
    for attempt in range(3):
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            if attempt == 0:
                snippet = re.sub(r",\s*([}\]])", r"\1", snippet)
                continue
            if attempt == 1:
                snippet = snippet.replace("«", '"').replace("»", '"')
                continue
            return None
