import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "game.db")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b-it-q4_K_M")

# LLM behavior
CONTEXT_TURNS = int(os.getenv("CONTEXT_TURNS", "12"))
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "60"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "350"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.4"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))
OLLAMA_TOP_K = int(os.getenv("OLLAMA_TOP_K", "40"))
LLM_MIN_NARRATIVE_CHARS = int(os.getenv("LLM_MIN_NARRATIVE_CHARS", "160"))
OLLAMA_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv("OLLAMA_FALLBACK_MODELS", "").split(",")
    if model.strip()
]

# Gameplay
MAX_OPTIONS = 4
