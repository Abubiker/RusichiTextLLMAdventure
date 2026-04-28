import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "game.db")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
OPENROUTER_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv("OPENROUTER_FALLBACK_MODELS", "google/gemma-4-31b-it:free,google/gemma-3-27b-it:free").split(",")
    if model.strip()
]

# LLM behavior
CONTEXT_TURNS = int(os.getenv("CONTEXT_TURNS", "12"))
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "60"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "600"))
LLM_MIN_NARRATIVE_CHARS = int(os.getenv("LLM_MIN_NARRATIVE_CHARS", "160"))

# Gameplay
MAX_OPTIONS = 4
