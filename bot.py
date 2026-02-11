import asyncio
import logging
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from src.config import BOT_TOKEN, OLLAMA_FALLBACK_MODELS, OLLAMA_MODEL
from src.db import get_state, init_db, set_state
from src.game.engine import build_intro, process_action
from src.game.state import (
    advance_question,
    apply_answer,
    creation_complete,
    inventory_capacity,
    new_creation_state,
    next_question,
)

logging.basicConfig(level=logging.INFO)


def _question_keyboard(question: Dict) -> Optional[ReplyKeyboardMarkup]:
    if question.get("type") != "choice":
        return None
    buttons = [
        [KeyboardButton(text=f"{i}. {opt['label']}")]
        for i, opt in enumerate(question.get("options", []), start=1)
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def _stats_text(character: Dict) -> str:
    special = character["special"]
    items = ", ".join(character.get("items", [])) or "ничего"
    status = ", ".join(character.get("status", [])) or "нет"
    capacity = inventory_capacity(character)
    return (
        f"Имя: {character.get('name') or '—'}\n"
        f"Фракция: {character.get('faction') or '—'}\n"
        f"Пол: {character.get('gender') or '—'}\n"
        f"SPECIAL:\n"
        f"Сила: {special['strength']}\n"
        f"Восприятие: {special['perception']}\n"
        f"Выносливость: {special['endurance']}\n"
        f"Харизма: {special['charisma']}\n"
        f"Интеллект: {special['intelligence']}\n"
        f"Ловкость: {special['agility']}\n"
        f"Удача: {special['luck']}\n"
        f"Здоровье: {character['health']}\n"
        f"Богатство: {character['wealth']}\n"
        f"Оружие: {character.get('weapon') or 'нож'}\n"
        f"Броня: {character.get('armor') or 'без брони'}\n"
        f"Инвентарь: {len(character.get('items', []))}/{capacity}\n"
        f"Предметы: {items}\n"
        f"Статусы: {status}"
    )


def _format_intro(backstory: str, narrative: str, options: list[str]) -> str:
    lines = [backstory, "", narrative]
    if options:
        lines.append("\nВозможные действия:")
        for i, opt in enumerate(options, start=1):
            lines.append(f"{i}. {opt}")
    return "\n".join(lines)


def _options_keyboard(options: list[str]) -> Optional[ReplyKeyboardMarkup]:
    if not options:
        return None
    buttons = [[KeyboardButton(text=str(i)) for i in range(1, len(options) + 1)]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def _available_models() -> list[str]:
    models = [OLLAMA_MODEL]
    for model in OLLAMA_FALLBACK_MODELS:
        if model and model not in models:
            models.append(model)
    return models


async def start_new_game(message: Message) -> None:
    data = new_creation_state()
    context = []
    set_state(message.from_user.id, "creating", data, context)

    question = next_question(data)
    if not question:
        await message.answer("Не удалось начать создание персонажа.")
        return

    keyboard = _question_keyboard(question)
    await message.answer(
        "Добро пожаловать в 'Русичи: Текстовое приключение'.\n"
        "Ответь на несколько вопросов, чтобы создать героя.",
        reply_markup=keyboard or ReplyKeyboardRemove(),
    )
    await message.answer(question["text"], reply_markup=keyboard or ReplyKeyboardRemove())


async def handle_creation(message: Message, state: Dict) -> None:
    data = state["data"]
    question = next_question(data)
    if not question:
        await message.answer("Создание персонажа уже завершено.")
        return

    ok, error_text = apply_answer(data, question, message.text or "")
    if not ok:
        keyboard = _question_keyboard(question)
        await message.answer(error_text, reply_markup=keyboard or ReplyKeyboardRemove())
        await message.answer(question["text"], reply_markup=keyboard or ReplyKeyboardRemove())
        return

    advance_question(data)
    if creation_complete(data):
        character = data["character"]
        backstory, narrative, options = build_intro(data)
        data["backstory"] = backstory
        data["last_options"] = options
        context = [{"role": "assistant", "content": f"{backstory}\n\n{narrative}"}]
        set_state(message.from_user.id, "playing", data, context)

        await message.answer(
            "Персонаж создан.\n" + _stats_text(character),
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer(
            _format_intro(backstory, narrative, options),
            reply_markup=_options_keyboard(options) or ReplyKeyboardRemove(),
        )
        return

    next_q = next_question(data)
    keyboard = _question_keyboard(next_q)
    await message.answer(next_q["text"], reply_markup=keyboard or ReplyKeyboardRemove())
    set_state(message.from_user.id, "creating", data, state["context"])


async def handle_play(message: Message, state: Dict) -> None:
    data = state["data"]
    context = state["context"]
    action = (message.text or "").strip()

    if not action:
        await message.answer("Опиши действие словами.")
        return

    reply_text, new_context, game_over = process_action(data, context, action)

    if game_over:
        set_state(message.from_user.id, "dead", data, new_context)
        await message.answer(
            reply_text + "\n\nТвой путь окончен. Напиши /newgame чтобы начать заново."
        )
        return

    set_state(message.from_user.id, "playing", data, new_context)
    options = data.get("last_options") or []
    await message.answer(
        reply_text,
        reply_markup=_options_keyboard(options) or ReplyKeyboardRemove(),
    )


async def show_stats(message: Message, state: Dict) -> None:
    data = state["data"]
    character = data["character"]
    await message.answer(_stats_text(character))


async def help_message(message: Message) -> None:
    await message.answer(
        "Команды:\n"
        "/start — новая игра\n"
        "/newgame — начать заново\n"
        "/stats — характеристики персонажа\n"
        "/model — выбрать модель LLM"
    )


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Добавь переменную окружения BOT_TOKEN.")

    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    await bot.delete_webhook(drop_pending_updates=True)

    dp.message.register(start_new_game, CommandStart())
    dp.message.register(start_new_game, Command("newgame"))
    dp.message.register(help_message, Command("help"))

    @dp.message(Command("model"))
    async def model_cmd(message: Message) -> None:
        state = get_state(message.from_user.id)
        if not state:
            await message.answer("Сначала начни игру: /start")
            return

        data = state["data"]
        models = _available_models()
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 1:
            current = data.get("llm_model") or OLLAMA_MODEL
            lines = [f"Текущая модель: {current}", "Доступные модели:"]
            for i, model in enumerate(models, start=1):
                lines.append(f"{i}. {model}")
            lines.append("Чтобы переключить: /model <номер> или /model <имя>")
            await message.answer("\n".join(lines))
            return

        choice = parts[1].strip()
        selected = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
        else:
            for model in models:
                if model == choice:
                    selected = model
                    break

        if not selected:
            await message.answer("Не понял выбор. Введи номер или точное имя модели.")
            return

        data["llm_model"] = selected
        set_state(message.from_user.id, state["state"], data, state["context"])
        await message.answer(f"Модель переключена на: {selected}")

    @dp.message(Command("stats"))
    async def stats_cmd(message: Message) -> None:
        state = get_state(message.from_user.id)
        if not state:
            await message.answer("Сначала начни игру: /start")
            return
        await show_stats(message, state)

    @dp.message(F.text)
    async def text_handler(message: Message) -> None:
        state = get_state(message.from_user.id)
        if not state:
            await start_new_game(message)
            return

        if state["state"] == "creating":
            await handle_creation(message, state)
            return
        if state["state"] == "playing":
            await handle_play(message, state)
            return
        if state["state"] == "dead":
            await message.answer("Игра окончена. Напиши /newgame чтобы начать заново.")
            return

        await start_new_game(message)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
