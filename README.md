# Русичи: Текстовое приключение

## Быстрый старт (Docker)
1. Скопируй `.env.example` в `.env` и укажи `BOT_TOKEN`.
2. Запусти контейнеры:
   ```bash
   docker compose up -d --build
   ```
3. Скачай модель в Ollama:
   ```bash
   docker exec -it rusichi-ollama ollama pull gemma3:4b-it-q4_K_M
   ```
4. (Опционально) Скачай fallback-модели:
   ```bash
   docker exec -it rusichi-ollama ollama pull smollm2:360m-instruct-q4_K_M
   docker exec -it rusichi-ollama ollama pull smollm2:135m-instruct-q4_K_M
   ```
5. Перезапусти бота (если нужно):
   ```bash
   docker compose restart bot
   ```

## Команды бота
- `/start` — новая игра
- `/newgame` — начать заново
- `/stats` — характеристики
- `/model` — выбрать модель LLM

## Переменные окружения
- `BOT_TOKEN` — токен Telegram бота
- `OLLAMA_MODEL` — модель Ollama (по умолчанию `gemma3:4b-it-q4_K_M`)
- `DB_PATH` — путь к SQLite базе (по умолчанию `game.db`)
- `CONTEXT_TURNS` — сколько последних реплик хранить в контексте (по умолчанию `8`)
- `OLLAMA_NUM_CTX` — размер контекста в токенах для Ollama (по умолчанию `2048`)
- `OLLAMA_NUM_PREDICT` — максимальная длина ответа (по умолчанию `320`)
- `OLLAMA_TEMPERATURE` — температура (по умолчанию `0.4`)
- `OLLAMA_TOP_P` — top‑p (по умолчанию `0.9`)
- `OLLAMA_TOP_K` — top‑k (по умолчанию `40`)
- `LLM_MIN_NARRATIVE_CHARS` — минимальная длина описания (по умолчанию `180`)
- `OLLAMA_FALLBACK_MODELS` — список fallback-моделей через запятую
