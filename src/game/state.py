from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

BASE_SPECIAL = {
    "strength": 3,
    "perception": 3,
    "endurance": 3,
    "charisma": 3,
    "intelligence": 3,
    "agility": 3,
    "luck": 3,
}


QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "faction",
        "type": "choice",
        "text": "К чьей стороне ты принадлежишь?",
        "options": [
            {
                "label": "Русич",
                "effects": {"charisma": 1},
                "data": {"faction": "Русич"},
            },
            {
                "label": "Воин Орды",
                "effects": {"strength": 1, "charisma": -1},
                "data": {"faction": "Воин Орды"},
            },
        ],
    },
    {
        "id": "name",
        "type": "text",
        "text": "Назови имя своего героя.",
    },
    {
        "id": "gender",
        "type": "choice",
        "text": "Укажи пол персонажа.",
        "options": [
            {
                "label": "Мужчина",
                "data": {"gender": "мужчина"},
            },
            {
                "label": "Женщина",
                "data": {"gender": "женщина"},
            },
        ],
    },
    {
        "id": "origin",
        "type": "choice",
        "text": "Где прошло твое детство?",
        "options": [
            {
                "label": "Деревня",
                "effects": {"strength": 1, "endurance": 1},
            },
            {
                "label": "Город",
                "effects": {"perception": 1, "charisma": 1},
            },
            {
                "label": "Степь",
                "effects": {"agility": 1, "endurance": 1},
            },
        ],
    },
    {
        "id": "weapon",
        "type": "choice",
        "text": "Какое оружие тебе ближе?",
        "options": [
            {
                "label": "Копье",
                "effects": {"strength": 1},
                "add_items": ["копье"],
                "data": {"weapon": "копье"},
            },
            {
                "label": "Лук",
                "effects": {"perception": 1},
                "add_items": ["лук", "стрелы"],
                "data": {"weapon": "лук"},
            },
            {
                "label": "Топор",
                "effects": {"strength": 1},
                "add_items": ["топор"],
                "data": {"weapon": "топор"},
            },
        ],
    },
    {
        "id": "armor",
        "type": "choice",
        "text": "Какую защиту предпочитаешь?",
        "options": [
            {
                "label": "Без брони",
                "effects": {"agility": 1},
                "data": {"armor": "без брони"},
            },
            {
                "label": "Стеганка",
                "effects": {"endurance": 1},
                "add_items": ["стеганка"],
                "data": {"armor": "стеганка"},
            },
            {
                "label": "Кольчуга",
                "effects": {"strength": 1, "agility": -1},
                "add_items": ["кольчуга"],
                "data": {"armor": "кольчуга"},
            },
        ],
    },
    {
        "id": "approach",
        "type": "choice",
        "text": "Как ты обычно решаешь споры?",
        "options": [
            {
                "label": "Убеждаю",
                "effects": {"charisma": 1},
            },
            {
                "label": "Силой",
                "effects": {"strength": 1},
            },
            {
                "label": "Хитростью",
                "effects": {"intelligence": 1},
            },
        ],
    },
    {
        "id": "value",
        "type": "choice",
        "text": "Что для тебя важнее всего?",
        "options": [
            {
                "label": "Честь",
                "effects": {"charisma": 1, "luck": -1},
            },
            {
                "label": "Выгода",
                "effects": {"intelligence": 1, "charisma": -1},
            },
            {
                "label": "Семья",
                "effects": {"endurance": 1, "luck": 1},
            },
        ],
    },
]


def new_character_state() -> Dict[str, Any]:
    return {
        "name": None,
        "faction": None,
        "gender": None,
        "special": dict(BASE_SPECIAL),
        "health": 3,
        "wealth": 3,
        "items": ["нож", "плащ"],
        "weapon": "нож",
        "armor": "без брони",
        "status": [],
        "flags": [],
        "location": "дорога",
        "goal": "стать главой своей фракции",
    }


def new_creation_state() -> Dict[str, Any]:
    return {
        "creation": {
            "index": 0,
            "answers": {},
        },
        "character": new_character_state(),
        "world": {
            "day": 1,
            "season": "весна",
        },
        "scene_memory": [],
        "llm_model": None,
        "last_options": [],
    }


def clamp_stat(value: int, *, min_value: int = 1) -> int:
    return max(min_value, min(6, value))


def apply_effects(
    stats: Dict[str, int],
    effects: Dict[str, int],
    *,
    min_value: int = 1,
) -> None:
    for key, delta in effects.items():
        if key not in stats:
            continue
        stats[key] = clamp_stat(stats[key] + int(delta), min_value=min_value)


def resolve_choice(question: Dict[str, Any], answer_text: str) -> Optional[Dict[str, Any]]:
    options = question.get("options", [])
    if not options:
        return None

    # Accept numeric choice (1..n)
    stripped = answer_text.strip()
    if stripped.isdigit():
        idx = int(stripped) - 1
        if 0 <= idx < len(options):
            return options[idx]

    # Accept if answer contains option label
    lowered = stripped.lower()
    for opt in options:
        if opt["label"].lower() in lowered:
            return opt

    return None


def apply_answer(data: Dict[str, Any], question: Dict[str, Any], answer_text: str) -> Tuple[bool, str]:
    qid = question["id"]
    character = data["character"]

    if question["type"] == "text":
        name = answer_text.strip()
        if not name:
            return False, "Имя не может быть пустым. Попробуй еще раз."
        character["name"] = name
        data["creation"]["answers"][qid] = name
        return True, ""

    choice = resolve_choice(question, answer_text)
    if not choice:
        return False, "Не понял выбор. Напиши номер варианта или слово из ответа."

    data["creation"]["answers"][qid] = choice["label"]

    if "effects" in choice:
        apply_effects(character["special"], choice["effects"], min_value=1)
        character["health"] = clamp_stat(character["special"]["endurance"], min_value=0)

    if "add_items" in choice:
        for item in choice["add_items"]:
            if item not in character["items"]:
                if len(character["items"]) < inventory_capacity(character):
                    character["items"].append(item)

    if "data" in choice:
        for key, value in choice["data"].items():
            character[key] = value
            if key == "weapon" and value not in character["items"]:
                if len(character["items"]) < inventory_capacity(character):
                    character["items"].append(value)
            if key == "armor" and value != "без брони" and value not in character["items"]:
                if len(character["items"]) < inventory_capacity(character):
                    character["items"].append(value)

    return True, ""


def creation_complete(data: Dict[str, Any]) -> bool:
    return data["creation"]["index"] >= len(QUESTIONS)


def next_question(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    idx = data["creation"]["index"]
    if idx >= len(QUESTIONS):
        return None
    return QUESTIONS[idx]


def advance_question(data: Dict[str, Any]) -> None:
    data["creation"]["index"] += 1


def inventory_capacity(character: Dict[str, Any]) -> int:
    special = character["special"]
    return max(1, special["strength"] + special["endurance"])
