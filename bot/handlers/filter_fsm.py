import sys
from pathlib import Path
import logging
import re
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aiogram import Router, F, Bot  # type: ignore
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton  # type: ignore
from aiogram.fsm.context import FSMContext  # type: ignore
from aiogram.fsm.state import State, StatesGroup  # type: ignore
from aiogram.filters import Command  # type: ignore

from config.settings import settings
from database.queries import create_user_filter, get_user_notification_settings, get_user_filters
from bot.locales.texts import t, get_option_label, TOGGLE_OPTIONS

logger = logging.getLogger(__name__)

router = Router()


class FilterCreationStates(StatesGroup):
    waiting_for_make = State()
    dashboard = State()
    waiting_for_input = State()


def get_topic_link(group_chat_id: Any, topic_id: int) -> str:
    """Generate accessible Telegram URL to the forum topic."""
    chat_str = str(group_chat_id).strip()
    if chat_str.startswith("@"):
        username = chat_str.lstrip("@")
        return f"https://t.me/{username}/{topic_id}"
    
    clean_id = chat_str
    if clean_id.startswith("-100"):
        clean_id = clean_id[4:]
    elif clean_id.startswith("-"):
        clean_id = clean_id[1:]
    return f"https://t.me/c/{clean_id}/{topic_id}"


def build_dashboard_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build the single-message interactive dashboard keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text=t("btn_model", lang), callback_data="dash_menu_model"),
            InlineKeyboardButton(text=t("btn_year", lang), callback_data="dash_menu_year")
        ],
        [
            InlineKeyboardButton(text=t("btn_mileage", lang), callback_data="dash_menu_mileage"),
            InlineKeyboardButton(text=t("btn_price", lang), callback_data="dash_menu_price")
        ],
        [
            InlineKeyboardButton(text=t("btn_fuel", lang), callback_data="dash_menu_fuel"),
            InlineKeyboardButton(text=t("btn_condition", lang), callback_data="dash_menu_condition")
        ],
        [
            InlineKeyboardButton(text=t("btn_transmission", lang), callback_data="dash_menu_transmission"),
            InlineKeyboardButton(text=t("btn_body_type", lang), callback_data="dash_menu_body_type")
        ],
        [
            InlineKeyboardButton(text=t("btn_country", lang), callback_data="dash_menu_country")
        ],
        [
            InlineKeyboardButton(text=t("btn_submit_topic", lang), callback_data="dash_submit_topic")
        ],
        [
            InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="dash_cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


POPULAR_MAKES = [
    "BMW", "Mercedes-Benz", "Audi", "Volkswagen",
    "Toyota", "Ford", "Skoda", "Volvo",
    "Renault", "Peugeot", "Hyundai", "Kia",
    "Opel", "Seat", "Porsche", "Mazda",
    "Nissan", "Honda"
]

POPULAR_MODELS: Dict[str, List[str]] = {
    "BMW": [
        "3 Series", "5 Series", "1 Series", "X5",
        "X3", "X1", "7 Series", "4 Series",
        "X6", "2 Series", "X4", "6 Series"
    ],
    "MERCEDES-BENZ": [
        "C-Class", "E-Class", "A-Class", "S-Class",
        "GLC", "GLE", "CLA", "B-Class",
        "GLA", "CLS", "GLS", "Vito"
    ],
    "AUDI": [
        "A4", "A6", "A3", "Q5",
        "Q7", "A5", "Q3", "A1",
        "Q8", "A7", "A8", "TT"
    ],
    "VOLKSWAGEN": [
        "Golf", "Passat", "Tiguan", "Polo",
        "Touran", "Arteon", "Touareg", "T-Roc",
        "Caddy", "T-Cross", "Sharan", "Scirocco"
    ],
    "TOYOTA": [
        "Corolla", "RAV4", "Yaris", "Camry",
        "C-HR", "Auris", "Avensis", "Land Cruiser",
        "Prius", "Aygo", "Hilux", "Supra"
    ],
    "SKODA": [
        "Octavia", "Superb", "Fabia", "Kodiaq",
        "Karoq", "Kamiq", "Scala", "Rapid",
        "Yeti", "Citigo", "Roomster", "Enyaq"
    ],
    "FORD": [
        "Focus", "Mondeo", "Fiesta", "Kuga",
        "Puma", "C-Max", "S-Max", "Mustang",
        "Transit", "Galaxy", "EcoSport", "Ranger"
    ],
    "VOLVO": [
        "XC60", "XC90", "V60", "V90",
        "XC40", "V40", "S60", "S90",
        "V70", "S80", "XC70", "C30"
    ],
    "RENAULT": [
        "Megane", "Clio", "Scenic", "Kadjar",
        "Captur", "Talisman", "Espace", "Koleos"
    ],
    "PEUGEOT": [
        "308", "508", "3008", "208",
        "5008", "2008", "407", "207"
    ],
    "HYUNDAI": [
        "Tucson", "i30", "Santa Fe", "i20",
        "Kona", "Ioniq", "i40", "ix35"
    ],
    "KIA": [
        "Sportage", "Ceed", "Sorento", "Rio",
        "Stonic", "Niro", "Optima", "Picanto"
    ],
    "OPEL": [
        "Astra", "Insignia", "Corsa", "Grandland",
        "Mokka", "Zafira", "Crossland", "Meriva"
    ],
    "SEAT": [
        "Leon", "Ibiza", "Ateca", "Tarraco",
        "Arona", "Alhambra", "Toledo", "Altea"
    ],
    "PORSCHE": [
        "Cayenne", "Macan", "Panamera", "911",
        "Taycan", "Boxster", "Cayman"
    ],
    "MAZDA": [
        "Mazda 6", "Mazda 3", "CX-5", "CX-30",
        "CX-3", "MX-5", "Mazda 2", "CX-60"
    ],
    "NISSAN": [
        "Qashqai", "X-Trail", "Juke", "Micra",
        "Leaf", "Navara", "Note", "370Z"
    ],
    "HONDA": [
        "Civic", "CR-V", "Accord", "HR-V",
        "Jazz", "Insight", "FR-V", "Civic Type R"
    ]
}


_DYNAMIC_MAKES: Optional[List[str]] = None
_DYNAMIC_MODELS: Dict[str, List[str]] = {}


def set_cached_makes_and_models(makes: List[str], models_map: Optional[Dict[str, List[str]]] = None):
    """Update dynamic makes and models in memory cache."""
    global _DYNAMIC_MAKES, _DYNAMIC_MODELS
    _DYNAMIC_MAKES = list(makes)
    if models_map is not None:
        _DYNAMIC_MODELS = dict(models_map)


def get_current_makes() -> List[str]:
    """Retrieve active list of car makes, prioritizing database values."""
    if _DYNAMIC_MAKES is not None and len(_DYNAMIC_MAKES) > 0:
        return _DYNAMIC_MAKES
    return POPULAR_MAKES


def get_models_for_make(make: str) -> List[str]:
    """Retrieve predefined or custom models for a make (case-insensitive & hyphen-tolerant)."""
    if not make:
        return []
    clean_key = make.strip().upper().replace(" ", "").replace("-", "")
    
    # Check dynamic cache first
    for k, models in _DYNAMIC_MODELS.items():
        if k.replace(" ", "").replace("-", "").upper() == clean_key:
            return models

    # Check fallback hardcoded
    for k, models in POPULAR_MODELS.items():
        if k.replace(" ", "").replace("-", "").upper() == clean_key:
            return models
    return []


def build_make_selection_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build grid of popular car makes plus custom manual input and cancel."""
    buttons = []
    row = []
    for make in get_current_makes():
        row.append(InlineKeyboardButton(text=make, callback_data=f"make_pick_{make}"))
        if len(row) >= 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text=t("btn_other_make", lang), callback_data="make_custom_type")
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="dash_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_model_submenu_keyboard(make: str, current_model: Any, lang: str) -> InlineKeyboardMarkup:
    """Build grid of popular models for selected make with checkmark and custom options."""
    models = get_models_for_make(make)
    buttons = []

    # Any / All models button
    is_all = (current_model is None or str(current_model) == "" or str(current_model).lower() in ("none", "all"))
    all_label = f"✅ {t('btn_all_models', lang)}" if is_all else t("btn_all_models", lang)
    buttons.append([InlineKeyboardButton(text=all_label, callback_data="dash_set_model_all")])

    row = []
    for m in models:
        is_sel = (str(current_model).strip().lower() == m.strip().lower())
        label = f"✅ {m}" if is_sel else m
        row.append(InlineKeyboardButton(text=label, callback_data=f"dash_set_model_{m}"))
        if len(row) >= 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text=t("btn_custom_model", lang), callback_data="dash_param_model")
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_back_to_dashboard", lang), callback_data="dash_back_to_main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



YEAR_CHOICES = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2012, 2010, 2008, 2005, 2000]
PRICE_CHOICES = [2500, 5000, 7500, 10000, 12500, 15000, 20000, 25000, 30000, 40000, 50000, 75000, 100000, 150000]
MILEAGE_CHOICES = [30000, 60000, 100000, 125000, 150000, 180000, 200000, 250000, 300000]


def build_year_min_keyboard(current_min: Any, lang: str) -> InlineKeyboardMarkup:
    """Build Step 1/2 keyboard for Minimum Year."""
    buttons = []
    is_any = (current_min is None or str(current_min) == "" or str(current_min).lower() == "none")
    any_text = f"✅ {t('btn_any_min', lang)}" if is_any else t('btn_any_min', lang)
    buttons.append([InlineKeyboardButton(text=any_text, callback_data="dash_step_ymin_any")])

    row = []
    for y in YEAR_CHOICES:
        is_sel = (str(current_min) == str(y))
        btn_text = f"✅ {y}" if is_sel else str(y)
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"dash_step_ymin_{y}"))
        if len(row) >= 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=t("btn_custom_input", lang), callback_data="dash_param_year")])
    buttons.append([InlineKeyboardButton(text=t("btn_back_to_dashboard", lang), callback_data="dash_back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_year_max_keyboard(min_year: Any, current_max: Any, lang: str) -> InlineKeyboardMarkup:
    """Build Step 2/2 keyboard for Maximum Year."""
    buttons = []
    is_any = (current_max is None or str(current_max) == "" or str(current_max).lower() == "none")
    any_text = f"✅ {t('btn_any_max', lang)}" if is_any else t('btn_any_max', lang)
    buttons.append([InlineKeyboardButton(text=any_text, callback_data="dash_step_ymax_any")])

    min_int = int(min_year) if (min_year is not None and str(min_year).isdigit()) else 0
    filtered_years = [y for y in YEAR_CHOICES if y >= min_int]

    row = []
    for y in filtered_years:
        is_sel = (str(current_max) == str(y))
        btn_text = f"✅ {y}" if is_sel else str(y)
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"dash_step_ymax_{y}"))
        if len(row) >= 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=t("btn_custom_input", lang), callback_data="dash_param_year")])
    buttons.append([InlineKeyboardButton(text=t("btn_back_to_dashboard", lang), callback_data="dash_back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_price_min_keyboard(current_min: Any, lang: str) -> InlineKeyboardMarkup:
    """Build Step 1/2 keyboard for Minimum Price (€)."""
    buttons = []
    is_any = (current_min is None or current_min == 0 or str(current_min).lower() == "none")
    any_text = f"✅ {t('btn_any_min', lang)}" if is_any else t('btn_any_min', lang)
    buttons.append([InlineKeyboardButton(text=any_text, callback_data="dash_step_pmin_0")])

    row = []
    for p in PRICE_CHOICES:
        try:
            is_sel = (current_min is not None and float(current_min) == float(p))
        except (ValueError, TypeError):
            is_sel = False
        label = f"{p:,} €".replace(",", " ")
        btn_text = f"✅ {label}" if is_sel else label
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"dash_step_pmin_{p}"))
        if len(row) >= 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=t("btn_custom_input", lang), callback_data="dash_param_price")])
    buttons.append([InlineKeyboardButton(text=t("btn_back_to_dashboard", lang), callback_data="dash_back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_price_max_keyboard(min_price: Any, current_max: Any, lang: str) -> InlineKeyboardMarkup:
    """Build Step 2/2 keyboard for Maximum Price (€)."""
    buttons = []
    is_any = (current_max is None or str(current_max) == "" or str(current_max).lower() == "none")
    any_text = f"✅ {t('btn_any_max', lang)}" if is_any else t('btn_any_max', lang)
    buttons.append([InlineKeyboardButton(text=any_text, callback_data="dash_step_pmax_any")])

    try:
        min_val = float(min_price) if min_price is not None else 0.0
    except (ValueError, TypeError):
        min_val = 0.0
    filtered_prices = [p for p in PRICE_CHOICES if float(p) >= min_val]

    row = []
    for p in filtered_prices:
        try:
            is_sel = (current_max is not None and float(current_max) == float(p))
        except (ValueError, TypeError):
            is_sel = False
        label = f"{p:,} €".replace(",", " ")
        btn_text = f"✅ {label}" if is_sel else label
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"dash_step_pmax_{p}"))
        if len(row) >= 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=t("btn_custom_input", lang), callback_data="dash_param_price")])
    buttons.append([InlineKeyboardButton(text=t("btn_back_to_dashboard", lang), callback_data="dash_back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_mileage_submenu_keyboard(current_max: Any, lang: str) -> InlineKeyboardMarkup:
    """Build keyboard for Maximum Mileage."""
    buttons = []
    is_any = (current_max is None or str(current_max) == "" or str(current_max).lower() == "none")
    any_text = f"✅ {t('btn_any_max', lang)}" if is_any else t('btn_any_max', lang)
    buttons.append([InlineKeyboardButton(text=any_text, callback_data="dash_step_mileage_any")])

    row = []
    for m in MILEAGE_CHOICES:
        try:
            is_sel = (current_max is not None and int(current_max) == int(m))
        except (ValueError, TypeError):
            is_sel = False
        label = f"≤ {m:,} km".replace(",", " ")
        btn_text = f"✅ {label}" if is_sel else label
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"dash_step_mileage_{m}"))
        if len(row) >= 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=t("btn_custom_input", lang), callback_data="dash_param_mileage")])
    buttons.append([InlineKeyboardButton(text=t("btn_back_to_dashboard", lang), callback_data="dash_back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_option_submenu_keyboard(category: str, current_val: str, lang: str) -> InlineKeyboardMarkup:
    """Build grid of selectable option buttons with active checkmark and back button."""
    options = TOGGLE_OPTIONS.get(category, [])
    buttons = []
    row = []

    # 2 columns for fuel/condition/body, 3 columns for country/transmission
    cols = 2 if category in ("fuel", "condition", "body_type") else 3

    for opt in options:
        raw_label = get_option_label(category, opt, lang)
        is_selected = str(opt).lower() == str(current_val).lower()
        btn_text = f"✅ {raw_label}" if is_selected else raw_label

        row.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"dash_set_{category}_{opt}"
        ))

        if len(row) >= cols:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text=t("btn_back_to_dashboard", lang), callback_data="dash_back_to_main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_dashboard_text(data: Dict[str, Any], lang: str) -> str:
    """Format dashboard message string using current state parameters."""
    make = data.get("make", "Unknown")
    model = data.get("model") or t("not_selected", lang)
    
    # Year display
    year_min = data.get("year_min")
    year_max = data.get("year_max")
    if year_min and year_max:
        year_str = f"{year_min} - {year_max}"
    elif year_min:
        year_str = f"≥ {year_min}"
    elif year_max:
        year_str = f"≤ {year_max}"
    else:
        year_str = t("not_selected", lang)

    # Mileage display
    mileage_min = data.get("mileage_min")
    mileage_max = data.get("mileage_max")
    if mileage_min and mileage_max:
        mileage_str = f"{mileage_min:,} - {mileage_max:,} km".replace(",", " ")
    elif mileage_max:
        mileage_str = f"≤ {mileage_max:,} km".replace(",", " ")
    else:
        mileage_str = t("not_selected", lang)

    # Price display
    price_min = data.get("price_min_eur")
    price_max = data.get("price_max_eur")
    if price_min and price_max:
        price_str = f"{price_min:,.0f} € - {price_max:,.0f} €".replace(",", " ")
    elif price_min:
        price_str = f"≥ {price_min:,.0f} €".replace(",", " ")
    elif price_max:
        price_str = f"≤ {price_max:,.0f} €".replace(",", " ")
    else:
        price_str = t("not_selected", lang)

    fuel = get_option_label("fuel", data.get("fuel_type", "all"), lang)
    condition = get_option_label("condition", data.get("condition", "all"), lang)
    transmission = get_option_label("transmission", data.get("transmission", "all"), lang)
    body_type = get_option_label("body_type", data.get("body_type", "all"), lang)
    country = get_option_label("country", data.get("target_country", "ALL"), lang)

    return t(
        "dashboard_header",
        lang,
        make=make,
        model=model,
        year=year_str,
        mileage=mileage_str,
        price=price_str,
        fuel=fuel,
        condition=condition,
        transmission=transmission,
        body_type=body_type,
        country=country
    )


# ==============================================================================
# FSM START & STEP 1: MAKE
# ==============================================================================

@router.message(Command("newfilter"))
@router.callback_query(F.data.in_(["btn_new_search", "btn_new_filter"]))
async def start_filter_creation(event: Message | CallbackQuery, state: FSMContext, lang: str = "en"):
    """Entry point for new filter creation."""
    await state.clear()
    await state.set_state(FilterCreationStates.waiting_for_make)

    prompt_text = t("select_make_title", lang)
    keyboard = build_make_selection_keyboard(lang)
    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await event.message.answer(prompt_text, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(prompt_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(FilterCreationStates.waiting_for_make, F.data.startswith("make_pick_"))
async def handle_make_picked(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Handle click on popular make button to initialize search dashboard."""
    if not callback.data:
        await callback.answer()
        return

    clean_make = callback.data.replace("make_pick_", "").strip()
    initial_data = {
        "make": clean_make,
        "model": None,
        "year_min": None,
        "year_max": None,
        "mileage_min": None,
        "mileage_max": None,
        "price_min_eur": None,
        "price_max_eur": None,
        "fuel_type": "all",
        "condition": "all",
        "transmission": "all",
        "body_type": "all",
        "target_country": "ALL"
    }
    await state.update_data(**initial_data)
    await state.set_state(FilterCreationStates.dashboard)

    dashboard_text = format_dashboard_text(initial_data, lang)
    keyboard = build_dashboard_keyboard(lang)

    if isinstance(callback.message, Message):
        dashboard_msg = await callback.message.edit_text(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
        await state.update_data(
            dashboard_msg_id=dashboard_msg.message_id,
            dashboard_chat_id=dashboard_msg.chat.id
        )
    await callback.answer()


@router.callback_query(FilterCreationStates.waiting_for_make, F.data == "make_custom_type")
async def handle_make_custom_prompt(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Prompt user to type custom make manually."""
    if isinstance(callback.message, Message):
        await callback.message.answer(t("prompt_make", lang), parse_mode="HTML")
    await callback.answer()


@router.message(FilterCreationStates.waiting_for_make)
async def process_make_step(message: Message, state: FSMContext, lang: str = "en"):
    """Receive vehicle make, initialize state, and send interactive dashboard."""
    raw_make = (message.text or "").strip()
    if not raw_make or len(raw_make) < 2:
        await message.answer(t("input_invalid_format", lang), parse_mode="HTML")
        return

    clean_make = raw_make.title()
    initial_data = {
        "make": clean_make,
        "model": None,
        "year_min": None,
        "year_max": None,
        "mileage_min": None,
        "mileage_max": None,
        "price_min_eur": None,
        "price_max_eur": None,
        "fuel_type": "all",
        "condition": "all",
        "transmission": "all",
        "body_type": "all",
        "target_country": "ALL"
    }
    await state.update_data(**initial_data)
    await state.set_state(FilterCreationStates.dashboard)

    dashboard_text = format_dashboard_text(initial_data, lang)
    keyboard = build_dashboard_keyboard(lang)
    
    dashboard_msg = await message.answer(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(
        dashboard_msg_id=dashboard_msg.message_id,
        dashboard_chat_id=dashboard_msg.chat.id
    )


# ==============================================================================
# DASHBOARD OPTION SUBMENUS (FUEL, TRANSMISSION, CONDITION, BODY, COUNTRY)
# ==============================================================================

@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_menu_"))
async def handle_open_option_submenu(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Open dedicated selection submenu with full choices list."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return

    category = callback.data.replace("dash_menu_", "")

    if category == "model":
        await handle_open_model_menu(callback, state, lang)
        return
    elif category == "year":
        await handle_open_year_menu(callback, state, lang)
        return
    elif category == "price":
        await handle_open_price_menu(callback, state, lang)
        return
    elif category == "mileage":
        await handle_open_mileage_menu(callback, state, lang)
        return

    field_map = {
        "fuel": "fuel_type",
        "transmission": "transmission",
        "condition": "condition",
        "body_type": "body_type",
        "country": "target_country"
    }
    if category not in field_map:
        await callback.answer()
        return

    data = await state.get_data()
    db_key = field_map[category]
    default_val = "ALL" if category == "country" else "all"
    current_val = str(data.get(db_key, default_val))

    text = t(f"submenu_{category}", lang)
    keyboard = build_option_submenu_keyboard(category, current_val, lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Submenu edit error: {edit_err}")
async def handle_open_model_menu(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Open dedicated Model selection submenu for current Make."""
    data = await state.get_data()
    make = data.get("make", "")
    models = get_models_for_make(make)
    if not models:
        if isinstance(callback.message, Message):
            prompt_msg = await callback.message.answer(t("prompt_model_input", lang), parse_mode="HTML")
            await state.update_data(current_field="model", prompt_msg_id=prompt_msg.message_id)
            await state.set_state(FilterCreationStates.waiting_for_input)
        await callback.answer()
        return

    text = t("select_model_title", lang, make=make)
    keyboard = build_model_submenu_keyboard(make=make, current_model=data.get("model"), lang=lang)
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Model menu edit note: {edit_err}")
    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_set_model_"))
async def handle_select_model(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Save selected model from submenu and return directly to main dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return

    raw_model = callback.data.replace("dash_set_model_", "").strip()
    chosen_model = None if raw_model.lower() == "all" else raw_model

    await state.update_data(model=chosen_model)

    updated_data = await state.get_data()
    dashboard_text = format_dashboard_text(updated_data, lang)
    keyboard = build_dashboard_keyboard(lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Dashboard return edit note: {edit_err}")

    await callback.answer()


async def handle_open_year_menu(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Step 1/2: Open Minimum Year selection menu."""
    data = await state.get_data()
    text = t("step_year_min_title", lang)
    keyboard = build_year_min_keyboard(current_min=data.get("year_min"), lang=lang)
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Year menu edit note: {edit_err}")
    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_step_ymin_"))
async def handle_select_year_min(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Step 2/2: Save Minimum Year, then open Maximum Year selection menu."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    raw_val = callback.data.replace("dash_step_ymin_", "")
    chosen_min = None if raw_val == "any" else int(raw_val)
    await state.update_data(temp_year_min=chosen_min)

    min_display = str(chosen_min) if chosen_min else t("any_year", lang)
    text = t("step_year_max_title", lang, min_year=min_display)

    data = await state.get_data()
    keyboard = build_year_max_keyboard(min_year=chosen_min, current_max=data.get("year_max"), lang=lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Year max edit note: {edit_err}")
    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_step_ymax_"))
async def handle_select_year_max(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Finalize Year range and return directly to main dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    raw_val = callback.data.replace("dash_step_ymax_", "")
    chosen_max = None if raw_val == "any" else int(raw_val)

    data = await state.get_data()
    chosen_min = data.get("temp_year_min")

    if chosen_min and chosen_max and chosen_min > chosen_max:
        chosen_min, chosen_max = chosen_max, chosen_min

    await state.update_data(
        year_min=chosen_min,
        year_max=chosen_max,
        temp_year_min=None
    )

    updated_data = await state.get_data()
    dashboard_text = format_dashboard_text(updated_data, lang)
    keyboard = build_dashboard_keyboard(lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Dashboard return note: {edit_err}")
    await callback.answer()


async def handle_open_price_menu(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Step 1/2: Open Minimum Price selection menu."""
    data = await state.get_data()
    text = t("step_price_min_title", lang)
    keyboard = build_price_min_keyboard(current_min=data.get("price_min_eur"), lang=lang)
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Price menu edit note: {edit_err}")
    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_step_pmin_"))
async def handle_select_price_min(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Step 2/2: Save Minimum Price, then open Maximum Price selection menu."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    raw_val = callback.data.replace("dash_step_pmin_", "")
    chosen_min = None if raw_val in ("0", "any") else float(raw_val)
    await state.update_data(temp_price_min=chosen_min)

    min_display = f"{chosen_min:,.0f} €".replace(",", " ") if chosen_min else "0 €"
    text = t("step_price_max_title", lang, min_price=min_display)

    data = await state.get_data()
    keyboard = build_price_max_keyboard(min_price=chosen_min, current_max=data.get("price_max_eur"), lang=lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Price max edit note: {edit_err}")
    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_step_pmax_"))
async def handle_select_price_max(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Finalize Price range and return directly to main dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    raw_val = callback.data.replace("dash_step_pmax_", "")
    chosen_max = None if raw_val == "any" else float(raw_val)

    data = await state.get_data()
    chosen_min = data.get("temp_price_min")

    if chosen_min and chosen_max and chosen_min > chosen_max:
        chosen_min, chosen_max = chosen_max, chosen_min

    await state.update_data(
        price_min_eur=chosen_min,
        price_max_eur=chosen_max,
        temp_price_min=None
    )

    updated_data = await state.get_data()
    dashboard_text = format_dashboard_text(updated_data, lang)
    keyboard = build_dashboard_keyboard(lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Dashboard return note: {edit_err}")
    await callback.answer()


async def handle_open_mileage_menu(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Open Maximum Mileage selection menu."""
    data = await state.get_data()
    text = t("submenu_mileage", lang)
    keyboard = build_mileage_submenu_keyboard(current_max=data.get("mileage_max"), lang=lang)
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Mileage menu edit note: {edit_err}")
    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_step_mileage_"))
async def handle_select_mileage(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Save selected Mileage and return directly to main dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    raw_val = callback.data.replace("dash_step_mileage_", "")
    chosen_max = None if raw_val == "any" else int(raw_val)

    await state.update_data(mileage_max=chosen_max)

    updated_data = await state.get_data()
    dashboard_text = format_dashboard_text(updated_data, lang)
    keyboard = build_dashboard_keyboard(lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Dashboard return note: {edit_err}")
    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_set_"))
async def handle_select_submenu_option(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Save selected option from submenu and return directly to main dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return

    payload = callback.data.replace("dash_set_", "")
    parts = payload.split("_", 1)
    if len(parts) != 2:
        await callback.answer()
        return

    category, chosen_val = parts[0], parts[1]
    field_map = {
        "fuel": "fuel_type",
        "transmission": "transmission",
        "condition": "condition",
        "body_type": "body_type",
        "country": "target_country"
    }
    if category in field_map:
        db_key = field_map[category]
        await state.update_data({db_key: chosen_val})

    updated_data = await state.get_data()
    dashboard_text = format_dashboard_text(updated_data, lang)
    keyboard = build_dashboard_keyboard(lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Dashboard return edit note: {edit_err}")

    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data == "dash_back_to_main")
async def handle_back_to_dashboard(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Return to dashboard view from submenu without changing value."""
    if not callback.from_user:
        await callback.answer()
        return

    await state.update_data(temp_year_min=None, temp_price_min=None)

    data = await state.get_data()
    dashboard_text = format_dashboard_text(data, lang)
    keyboard = build_dashboard_keyboard(lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as edit_err:
            logger.debug(f"Dashboard back edit note: {edit_err}")

    await callback.answer()


@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_toggle_"))
async def handle_toggle_parameter(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Fallback handler for cycling toggle parameters."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    action = callback.data.replace("dash_toggle_", "")
    data = await state.get_data()

    field_map = {
        "fuel": "fuel_type",
        "transmission": "transmission",
        "condition": "condition",
        "body_type": "body_type",
        "country": "target_country"
    }

    if action in field_map:
        db_key = field_map[action]
        options = TOGGLE_OPTIONS.get(action, [])
        current_val = data.get(db_key, options[0] if options else "all")

        try:
            curr_idx = options.index(current_val)
            next_idx = (curr_idx + 1) % len(options)
            next_val = options[next_idx]
        except (ValueError, IndexError):
            next_val = options[0] if options else "all"

        await state.update_data({db_key: next_val})
        updated_data = await state.get_data()
        
        dashboard_text = format_dashboard_text(updated_data, lang)
        keyboard = build_dashboard_keyboard(lang)

        if isinstance(callback.message, Message):
            try:
                await callback.message.edit_text(dashboard_text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as edit_err:
                logger.debug(f"Dashboard edit note: {edit_err}")

    await callback.answer()


# ==============================================================================
# DASHBOARD TEXT/NUMERIC PARAMETERS (MODEL, YEAR, MILEAGE, PRICE)
# ==============================================================================

@router.callback_query(FilterCreationStates.dashboard, F.data.startswith("dash_param_"))
async def handle_text_param_click(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Handle click on text/numeric parameter to initiate waiting_for_input."""
    if not callback.data:
        await callback.answer()
        return
    param = callback.data.replace("dash_param_", "")
    prompt_keys = {
        "model": "prompt_model_input",
        "year": "prompt_year_input",
        "mileage": "prompt_mileage_input",
        "price": "prompt_price_input"
    }

    if param in prompt_keys and isinstance(callback.message, Message):
        prompt_text = t(prompt_keys[param], lang)
        prompt_msg = await callback.message.answer(prompt_text, parse_mode="HTML")

        await state.update_data(
            current_field=param,
            prompt_msg_id=prompt_msg.message_id
        )
        await state.set_state(FilterCreationStates.waiting_for_input)

    await callback.answer()


@router.message(FilterCreationStates.waiting_for_input)
async def process_text_param_input(message: Message, state: FSMContext, bot: Bot, lang: str = "en"):
    """Validate user input, delete temporary messages, and update dashboard."""
    data = await state.get_data()
    field = data.get("current_field")
    user_text = (message.text or "").strip()

    updates = {}
    valid = False

    if field == "model":
        if user_text == "-":
            updates["model"] = None
            valid = True
        elif user_text:
            updates["model"] = user_text.upper() if len(user_text) <= 4 else user_text.title()
            valid = True

    elif field == "year":
        if user_text == "-":
            updates["year_min"] = None
            updates["year_max"] = None
            valid = True
        else:
            numbers = [int(n) for n in re.findall(r"\b\d{4}\b", user_text)]
            if len(numbers) == 1:
                updates["year_min"] = numbers[0]
                updates["year_max"] = None
                valid = True
            elif len(numbers) >= 2:
                updates["year_min"] = min(numbers[0], numbers[1])
                updates["year_max"] = max(numbers[0], numbers[1])
                valid = True

    elif field == "mileage":
        if user_text == "-":
            updates["mileage_min"] = None
            updates["mileage_max"] = None
            valid = True
        else:
            clean_str = user_text.replace(" ", "").replace(",", "").replace("km", "")
            numbers = [int(n) for n in re.findall(r"\b\d+\b", clean_str)]
            if len(numbers) == 1:
                updates["mileage_min"] = None
                updates["mileage_max"] = numbers[0]
                valid = True
            elif len(numbers) >= 2:
                updates["mileage_min"] = min(numbers[0], numbers[1])
                updates["mileage_max"] = max(numbers[0], numbers[1])
                valid = True

    elif field == "price":
        if user_text == "-":
            updates["price_min_eur"] = None
            updates["price_max_eur"] = None
            valid = True
        else:
            clean_str = user_text.replace(" ", "").replace(",", "").replace("€", "").replace("eur", "")
            numbers = [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", clean_str)]
            if len(numbers) == 1:
                updates["price_min_eur"] = None
                updates["price_max_eur"] = numbers[0]
                valid = True
            elif len(numbers) >= 2:
                updates["price_min_eur"] = min(numbers[0], numbers[1])
                updates["price_max_eur"] = max(numbers[0], numbers[1])
                valid = True

    if not valid:
        await message.answer(t("input_invalid_format", lang), parse_mode="HTML")
        return

    # Delete prompt message and user input message
    prompt_msg_id = data.get("prompt_msg_id")
    if prompt_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
        except Exception:
            pass
    try:
        await message.delete()
    except Exception:
        pass

    # Update state and return to dashboard state
    await state.update_data(**updates)
    await state.set_state(FilterCreationStates.dashboard)

    # Edit main dashboard message
    updated_data = await state.get_data()
    dashboard_msg_id = data.get("dashboard_msg_id")
    dashboard_chat_id = data.get("dashboard_chat_id") or message.chat.id

    if dashboard_msg_id:
        dash_text = format_dashboard_text(updated_data, lang)
        keyboard = build_dashboard_keyboard(lang)
        try:
            await bot.edit_message_text(
                chat_id=dashboard_chat_id,
                message_id=dashboard_msg_id,
                text=dash_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as edit_err:
            logger.debug(f"Dashboard refresh error: {edit_err}")


# ==============================================================================
# CANCEL BUTTON
# ==============================================================================

@router.callback_query(F.data == "dash_cancel")
@router.message(Command("cancel"))
async def cancel_dashboard(event: Message | CallbackQuery, state: FSMContext, lang: str = "en"):
    """Cancel search filter creation."""
    await state.clear()
    cancel_text = t("filter_cancelled", lang)
    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await event.message.edit_text(cancel_text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(cancel_text, parse_mode="HTML")


# ==============================================================================
# SUBMIT & CREATE TOPIC + PINNED MESSAGE
# ==============================================================================

@router.callback_query(FilterCreationStates.dashboard, F.data == "dash_submit_topic")
async def submit_and_create_topic(callback: CallbackQuery, state: FSMContext, bot: Bot, lang: str = "en"):
    """Finalize filter: create Telegram forum topic, post & pin summary card, save to DB."""
    if not callback.from_user:
        await callback.answer()
        return

    data = await state.get_data()
    make = data.get("make")
    if not make:
        await callback.answer(t("input_invalid_format", lang), show_alert=True)
        return

    model = data.get("model")
    year_min = data.get("year_min")
    year_max = data.get("year_max")
    mileage_min = data.get("mileage_min")
    mileage_max = data.get("mileage_max")
    price_min = data.get("price_min_eur")
    price_max = data.get("price_max_eur")
    fuel_type = data.get("fuel_type", "all")
    condition = data.get("condition", "all")
    transmission = data.get("transmission", "all")
    body_type = data.get("body_type", "all")
    target_country = data.get("target_country", "ALL")

    # 1. Build attractive Topic Title
    parts = []
    if model:
        parts.append(f"{make} {model}")
    else:
        parts.append(make)

    spec_parts = []
    if year_min and year_max:
        spec_parts.append(f"{year_min}-{year_max}")
    elif year_min:
        spec_parts.append(f">{year_min}")
    elif year_max:
        spec_parts.append(f"<{year_max}")

    if price_max:
        spec_parts.append(f"<{price_max:,.0f}€".replace(",", ""))

    if spec_parts:
        topic_name = f"🚗 {' '.join(parts)} ({', '.join(spec_parts)})"
    else:
        topic_name = f"🚗 {' '.join(parts)}"

    if len(topic_name) > 120:
        topic_name = topic_name[:117] + "..."

    user_id = callback.from_user.id
    notify_settings = await get_user_notification_settings(user_id)
    existing_filters = await get_user_filters(user_id)

    target_chat_id = user_id
    topic_id = 0
    pinned_message_id = None
    created_in_group = False
    group_title = notify_settings.get("connected_group_title") or "Şəxsi Qrup"

    year_str = f"{year_min} - {year_max}" if (year_min and year_max) else (str(year_min) if year_min else (str(year_max) if year_max else "-"))
    mileage_str = f"Max {mileage_max:,} km".replace(",", " ") if mileage_max else "-"
    price_str = f"{price_min:,.0f} € - {price_max:,.0f} €".replace(",", " ") if (price_min and price_max) else (f"≤ {price_max:,.0f} €" if price_max else "-")

    fuel_lbl = get_option_label("fuel", fuel_type, lang)
    trans_lbl = get_option_label("transmission", transmission, lang)
    cond_lbl = get_option_label("condition", condition, lang)
    country_lbl = get_option_label("country", target_country, lang)

    # 1. Attempt to create forum topic in personal group if in Group mode
    if notify_settings.get("notification_target") == "group" and notify_settings.get("connected_group_id"):
        group_id = notify_settings["connected_group_id"]
        try:
            topic = await bot.create_forum_topic(chat_id=group_id, name=topic_name)
            topic_id = topic.message_thread_id
            target_chat_id = group_id
            created_in_group = True

            pinned_card = t(
                "pinned_summary_card", lang,
                make=make,
                model=model or t("not_selected", lang),
                year=year_str,
                mileage=mileage_str,
                price=price_str,
                fuel=fuel_lbl,
                transmission=trans_lbl,
                condition=cond_lbl,
                body_type=get_option_label("body_type", body_type, lang),
                country=country_lbl
            )
            try:
                pmsg = await bot.send_message(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    text=pinned_card,
                    parse_mode="HTML"
                )
                pinned_message_id = pmsg.message_id
                await bot.pin_chat_message(chat_id=group_id, message_id=pinned_message_id)
            except Exception:
                pass
        except Exception as group_err:
            logger.warning(f"Could not create forum topic in personal group {group_id}: {group_err}. Falling back to DM.")
            topic_id = 0
            target_chat_id = user_id
            created_in_group = False

    # 2. Save filter to database
    filter_id = await create_user_filter(
        user_id=user_id,
        make=make,
        model=model,
        year_min=year_min,
        year_max=year_max,
        mileage_min=mileage_min,
        mileage_max=mileage_max,
        price_min_eur=price_min,
        price_max_eur=price_max,
        fuel_type=fuel_type,
        condition=condition,
        transmission=transmission,
        body_type=body_type,
        target_country=target_country,
        target_chat_id=target_chat_id,
        topic_id=topic_id,
        pinned_message_id=pinned_message_id,
        is_active=1
    )
    logger.info(f"Created search filter #{filter_id} for user {user_id} (target_chat: {target_chat_id}, topic: {topic_id})")

    # 3. Format Confirmation & Action Keyboard
    buttons = []
    if created_in_group and topic_id > 0:
        topic_url = get_topic_link(target_chat_id, topic_id)
        buttons.append([
            InlineKeyboardButton(text="🔗 Mövzuya Keç (Qrup)", url=topic_url)
        ])
        success_msg = (
            f"✅ <b>Axtarışınız uğurla aktivləşdirildi!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚙 <b>{make} {model or ''}</b>\n"
            f"📅 <b>İl:</b> {year_str}\n"
            f"🧭 <b>Yürüş:</b> {mileage_str}\n"
            f"💰 <b>Büdcə:</b> {price_str}\n"
            f"⛽ <b>Yanacaq:</b> {fuel_lbl}\n"
            f"⚙️ <b>Sürətlər Qutusu:</b> {trans_lbl}\n"
            f"🛠 <b>Vəziyyət:</b> {cond_lbl}\n"
            f"🌍 <b>Bazar:</b> {country_lbl}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>Şəxsi Qrupunuzda Mövzu Açıldı:</b> Bu filtrə uyğun bütün elanlar <b>{group_title}</b> qrupunda xüsusi <b>{topic_name}</b> mövzusuna göndəriləcək.\n\n"
            f"<i>Nə etmək istəyirsiniz?</i>"
        )
    else:
        success_msg = (
            f"✅ <b>Axtarışınız uğurla aktivləşdirildi!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚙 <b>{make} {model or ''}</b>\n"
            f"📅 <b>İl:</b> {year_str}\n"
            f"🧭 <b>Yürüş:</b> {mileage_str}\n"
            f"💰 <b>Büdcə:</b> {price_str}\n"
            f"⛽ <b>Yanacaq:</b> {fuel_lbl}\n"
            f"⚙️ <b>Sürətlər Qutusu:</b> {trans_lbl}\n"
            f"🛠 <b>Vəziyyət:</b> {cond_lbl}\n"
            f"🌍 <b>Bazar:</b> {country_lbl}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 <b>100% Şəxsi Çat Qorunması:</b> Bu filtrə uyğun tapılan bütün yeni elanlar tam məxfi olaraq yalnız və yalnız sizin bu şəxsi çatınıza göndəriləcəkdir."
        )

        # Progressive disclosure tip if user has 2 or more filters and is in DM mode
        if len(existing_filters) >= 1 and notify_settings.get("notification_target") == "dm":
            success_msg += (
                f"\n\n💡 <b>İpucu:</b> Birdən çox avtomobil axtarırsınızsa, elanların qarışmaması üçün öz şəxsi qrupunuzu qoşub hər maşını ayrı Mövzuda (Topic-də) izləyə bilərsiniz."
            )
            buttons.append([
                InlineKeyboardButton(text="👥 Şəxsi Qrupu Qoş (Topics Pro)", callback_data="btn_connect_group_info")
            ])

        success_msg += "\n\n<i>Nə etmək istəyirsiniz?</i>"

    buttons.append([
        InlineKeyboardButton(text="📥 Mövcud Elanları İndi Gətir", callback_data=f"filter_fetch_now_{filter_id}")
    ])
    buttons.append([
        InlineKeyboardButton(text="⚙️ Filtr Tənzimləmələri & Limit", callback_data=f"filter_details_{filter_id}"),
        InlineKeyboardButton(text="📋 Bütün Filtrlərim", callback_data="btn_my_topics")
    ])
    buttons.append([
        InlineKeyboardButton(text="➕ Yeni Axtarış Əlavə Et", callback_data="btn_new_search"),
        InlineKeyboardButton(text="🏠 Əsas Menyu", callback_data="btn_main_menu")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            success_msg,
            reply_markup=kb,
            parse_mode="HTML"
        )

    await state.clear()
    await callback.answer()
