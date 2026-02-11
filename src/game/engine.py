from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Tuple

from .dice import roll_d6
from .prompts import COMBAT_PROMPT_TEMPLATE, INTRO_PROMPT, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from .state import apply_effects, clamp_stat, inventory_capacity
from ..config import (
    CONTEXT_TURNS,
    LLM_MIN_NARRATIVE_CHARS,
    MAX_OPTIONS,
    OLLAMA_FALLBACK_MODELS,
    OLLAMA_MODEL,
)
from ..llm.ollama_client import chat, extract_json

STAT_LABELS = {
    "strength": "Сила",
    "perception": "Восприятие",
    "endurance": "Выносливость",
    "charisma": "Харизма",
    "intelligence": "Интеллект",
    "agility": "Ловкость",
    "luck": "Удача",
}

BANNED_TERMS = [
    "телефон",
    "смартфон",
    "интернет",
    "компьютер",
    "машина",
    "автомобиль",
    "мотоцикл",
    "пистолет",
    "автомат",
    "граната",
    "самолет",
    "вертолет",
    "ракета",
    "лазер",
    "джедай",
    "космос",
    "магия",
    "колдун",
    "заклин",
    "эльф",
    "орк",
    "дракон",
    "портал",
    "робот",
    "киборг",
    "плазм",
    "револьвер",
    "гильза",
]

COMBAT_KEYWORDS = [
    "удар",
    "атак",
    "сраж",
    "битв",
    "бью",
    "убью",
    "заруб",
    "рассек",
    "колю",
    "стрел",
    "топор",
    "меч",
    "копь",
]

FLEE_KEYWORDS = [
    "убежать",
    "бежать",
    "отступ",
    "скрыться",
    "уход",
    "отойти",
]

DEFEND_KEYWORDS = [
    "защищ",
    "парир",
    "уклон",
    "прикры",
    "щит",
]

SOCIAL_KEYWORDS = [
    "уговор",
    "убед",
    "переговор",
    "договор",
    "обман",
    "хитр",
    "обещ",
    "мол",
    "прос",
    "запуг",
    "угрож",
]

WEALTH_KEYWORDS = [
    "куп",
    "прод",
    "торг",
    "рынок",
    "монет",
    "сереб",
    "золото",
    "дань",
    "пошлин",
    "подкуп",
]

PERCEPTION_KEYWORDS = [
    "осмотр",
    "замет",
    "наблюд",
    "след",
    "выслед",
    "прислуш",
]

STEALTH_KEYWORDS = [
    "скрыт",
    "крад",
    "тихо",
    "подкрад",
]

INVENTORY_KEYWORDS = [
    "оруж",
    "доспех",
    "снаряж",
    "почин",
    "чинить",
    "экип",
    "лук",
    "меч",
    "топор",
    "копь",
]

HEALTH_KEYWORDS = [
    "болез",
    "яд",
    "отрав",
    "рана",
    "леч",
    "перевяз",
    "кров",
]

PHYSICAL_KEYWORDS = [
    "удар",
    "атак",
    "сраж",
    "битв",
    "бег",
    "прыг",
    "лез",
    "плы",
]

RISKY_KEYWORDS = [
    "ночью",
    "напролом",
    "в одиночку",
    "срочно",
    "без подготовки",
]

CAREFUL_KEYWORDS = [
    "осторож",
    "тихо",
    "скрыт",
    "подготов",
    "осмотр",
    "развед",
]

PLACE_KEYWORDS = {
    "tavern": ["таверн", "корчм", "постоял", "трактир"],
    "village": ["деревн", "село", "поселен", "селен", "слоб"],
    "market": ["рынок", "торг", "ярмарк"],
    "forest": ["лес", "чащ", "роща"],
    "river": ["река", "брод", "переправ"],
    "road": ["дорог", "тракт", "путь"],
    "church": ["церк", "храм", "молитв", "часовн"],
}

PLACE_LABELS = {
    "tavern": "таверна",
    "village": "селение",
    "market": "рынок",
    "forest": "лес",
    "river": "река",
    "road": "дорога",
    "church": "церковь",
}

PLACE_DETAIL_KEYWORDS = {
    "tavern": ["дым", "круж", "лавк", "огон", "похлеб", "жар", "трактир", "корчм", "звон", "стол"],
    "village": ["изб", "плет", "колод", "дым", "печ", "ворот", "улиц", "скот", "двор"],
    "market": ["лавк", "торг", "ряд", "купц", "монет", "шум", "толп", "товар"],
    "forest": ["чащ", "мох", "ствол", "ветв", "тень", "птиц", "шорох"],
    "river": ["течен", "берег", "брод", "вода", "камыш", "переправ", "льдин"],
    "road": ["тракт", "колея", "пыль", "гряз", "след", "обочин"],
    "church": ["колокол", "свеч", "икон", "воск", "притвор", "алтар", "ладан"],
}

GENERAL_DETAIL_KEYWORDS = [
    "ветер",
    "запах",
    "дым",
    "шум",
    "холод",
    "тепл",
    "сыр",
    "пыль",
    "гряз",
    "свет",
    "тень",
    "скрип",
    "стук",
    "шепот",
    "голос",
    "крик",
    "жар",
    "кров",
    "боль",
    "огонь",
    "влага",
    "мокр",
]

STOPWORDS = {
    "и",
    "в",
    "на",
    "к",
    "ко",
    "по",
    "с",
    "со",
    "из",
    "у",
    "от",
    "до",
    "за",
    "под",
    "над",
    "о",
    "об",
    "про",
    "для",
    "без",
    "что",
    "это",
    "как",
    "я",
    "мы",
    "ты",
    "вы",
    "он",
    "она",
    "они",
    "его",
    "ее",
    "их",
    "мне",
    "моя",
    "мой",
    "твой",
    "наш",
    "ваш",
    "свой",
    "есть",
    "буду",
    "будет",
    "быть",
    "иду",
    "иду",
    "идти",
    "пойду",
    "хочу",
}

ENEMY_TEMPLATES_RUS = [
    {"name": "татарский дозорный", "hp": 6, "attack": 2, "defense": 1},
    {"name": "степной разбойник", "hp": 5, "attack": 2, "defense": 0},
    {"name": "волк", "hp": 4, "attack": 2, "defense": 0},
]

ENEMY_TEMPLATES_ORD = [
    {"name": "русский дозорный", "hp": 6, "attack": 2, "defense": 1},
    {"name": "лесной разбойник", "hp": 5, "attack": 2, "defense": 0},
    {"name": "кабан-секач", "hp": 5, "attack": 2, "defense": 0},
]

WEAPONS = {
    "нож": {"damage": 1, "stat": "agility", "crit_bonus": 0, "range": "melee"},
    "топор": {"damage": 3, "stat": "strength", "crit_bonus": 1, "range": "melee"},
    "копье": {"damage": 2, "stat": "strength", "crit_bonus": 1, "range": "melee"},
    "лук": {"damage": 2, "stat": "perception", "crit_bonus": 1, "range": "ranged"},
}

ARMORS = {
    "без брони": {"defense": 0, "agility_penalty": 0},
    "стеганка": {"defense": 1, "agility_penalty": 0},
    "кольчуга": {"defense": 2, "agility_penalty": 1},
    "ламеллярный доспех": {"defense": 2, "agility_penalty": 1},
}


def _contains_any(text: str, keywords: List[str]) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def _place_from_text(text: str) -> Optional[str]:
    lower = text.lower()
    for place, keywords in PLACE_KEYWORDS.items():
        if _contains_any(lower, keywords):
            return place
    return None


def _action_place(action: str, location: Optional[str] = None) -> Optional[str]:
    place = _place_from_text(action)
    if place:
        return place
    if location:
        return _place_from_text(location)
    return None


def _update_location(data: Dict[str, Any], action: str) -> None:
    place = _action_place(action)
    if not place:
        return
    label = PLACE_LABELS.get(place)
    if label:
        data["character"]["location"] = label


def _scene_memory_text(data: Dict[str, Any]) -> str:
    memory = data.get("scene_memory", [])
    if isinstance(memory, list) and memory:
        return " | ".join(memory[-2:])
    if isinstance(memory, str):
        return memory
    return ""


def _fallback_memory(
    *,
    action: str,
    narrative: str,
    location: Optional[str],
    enemy_name: Optional[str] = None,
) -> str:
    sentence = narrative.strip().split("\n", 1)[0]
    sentence = sentence[:160].strip()
    parts = []
    if location:
        parts.append(f"Ты находишься в месте: {location}")
    if enemy_name:
        parts.append(f"Рядом противник: {enemy_name}")
    if action:
        parts.append(f"Ключевое действие: {action}")
    if sentence:
        parts.append(f"Итог: {sentence}")
    return ". ".join(parts)[:220]


def _update_scene_memory(
    data: Dict[str, Any],
    *,
    memory: Optional[str],
    action: str,
    narrative: str,
    enemy_name: Optional[str] = None,
) -> None:
    location = data.get("character", {}).get("location")
    text = (memory or "").strip()
    if not text or len(text) < 20 or not re.search(r"[А-Яа-я]", text):
        text = _fallback_memory(
            action=action,
            narrative=narrative,
            location=location,
            enemy_name=enemy_name,
        )
    history = data.get("scene_memory")
    if not isinstance(history, list):
        history = []
    history.append(text)
    data["scene_memory"] = history[-3:]


def _required_terms_for_action(action: str, location: Optional[str] = None) -> List[str]:
    place = _action_place(action, location)
    if not place:
        return []
    return PLACE_KEYWORDS.get(place, [])


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?]+", text))


def _action_terms(action: str) -> List[str]:
    words = re.findall(r"[а-яё]+", action.lower())
    terms = [w for w in words if len(w) >= 4 and w not in STOPWORDS]
    return list(dict.fromkeys(terms))[:6]


def _mentions_action(narrative: str, action: str) -> bool:
    if not narrative:
        return False
    if not action:
        return True
    lowered = action.lower().strip()
    if lowered in ("начало игры", "старт", "start"):
        return True
    terms = _action_terms(action)
    if not terms:
        return True
    lower_n = narrative.lower()
    return any(term in lower_n for term in terms)


def _has_scene_detail(narrative: str, action: str, location: Optional[str] = None) -> bool:
    lower = narrative.lower()
    place = _action_place(action, location)
    if place:
        details = PLACE_DETAIL_KEYWORDS.get(place, [])
        if details and not any(term in lower for term in details):
            return False
        return True
    return any(term in lower for term in GENERAL_DETAIL_KEYWORDS)


def is_out_of_setting(action: str) -> bool:
    lower = action.lower()
    return any(term in lower for term in BANNED_TERMS)

def is_combat_action(action: str) -> bool:
    return _contains_any(action, COMBAT_KEYWORDS)

def resolve_action_text(data: Dict[str, Any], action: str) -> str:
    stripped = action.strip()
    if stripped.isdigit():
        idx = int(stripped) - 1
        options = data.get("last_options") or []
        if 0 <= idx < len(options):
            return options[idx]
    return action

def _default_options() -> List[str]:
    return [
        "Осмотреться и оценить обстановку",
        "Поговорить с ближайшими людьми",
        "Продумать осторожный план",
        "Проверить снаряжение и подготовиться",
    ]

def _combat_options() -> List[str]:
    return [
        "Атаковать",
        "Защититься",
        "Попытаться отступить",
    ]


def _contextual_options(action: str, location: Optional[str] = None) -> List[str]:
    place = _action_place(action, location)
    if place == "tavern":
        return [
            "Поговорить с хозяином",
            "Присесть к столу с местными",
            "Заказать еду и слушать разговоры",
            "Оглядеться у входа и понять, кто следит",
        ]
    if place == "village":
        return [
            "Расспросить старосту",
            "Искать ночлег",
            "Осмотреть околицы",
            "Проверить дворы и хозяйственные следы",
        ]
    if place == "market":
        return [
            "Пройтись между лавками",
            "Поторговаться с купцами",
            "Поспрашивать новости",
            "Найти ремесленника или кузнеца",
        ]
    if place == "forest":
        return [
            "Искать тропу",
            "Проверить следы",
            "Развести осторожный привал",
            "Подняться на пригорок и оглядеться",
        ]
    if place == "river":
        return [
            "Осмотреть брод",
            "Поговорить с перевозчиком",
            "Найти безопасный переход",
            "Проверить лодки и береговые следы",
        ]
    if place == "church":
        return [
            "Поговорить со священником",
            "Поставить свечу и осмотреться",
            "Спросить о ночлеге",
            "Попросить совета или приюта",
        ]
    return _default_options()

def create_enemy(character: Dict[str, Any]) -> Dict[str, Any]:
    faction = character.get("faction") or "Русич"
    pool = ENEMY_TEMPLATES_RUS if faction == "Русич" else ENEMY_TEMPLATES_ORD
    template = random.choice(pool)
    strength = character["special"]["strength"]
    endurance = character["special"]["endurance"]
    hp = template["hp"] + max(0, (strength + endurance) // 4 - 1)
    return {
        "name": template["name"],
        "hp": hp,
        "attack": template["attack"],
        "defense": template["defense"],
    }


def _llm_models(data: Dict[str, Any]) -> List[str]:
    override = data.get("llm_model")
    models = [override or OLLAMA_MODEL]
    for model in OLLAMA_FALLBACK_MODELS:
        if model and model not in models:
            models.append(model)
    return models


def _is_valid_narrative(
    narrative: Optional[str],
    options: List[str],
    action: str,
    location: Optional[str] = None,
) -> bool:
    if not narrative:
        return False
    if len(narrative.strip()) < LLM_MIN_NARRATIVE_CHARS:
        return False
    paragraphs = [p for p in narrative.split("\n\n") if p.strip()]
    if len(paragraphs) < 2:
        return False
    if _sentence_count(narrative) < 2:
        return False
    if not re.search(r"[А-Яа-я]", narrative):
        return False
    if len(options) < 2:
        return False
    required_terms = _required_terms_for_action(action, location)
    if required_terms:
        lower = narrative.lower()
        if not any(term in lower for term in required_terms):
            return False
    if not _mentions_action(narrative, action):
        return False
    if not _has_scene_detail(narrative, action, location):
        return False
    return True


def _call_llm_json(messages: List[Dict[str, str]], models: List[str]) -> Optional[Dict[str, Any]]:
    for model in models:
        try:
            response = chat(messages, model=model, response_format="json")
            content = response.get("message", {}).get("content", "")
            data_json = extract_json(content)
            if data_json:
                return data_json
        except Exception:
            continue
    return None


def get_weapon(character: Dict[str, Any]) -> Dict[str, Any]:
    weapon_name = character.get("weapon") or "нож"
    return WEAPONS.get(weapon_name, WEAPONS["нож"])


def get_armor(character: Dict[str, Any]) -> Dict[str, Any]:
    armor_name = character.get("armor") or "без брони"
    return ARMORS.get(armor_name, ARMORS["без брони"])

def ensure_combat(data: Dict[str, Any]) -> Dict[str, Any]:
    combat = data.get("combat")
    if combat and combat.get("active"):
        return combat
    enemy = create_enemy(data["character"])
    combat = {
        "active": True,
        "round": 1,
        "enemy": enemy,
    }
    data["combat"] = combat
    return combat

def choose_stat(action: str) -> str:
    if _contains_any(action, HEALTH_KEYWORDS):
        return "endurance"
    if _contains_any(action, SOCIAL_KEYWORDS):
        return "charisma"
    if _contains_any(action, WEALTH_KEYWORDS):
        return "charisma"
    if _contains_any(action, PERCEPTION_KEYWORDS):
        return "perception"
    if _contains_any(action, STEALTH_KEYWORDS):
        return "agility"
    if _contains_any(action, INVENTORY_KEYWORDS):
        return "strength"
    if _contains_any(action, PHYSICAL_KEYWORDS):
        return "strength"
    return "endurance"


def compute_difficulty(stat_value: int, action: str) -> int:
    difficulty = 3
    if stat_value <= 2:
        difficulty += 1
    elif stat_value >= 5:
        difficulty -= 1

    if _contains_any(action, RISKY_KEYWORDS):
        difficulty += 1
    if _contains_any(action, CAREFUL_KEYWORDS):
        difficulty -= 1

    return max(1, min(6, difficulty))


def _trim_context(context: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if len(context) <= CONTEXT_TURNS:
        return context
    return context[-CONTEXT_TURNS :]


def _context_summary(
    context: List[Dict[str, str]],
    data: Optional[Dict[str, Any]] = None,
) -> str:
    trimmed = _trim_context(context)
    parts = []
    if data:
        character = data.get("character", {})
        location = character.get("location")
        status = ", ".join(character.get("status", [])) or ""
        memory = _scene_memory_text(data)
        if location:
            parts.append(f"Текущее место: {location}.")
        if status:
            parts.append(f"Состояние: {status}.")
        if memory:
            parts.append(f"Память сцены: {memory}.")
    for msg in trimmed[-6:]:
        role = "Игрок" if msg["role"] == "user" else "Ведущий"
        parts.append(f"{role}: {msg['content']}")
    return "\n".join(parts) if parts else "Пока без событий."


def _normalize_effects(effects: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "strength": 0,
        "perception": 0,
        "endurance": 0,
        "charisma": 0,
        "intelligence": 0,
        "agility": 0,
        "luck": 0,
        "health": 0,
        "wealth": 0,
        "add_items": [],
        "remove_items": [],
    }
    if not effects:
        return normalized

    for key in [
        "strength",
        "perception",
        "endurance",
        "charisma",
        "intelligence",
        "agility",
        "luck",
        "health",
        "wealth",
    ]:
        if key in effects:
            try:
                val = int(effects[key])
            except (ValueError, TypeError):
                val = 0
            normalized[key] = max(-2, min(2, val))

    for key in ["add_items", "remove_items"]:
        items = effects.get(key, [])
        if isinstance(items, list):
            normalized[key] = [str(item)[:32] for item in items[:3]]

    return normalized


def apply_affliction(character: Dict[str, Any]) -> Tuple[Optional[str], bool]:
    status: List[str] = character.get("status", [])
    health = character["health"]

    note = None
    died = False

    if "болезнь" not in status and "отравление" not in status:
        if roll_d6() == 1:
            affliction = random.choice(["болезнь", "отравление"])
            status.append(affliction)
            character["health"] = clamp_stat(health - 1, min_value=0)
            note = f"Тебя накрывает {affliction}: слабость и жар сбивают с ног."
    else:
        roll = roll_d6()
        if roll == 1:
            character["health"] = 0
            died = True
            note = "Хворь берет верх — силы покидают тебя."
        elif roll <= 3:
            character["health"] = clamp_stat(health - 1, min_value=0)
            note = "Слабость усиливается, каждый шаг дается тяжелее."

    character["status"] = status
    return note, died


def _combat_action_type(action: str) -> str:
    if _contains_any(action, FLEE_KEYWORDS):
        return "flee"
    if _contains_any(action, DEFEND_KEYWORDS):
        return "defend"
    return "attack"


def _combat_stat(action: str, action_type: str) -> str:
    if action_type == "flee":
        return "agility"
    if action_type == "defend":
        return "agility"
    if "стрел" in action or "лук" in action:
        return "perception"
    return "strength"


def _combat_fallback_narrative(
    *,
    action: str,
    success: bool,
    enemy_name: str,
    player_damage: int,
    enemy_hit: bool,
    enemy_damage: int,
) -> str:
    lines = []
    if success:
        if player_damage > 0:
            lines.append(
                f"Ты бросаешься в атаку и находишь брешь — удар достигает {enemy_name}."
            )
        else:
            lines.append(
                f"Ты действуешь решительно, но {enemy_name} уходит в сторону в последний миг."
            )
    else:
        lines.append(
            f"Твое движение выдает себя: {enemy_name} встречает тебя холодным, точным шагом."
        )
    if enemy_hit and enemy_damage > 0:
        lines.append(
            f"В ответ {enemy_name} наносит удар, оставляя жгучую боль."
        )
    elif enemy_hit:
        lines.append(
            f"{enemy_name} пытается достать тебя, но ты успеваешь увести корпус."
        )
    else:
        lines.append(
            f"{enemy_name} не успевает перехватить инициативу."
        )
    return "\n\n".join(lines)


def _fallback_narrative(action: str, success: bool) -> str:
    if success:
        p1 = (
            f"Ты берешься за задуманное: {action}. "
            "Порывы ветра несут сырой холод, под ногами шуршит прошлогодняя трава, "
            "а вдалеке слышится глухой шум людских голосов."
        )
        p2 = (
            "Твой шаг меняет обстановку: кто-то замечает тебя, и пространство вокруг будто оживает. "
            "Перед тобой возникает новая развилка, где каждое решение тянет за собой последствия."
        )
        return "\n\n".join([p1, p2])
    p1 = (
        f"Ты пытаешься выполнить задуманное: {action}. "
        "Сырая земля тянет сапоги, воздух тяжелый и холодный, а вокруг не видно надежных ориентиров."
    )
    p2 = (
        "Попытка выходит боком: обстоятельства встречают тебя настороженно, и путь усложняется. "
        "Однако шанс исправить ошибку остается — нужно выбрать иной ход."
    )
    return "\n\n".join([p1, p2])


def _fallback_scene(
    action: str,
    success: bool,
    location: Optional[str] = None,
) -> Tuple[str, List[str]]:
    place = _action_place(action, location)
    if place == "tavern":
        p1 = (
            "Ты входишь в таверну, где густой дым висит под потолком, а на деревянных лавках "
            "теснятся путники и местные. Глухие разговоры, звон кружек и треск огня создают "
            "тяжелую, но живую атмосферу."
        )
        p2 = (
            "Твой шаг уверенный, и ты сразу ловишь на себе взгляды. "
            "Кажется, здесь можно узнать новости или найти дело, но и опасность скрыта в каждом лице."
        )
        if not success:
            p2 = (
                "Ты входишь неудачно: разговоры на миг обрываются, и на тебя смотрят настороженно. "
                "Придется действовать осторожно, чтобы не навлечь беду."
            )
        return "\n\n".join([p1, p2]), _contextual_options(action, location)

    if place == "village":
        p1 = (
            "Дорога приводит тебя к небольшому селению: низкие избы, покосившиеся плетни и запах дыма "
            "из печных труб встречают у околицы. Над всем — тревожная тишина и следы тяжелых времен."
        )
        p2 = (
            "Ты замечаешь людей у колодца и понимаешь, что здесь знают новости. "
            "Есть шанс найти пристанище, но и чужаку верят не сразу."
        )
        if not success:
            p2 = (
                "В селе ты чувствуешь холодную настороженность: люди прячут взгляды и не спешат говорить. "
                "Придется проявить терпение, чтобы не спугнуть их."
            )
        return "\n\n".join([p1, p2]), _contextual_options(action, location)

    if place == "forest":
        p1 = (
            "Лес встречает густой тенью и сырым воздухом. Между стволами тянутся узкие тропы, "
            "а под ногами мягко пружинит мох."
        )
        p2 = (
            "Ты различаешь свежие следы и понимаешь, что здесь не только зверь бродит. "
            "Каждый шаг требует внимания."
        )
        if not success:
            p2 = (
                "В чаще легко потерять направление: ветви цепляются за одежду, а шумы обманчивы. "
                "Ты чувствуешь, что лес держит тебя на расстоянии."
            )
        return "\n\n".join([p1, p2]), _contextual_options(action, location)

    if place == "market":
        p1 = (
            "На рынке шумно: люди торгуются, перекликаются, в воздухе смешаны запахи дыма и сырой кожи. "
            "Ряды лавок тянутся вдоль площади."
        )
        p2 = (
            "Ты видишь, где можно и выгодно обменять товар, и услышать новости. "
            "Но любая сделка здесь требует острого взгляда."
        )
        if not success:
            p2 = (
                "Толпа давит со всех сторон, и ты ощущаешь, как легко здесь стать добычей ловких рук. "
                "Придется быть внимательным."
            )
        return "\n\n".join([p1, p2]), _contextual_options(action, location)

    if place == "river":
        p1 = (
            "Перед тобой река: холодная вода несет льдинки и мусор, а течение кажется быстрым и коварным. "
            "На берегу приметны следы переправ."
        )
        p2 = (
            "Ты прикидываешь, где безопаснее перейти и кто мог бы помочь. "
            "Неосторожность здесь может стоить жизни."
        )
        if not success:
            p2 = (
                "Берег скользкий, и течение выглядит опаснее, чем казалось издалека. "
                "Любая ошибка обернется бедой."
            )
        return "\n\n".join([p1, p2]), _contextual_options(action, location)

    if place == "road":
        p1 = (
            "Тракт тянется серой лентой: колеи, грязь и следы копыт тянутся вдаль, а по обочинам "
            "шуршит сухая трава. Дорога живая, но опасная — здесь легко встретить и путника, и беду."
        )
        p2 = (
            "Ты прикидываешь, где идти безопаснее и кого можно встретить впереди. "
            "Каждый поворот здесь может принести новую весть."
        )
        if not success:
            p2 = (
                "Грунт размок и тянет сапоги, колеи сбивают с шага, а вдалеке мерещится чужое движение. "
                "Придется держать ухо востро."
            )
        return "\n\n".join([p1, p2]), _contextual_options(action, location)

    if place == "church":
        p1 = (
            "Небольшая церковь стоит на пригорке, и над ней звучит глухой колокольный звон. "
            "Здесь пахнет воском и сырой древесиной."
        )
        p2 = (
            "Тишина внутри давит и успокаивает одновременно. "
            "Ты понимаешь, что здесь можно найти совет или пристанище."
        )
        if not success:
            p2 = (
                "Ты чувствуешь себя чужаком: взгляды прихожан насторожены, и каждый шаг отзывается эхом. "
                "Нужно быть тактичным."
            )
        return "\n\n".join([p1, p2]), _contextual_options(action, location)

    return _fallback_narrative(action, success), _contextual_options(action, location)


def _ensure_combat_effects(combat: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    effects = combat.get("effects")
    if not effects:
        effects = {"player": {"bleed": 0, "stun": 0}, "enemy": {"bleed": 0, "stun": 0}}
        combat["effects"] = effects
    return effects


def _apply_combat_effects(
    combat: Dict[str, Any],
    character: Dict[str, Any],
    enemy: Dict[str, Any],
) -> List[str]:
    notes: List[str] = []
    effects = _ensure_combat_effects(combat)

    if effects["player"].get("bleed", 0) > 0:
        character["health"] = clamp_stat(character["health"] - 1, min_value=0)
        effects["player"]["bleed"] -= 1
        notes.append("Кровь сочится из раны, силы убывают.")

    if effects["enemy"].get("bleed", 0) > 0:
        enemy["hp"] = max(0, enemy["hp"] - 1)
        effects["enemy"]["bleed"] -= 1
        notes.append(f"{enemy['name']} слабеет от кровопотери.")

    return notes


def build_intro(data: Dict[str, Any]) -> Tuple[str, str, List[str]]:
    character = data["character"]
    world = data.get("world", {})
    special = character["special"]
    items = ", ".join(character.get("items", [])) or "ничего"
    capacity = inventory_capacity(character)
    prompt = INTRO_PROMPT.format(
        name=character["name"],
        faction=character["faction"],
        gender=character.get("gender") or "не указан",
        strength=special["strength"],
        perception=special["perception"],
        endurance=special["endurance"],
        charisma=special["charisma"],
        intelligence=special["intelligence"],
        agility=special["agility"],
        luck=special["luck"],
        health=character["health"],
        wealth=character["wealth"],
        weapon=character.get("weapon") or "нож",
        armor=character.get("armor") or "без брони",
        items=items,
        capacity=capacity,
        location=character["location"],
        season=world.get("season", "весна"),
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    data_json = _call_llm_json(messages, _llm_models(data)) or {}
    backstory = data_json.get("backstory") or "Твоя история начинается на окраине великого смутного времени."
    narrative = data_json.get("narrative") or "Ты оказываешься на дороге среди весенних ветров."
    options = data_json.get("options") or ["Осмотреться", "Пойти к ближайшему селению"]
    if not _is_valid_narrative(narrative, options, "начало игры", character.get("location")):
        narrative, options = _fallback_scene("дорога", True, character.get("location"))
        memory = None
    else:
        memory = data_json.get("memory")
    _update_scene_memory(
        data,
        memory=memory,
        action="начало игры",
        narrative=narrative,
        enemy_name=None,
    )
    return backstory, narrative, options[:MAX_OPTIONS]


def process_combat_action(
    data: Dict[str, Any],
    context: List[Dict[str, str]],
    action: str,
) -> Tuple[str, List[Dict[str, str]], bool]:
    character = data["character"]
    combat = ensure_combat(data)
    enemy = combat["enemy"]
    effect_notes = _apply_combat_effects(combat, character, enemy)

    action_type = _combat_action_type(action)
    weapon = get_weapon(character)
    armor = get_armor(character)
    stat_key = _combat_stat(action, action_type)
    if action_type == "attack":
        stat_key = weapon["stat"]
    stat_value = character["special"][stat_key]
    effects = _ensure_combat_effects(combat)
    if effects["player"].get("stun", 0) > 0:
        stat_value = max(1, stat_value - 1)
        effects["player"]["stun"] -= 1
    difficulty = compute_difficulty(stat_value, action) + enemy.get("defense", 0)
    difficulty = max(1, min(6, difficulty))
    roll = roll_d6()
    success = roll >= difficulty

    player_damage = 0
    if action_type == "attack" and success:
        stat_for_damage = character["special"][weapon["stat"]]
        base = weapon["damage"] + max(0, stat_for_damage - 2)
        player_damage = base + random.randint(0, 2)
        if roll == 6:
            player_damage += 2 + weapon.get("crit_bonus", 0)
            effects["enemy"]["stun"] = max(effects["enemy"]["stun"], 1)
        player_damage = max(0, player_damage - enemy.get("defense", 0))
        enemy["hp"] = max(0, enemy["hp"] - player_damage)
        if player_damage >= 3:
            effects["enemy"]["bleed"] = max(effects["enemy"]["bleed"], 2)

    flee_success = False
    if action_type == "flee" and success:
        flee_success = True

    enemy_hit = False
    enemy_damage = 0
    enemy_can_attack = enemy["hp"] > 0 and not flee_success
    if effects["enemy"].get("stun", 0) > 0:
        enemy_can_attack = False
        effects["enemy"]["stun"] -= 1

    if enemy_can_attack:
        agility_effective = max(1, character["special"]["agility"] - armor.get("agility_penalty", 0))
        defense_value = max(agility_effective, character["special"]["endurance"])
        enemy_diff = compute_difficulty(defense_value, "защита")
        if action_type == "defend" and success:
            enemy_diff += 1
        enemy_roll = roll_d6()
        enemy_hit = enemy_roll >= enemy_diff
        if enemy_hit:
            enemy_damage = enemy.get("attack", 1) + random.randint(0, 1)
            enemy_damage = max(0, enemy_damage - armor.get("defense", 0))
            if action_type == "defend" and success:
                enemy_damage = max(0, enemy_damage - 1)
            if enemy_roll == 6:
                enemy_damage += 1
                effects["player"]["bleed"] = max(effects["player"]["bleed"], 2)
            character["health"] = clamp_stat(character["health"] - enemy_damage, min_value=0)

    affliction_note, died = apply_affliction(character)

    battle_over = False
    if character["health"] <= 0:
        died = True
    if enemy["hp"] <= 0 or flee_success:
        battle_over = True
    else:
        combat["round"] = combat.get("round", 1) + 1

    summary = _context_summary(context, data)
    memory = _scene_memory_text(data) or "Пока без событий."
    memory = _scene_memory_text(data) or "Пока без событий."
    items = ", ".join(character.get("items", [])) or "ничего"
    capacity = inventory_capacity(character)
    special = character["special"]

    prompt = COMBAT_PROMPT_TEMPLATE.format(
        name=character["name"],
        faction=character["faction"],
        gender=character.get("gender") or "не указан",
        strength=special["strength"],
        perception=special["perception"],
        endurance=special["endurance"],
        charisma=special["charisma"],
        intelligence=special["intelligence"],
        agility=special["agility"],
        luck=special["luck"],
        health=character["health"],
        wealth=character["wealth"],
        weapon=character.get("weapon") or "нож",
        armor=character.get("armor") or "без брони",
        items=items,
        capacity=capacity,
        status=", ".join(character.get("status", [])) or "нет",
        enemy_name=enemy["name"],
        enemy_hp=enemy["hp"],
        action=action,
        stat_name=STAT_LABELS[stat_key],
        stat_value=stat_value,
        difficulty=difficulty,
        roll=roll,
        success="да" if success else "нет",
        player_damage=player_damage,
        enemy_hit="да" if enemy_hit else "нет",
        enemy_damage=enemy_damage,
        summary=summary,
        memory=memory,
    )

    messages = _trim_context(context)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    messages.append({"role": "user", "content": prompt})

    narrative = None
    options: List[str] = []

    data_json = _call_llm_json(messages, _llm_models(data)) or {}
    narrative = data_json.get("narrative")
    options = data_json.get("options") or []
    memory_out = data_json.get("memory")

    if not _is_valid_narrative(narrative, options, action, character.get("location")):
        narrative = None

    if not narrative:
        narrative = _combat_fallback_narrative(
            action=action,
            success=success,
            enemy_name=enemy["name"],
            player_damage=player_damage,
            enemy_hit=enemy_hit,
            enemy_damage=enemy_damage,
        )
        memory_out = None

    if effect_notes:
        narrative = "\n\n".join(effect_notes + [narrative])

    _update_scene_memory(
        data,
        memory=memory_out,
        action=action,
        narrative=narrative,
        enemy_name=enemy.get("name"),
    )

    if battle_over:
        data.pop("combat", None)
        if flee_success:
            options = options or [
                "Перевести дух и осмотреться",
                "Спрятаться и переждать",
                "Пойти к ближайшему укрытию",
            ]
        else:
            loot = random.choice(["мешок с монетами", "сухари", "ремень и нож"])
            if loot not in character["items"] and len(character["items"]) < capacity:
                character["items"].append(loot)
            options = options or [
                "Обыскать местность",
                "Продолжить путь",
                "Привести себя в порядок",
            ]

    if not options:
        options = _combat_options()

    data["last_options"] = options[:MAX_OPTIONS]

    reply_text = _format_reply(
        narrative,
        options,
        {
            "stat_key": stat_key,
            "roll": roll,
            "difficulty": difficulty,
            "success": success,
            "affliction": affliction_note,
        },
    )

    context.append({"role": "user", "content": action})
    context.append({"role": "assistant", "content": narrative})
    context = _trim_context(context)

    game_over = died
    return reply_text, context, game_over


def process_action(
    data: Dict[str, Any],
    context: List[Dict[str, str]],
    action: str,
) -> Tuple[str, List[Dict[str, str]], bool]:
    character = data["character"]
    action = resolve_action_text(data, action)

    if is_out_of_setting(action):
        reply = "Это вне сеттинга XIII века. Попробуй действие, уместное для Руси и Орды."
        options = _default_options()
        data["last_options"] = options[:MAX_OPTIONS]
        return _format_reply(reply, options, None), context, False

    _update_location(data, action)
    location = character.get("location")

    if data.get("combat", {}).get("active") or is_combat_action(action):
        return process_combat_action(data, context, action)

    stat_key = choose_stat(action)
    stat_value = character["special"][stat_key]
    difficulty = compute_difficulty(stat_value, action)
    roll = roll_d6()
    success = roll >= difficulty

    summary = _context_summary(context, data)
    special = character["special"]
    items = ", ".join(character.get("items", [])) or "ничего"
    capacity = inventory_capacity(character)
    prompt = USER_PROMPT_TEMPLATE.format(
        name=character["name"],
        faction=character["faction"],
        gender=character.get("gender") or "не указан",
        strength=special["strength"],
        perception=special["perception"],
        endurance=special["endurance"],
        charisma=special["charisma"],
        intelligence=special["intelligence"],
        agility=special["agility"],
        luck=special["luck"],
        health=character["health"],
        wealth=character["wealth"],
        weapon=character.get("weapon") or "нож",
        armor=character.get("armor") or "без брони",
        items=items,
        capacity=capacity,
        status=", ".join(character.get("status", [])) or "нет",
        location=character.get("location", "дорога"),
        day=data.get("world", {}).get("day", 1),
        season=data.get("world", {}).get("season", "весна"),
        action=action,
        stat_name=STAT_LABELS[stat_key],
        stat_value=stat_value,
        difficulty=difficulty,
        roll=roll,
        success="да" if success else "нет",
        summary=summary,
        memory=memory,
    )

    messages = _trim_context(context)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    messages.append({"role": "user", "content": prompt})

    narrative = None
    options: List[str] = []
    effects: Dict[str, Any] = {}
    verdict = "OK"
    reason = ""

    data_json = _call_llm_json(messages, _llm_models(data)) or {}
    verdict = data_json.get("verdict", "OK")
    if verdict == "REJECT":
        reason = data_json.get("reason", "Действие не подходит для сеттинга.")
        options = data_json.get("options") or []
    else:
        narrative = data_json.get("narrative")
        options = data_json.get("options") or []
        effects = data_json.get("effects") or {}
    memory_out = data_json.get("memory")

    if verdict == "REJECT":
        fallback_options = options or _default_options()
        data["last_options"] = fallback_options[:MAX_OPTIONS]
        return _format_reply(reason, fallback_options, None), context, False

    if verdict != "REJECT":
        if not _is_valid_narrative(narrative, options, action, location):
            narrative, options = _fallback_scene(action, success, location)
            effects = {}
            memory_out = None
        if not narrative:
            narrative = _fallback_narrative(action, success)
            memory_out = None

    effects = _normalize_effects(effects)
    special_effects = {
        key: effects[key]
        for key in [
            "strength",
            "perception",
            "endurance",
            "charisma",
            "intelligence",
            "agility",
            "luck",
        ]
        if effects.get(key, 0) != 0
    }
    apply_effects(character["special"], special_effects, min_value=1)

    if effects.get("health"):
        character["health"] = clamp_stat(
            character["health"] + effects["health"], min_value=0
        )
    if effects.get("wealth"):
        character["wealth"] = clamp_stat(
            character["wealth"] + effects["wealth"], min_value=0
        )

    inventory_note = None
    capacity = inventory_capacity(character)
    for item in effects["add_items"]:
        if item not in character["items"]:
            if len(character["items"]) < capacity:
                character["items"].append(item)
            else:
                inventory_note = "Снаряжение переполнено — лишние вещи некуда сложить."
    for item in effects["remove_items"]:
        if item in character["items"]:
            character["items"].remove(item)

    if len(character["items"]) > capacity:
        overflow = character["items"][capacity:]
        character["items"] = character["items"][:capacity]
        dropped = ", ".join(overflow)
        inventory_note = f"Пришлось бросить часть вещей: {dropped}."

    affliction_note, died = apply_affliction(character)

    game_over = False
    if character["health"] <= 0:
        died = True

    if died:
        game_over = True

    if not options:
        options = _default_options()

    _update_scene_memory(
        data,
        memory=memory_out,
        action=action,
        narrative=narrative,
        enemy_name=None,
    )

    data["last_options"] = options[:MAX_OPTIONS]

    reply_text = _format_reply(narrative, options, {
        "stat_key": stat_key,
        "roll": roll,
        "difficulty": difficulty,
        "success": success,
        "affliction": affliction_note,
        "inventory_note": inventory_note,
    })

    # Update context
    context.append({"role": "user", "content": action})
    context.append({"role": "assistant", "content": narrative})
    context = _trim_context(context)

    return reply_text, context, game_over


def _format_reply(narrative: str, options: List[str], check: Optional[Dict[str, Any]]) -> str:
    lines = []
    if check:
        stat_label = STAT_LABELS.get(check["stat_key"], check["stat_key"])
        outcome = "успех" if check["success"] else "провал"
        lines.append(
            f"Проверка: {stat_label} d6={check['roll']} против сложности {check['difficulty']} — {outcome}."
        )
    lines.append(narrative)
    if check and check.get("affliction"):
        lines.append(check["affliction"])
    if check and check.get("inventory_note"):
        lines.append(check["inventory_note"])

    if options:
        lines.append("\nВозможные действия:")
        for i, opt in enumerate(options[:MAX_OPTIONS], start=1):
            lines.append(f"{i}. {opt}")

    return "\n".join(lines)
