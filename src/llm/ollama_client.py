import json
import re
from typing import Any, Dict, List, Optional

import requests

from ..config import (
    LLM_TIMEOUT_SEC,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TEMPERATURE,
    OLLAMA_TOP_K,
    OLLAMA_TOP_P,
)


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    *,
    response_format: Optional[str] = "json",
) -> Dict[str, Any]:
    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    options = {
        "num_ctx": OLLAMA_NUM_CTX,
        "num_predict": OLLAMA_NUM_PREDICT,
        "temperature": OLLAMA_TEMPERATURE,
        "top_p": OLLAMA_TOP_P,
        "top_k": OLLAMA_TOP_K,
    }
    payload["options"] = options
    if response_format:
        payload["format"] = response_format
    resp = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=LLM_TIMEOUT_SEC)
    resp.raise_for_status()
    return resp.json()


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
                # Remove trailing commas before } or ]
                snippet = re.sub(r",\s*([}\]])", r"\1", snippet)
                continue
            if attempt == 1:
                # Replace fancy quotes with normal quotes
                snippet = snippet.replace("«", "\"").replace("»", "\"")
                continue
            return None
