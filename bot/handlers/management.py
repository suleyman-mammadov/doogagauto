import sys
from pathlib import Path
import logging
from typing import Optional, List, Dict, Any, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aiogram import Router, F, Bot  # type: ignore
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated  # type: ignore
from aiogram.filters import Command  # type: ignore
from aiogram.fsm.context import FSMContext  # type: ignore
from aiogram.fsm.state import State, StatesGroup  # type: ignore

from config.settings import settings
from database.queries import (
    get_user_language,
    set_user_language,
    get_user_hot_deals_status,
    toggle_user_hot_deals,
    get_user_hot_deals_settings,
    update_user_hot_deals_settings,
    get_user_filters,
    get_filter_by_id,
    toggle_filter_status,
    delete_filter,
    get_database_stats,
    update_user_filter,
    increment_filter_alert_count,
    search_seen_listings_for_filter,
    get_top_arbitrage_deals,
    get_user_notification_settings,
    set_user_notification_target,
    link_user_group,
    unlink_user_group
)
from bot.locales.texts import t, LANGUAGES, get_option_label
from bot.middlewares.i18n import set_cached_user_language

logger = logging.getLogger(__name__)

router = Router()


class FilterEditState(StatesGroup):
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_price = State()
    waiting_for_mileage = State()


DEAL_TYPE_LABELS: Dict[str, str] = {
    "all": "💎 All Deals",
    "top_profit": "🚀 Top Margin (>25%)",
    "new_cars": "⚡ New Models (2018+)",
    "low_mileage": "🛣️ Low Mileage (≤100k km)",
    "low_mileage_cheap": "🌟 Low Mileage + Cheap"
}


def get_deal_type_label(deal_type: str, lang: str = "en") -> str:
    labels = {
        "all": {"en": "💎 All Deals", "pl": "💎 Wszystkie Okazje", "ru": "💎 Все Сделки"},
        "top_profit": {"en": "🚀 Top Margin (>25%)", "pl": "🚀 Najwyższa Marża (>25%)", "ru": "🚀 Макс. Маржа (>25%)"},
        "new_cars": {"en": "⚡ New Models (2018+)", "pl": "⚡ Nowsze Modele (2018+)", "ru": "⚡ Новые Модели (2018+)"},
        "low_mileage": {"en": "🛣️ Low Mileage (≤100k km)", "pl": "🛣️ Niski Przebieg (≤100k km)", "ru": "🛣️ Низкий Пробег (≤100k км)"},
        "low_mileage_cheap": {"en": "🌟 Low Mileage + Cheap", "pl": "🌟 Niski Przebieg + Tani", "ru": "🌟 Низкий Пробег + Недорогой"}
    }
    sub = labels.get(deal_type, {})
    return sub.get(lang) or sub.get("en") or deal_type


def format_limit_label(limit: int, lang: str = "en") -> str:
    if not limit or limit <= 0:
        return t("limit_unlimited", lang)
    return t("limit_per_day", lang, limit=limit)


def format_age_label(age_hours: int, lang: str = "en") -> str:
    if not age_hours or age_hours <= 0:
        return t("age_realtime", lang)
    elif age_hours == 1:
        return t("age_1h", lang)
    elif age_hours == 24:
        return t("age_24h", lang)
    elif age_hours == 168:
        return t("age_7d", lang)
    elif age_hours == 720:
        return t("age_30d", lang)
    return f"🌐 {age_hours}h"


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Build language selection inline buttons with English, Polish, Russian."""
    buttons = [
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton(text="🇵🇱 Polski", callback_data="set_lang_pl")
        ],
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_keyboard(lang: str, hot_deals_enabled: bool = True, notify_settings: Optional[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
    """Build settings keyboard with language selection, notification destination, Hot Deals toggle, detailed preferences, and main menu."""
    hd_btn_text = t("btn_hot_deals_on", lang) if hot_deals_enabled else t("btn_hot_deals_off", lang)
    buttons = [
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton(text="🇵🇱 Polski", callback_data="set_lang_pl"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")
        ]
    ]

    target = notify_settings.get("notification_target", "dm") if notify_settings else "dm"
    group_id = notify_settings.get("connected_group_id") if notify_settings else None
    group_title = notify_settings.get("connected_group_title") if notify_settings else None

    if target == "dm":
        if group_id:
            buttons.append([
                InlineKeyboardButton(text=f"{t('btn_switch_to_group', lang)} ({group_title or 'Topics'})", callback_data="btn_switch_to_group")
            ])
            buttons.append([
                InlineKeyboardButton(text=t("btn_disconnect_group", lang), callback_data="btn_connect_group_info")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text=t("btn_connect_group_pro", lang), callback_data="btn_connect_group_info")
            ])
    else:
        buttons.append([
            InlineKeyboardButton(text=t("btn_switch_to_dm", lang), callback_data="btn_switch_to_dm")
        ])
        buttons.append([
            InlineKeyboardButton(text=t("btn_disconnect_group", lang), callback_data="btn_connect_group_info")
        ])

    buttons.append([
        InlineKeyboardButton(text=hd_btn_text, callback_data="toggle_hot_deals")
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_hot_deals_settings", lang), callback_data="btn_hot_deals_menu")
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="btn_main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_interval_label(interval_hours: int, lang: str) -> str:
    """Format interval hours to localized text."""
    if interval_hours == 0:
        return t("interval_realtime", lang)
    elif interval_hours == 1:
        return t("interval_1h", lang)
    elif interval_hours == 3:
        return t("interval_3h", lang)
    elif interval_hours == 6:
        return t("interval_6h", lang)
    elif interval_hours == 24:
        return t("interval_24h", lang)
    return f"{interval_hours}h"


def build_hot_deals_dashboard_text(hd: Dict[str, Any], lang: str) -> str:
    """Format Hot Deals preferences dashboard header."""
    status_label = t("status_active", lang) if hd.get("enabled", True) else t("status_disabled", lang)
    min_profit_str = f"{int(hd.get('min_profit_eur', 1500)):,}".replace(",", " ")
    min_profit_pct = f"{int(hd.get('min_profit_percent', 15))}%"
    deal_type_str = get_deal_type_label(hd.get("deal_type", "all"), lang)
    min_year_str = f"{hd.get('min_year', 2012)}+" if hd.get("min_year", 0) > 0 else t("any_year", lang)
    max_price_str = f"≤ {int(hd.get('max_price_eur', 0)):,} €".replace(",", " ") if hd.get("max_price_eur", 0) > 0 else t("unlimited_price", lang)
    max_mileage_str = f"≤ {int(hd.get('max_mileage', 0)):,} km".replace(",", " ") if hd.get("max_mileage", 0) > 0 else t("unlimited_price", lang)
    interval_str = format_interval_label(hd.get("interval_hours", 0), lang)

    return t(
        "hot_deals_dashboard_title",
        lang,
        status=status_label,
        min_profit=min_profit_str,
        min_pct=min_profit_pct,
        deal_type=deal_type_str,
        min_year=min_year_str,
        max_price=max_price_str,
        max_mileage=max_mileage_str,
        interval=interval_str
    )


def build_hot_deals_dashboard_keyboard(hd: Dict[str, Any], lang: str) -> InlineKeyboardMarkup:
    """Build Hot Deals preferences dashboard buttons."""
    status_text = f"🔘 Status: {t('status_active', lang)}" if hd.get("enabled", True) else f"🔘 Status: {t('status_disabled', lang)}"
    min_profit_str = f"≥ {int(hd.get('min_profit_eur', 1500))} €"
    min_pct_str = f"≥ {int(hd.get('min_profit_percent', 15))}%"
    min_year_str = f"{hd.get('min_year', 2012)}+" if hd.get("min_year", 0) > 0 else t("any_year", lang)
    max_price_str = f"≤ {int(hd.get('max_price_eur', 0))} €" if hd.get("max_price_eur", 0) > 0 else t("unlimited_price", lang)
    deal_type_label = get_deal_type_label(hd.get("deal_type", "all"), lang)
    interval_str = format_interval_label(hd.get("interval_hours", 0), lang)
    mileage_str = f"≤ {int(hd.get('max_mileage', 0)):,} km".replace(",", " ") if hd.get("max_mileage", 0) > 0 else t("unlimited_price", lang)

    buttons = [
        [
            InlineKeyboardButton(text=status_text, callback_data="hd_toggle_status")
        ],
        [
            InlineKeyboardButton(text=t("btn_hd_profit", lang, v=min_profit_str), callback_data="hd_param_profit"),
            InlineKeyboardButton(text=t("btn_hd_pct", lang, v=min_pct_str), callback_data="hd_param_pct")
        ],
        [
            InlineKeyboardButton(text=t("btn_hd_focus", lang, v=deal_type_label), callback_data="hd_param_type")
        ],
        [
            InlineKeyboardButton(text=t("btn_hd_year", lang, v=min_year_str), callback_data="hd_param_year"),
            InlineKeyboardButton(text=t("btn_hd_price", lang, v=max_price_str), callback_data="hd_param_price")
        ],
        [
            InlineKeyboardButton(text=t("btn_hd_mileage", lang, v=mileage_str), callback_data="hd_param_mileage"),
            InlineKeyboardButton(text=t("btn_hd_interval", lang, v=interval_str), callback_data="hd_param_interval")
        ],
        [
            InlineKeyboardButton(text=t("btn_hot_deals_hub", lang), callback_data="btn_hot_deals_hub"),
            InlineKeyboardButton(text=t("btn_back_to_settings", lang), callback_data="btn_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build localized main menu buttons."""
    buttons = [
        [
            InlineKeyboardButton(text=t("btn_new_search", lang), callback_data="btn_new_search"),
            InlineKeyboardButton(text=t("btn_my_topics", lang), callback_data="btn_my_topics")
        ],
        [
            InlineKeyboardButton(text=t("btn_hot_deals_hub", lang), callback_data="btn_hot_deals_hub"),
            InlineKeyboardButton(text=t("btn_stats", lang), callback_data="btn_stats")
        ],
        [
            InlineKeyboardButton(text=t("btn_settings", lang), callback_data="btn_settings"),
            InlineKeyboardButton(text=t("btn_help", lang), callback_data="btn_help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_topic_link(group_chat_id: Any, topic_id: int) -> str:
    """Generate Telegram URL to forum topic."""
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


# ==============================================================================
# /START & LANGUAGE SELECTIONqweqw
# ==============================================================================

async def validate_group_for_bot(bot: Bot, chat_id: int, lang: Optional[str] = "en") -> Tuple[bool, str]:
    """Verify that group is a forum, botis administrator, and has manage_topics & pin permissions."""
    try:
        chat = await bot.get_chat(chat_id)
        if not getattr(chat, "is_forum", False):
            return False, t("validate_not_forum", lang)

        bot_info = await bot.get_me()
        member = await bot.get_chat_member(chat_id, bot_info.id)
        if member.status != "administrator":
            return False, t("validate_not_admin", lang)

        if not getattr(member, "can_manage_topics", False):
            return False, t("validate_no_manage_topics", lang)

        if not getattr(member, "can_pin_messages", False):
            return False, t("validate_no_pin", lang)

        return True, ""
    except Exception as e:
        return False, t("validate_error", lang, e=str(e))


async def process_group_connection(message: Message, bot: Bot, user_id: int):
    """Link a validated group to user settings and notify user."""
    u_lang = (await get_user_language(user_id)) or "en" if user_id else "en"
    is_valid, error_msg = await validate_group_for_bot(bot, message.chat.id, lang=u_lang)
    if not is_valid:
        if error_msg:
            await message.answer(error_msg, parse_mode="HTML")
        return

    group_title = message.chat.title or t("group_default_title", u_lang)
    await link_user_group(user_id, message.chat.id, group_title)

    await message.answer(
        t("group_connected_chat", u_lang, title=group_title, user_id=user_id),
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            chat_id=user_id,
            text=t("group_connected_user", u_lang, title=group_title),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(Command("connect"))
async def cmd_connect_group(message: Message, bot: Bot):
    """Handle /connect command inside a personal group."""
    if message.chat.type not in ["group", "supergroup"]:
        user_id = message.from_user.id if message.from_user else None
        u_lang = (await get_user_language(user_id)) or "en" if user_id else "en"
        await message.answer(t("group_only_supergroup_msg", u_lang))
        return

    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    args = (message.text or "").split()
    if len(args) > 1 and args[1].isdigit():
        user_id = int(args[1])

    await process_group_connection(message, bot=bot, user_id=user_id)


@router.my_chat_member()
async def on_my_chat_member_updated(update: ChatMemberUpdated, bot: Bot):
    """Detect when bot is added to a personal group or promoted to administrator."""
    if update.chat.type not in ["group", "supergroup"]:
        return

    if update.new_chat_member.status != "administrator":
        return

    user_id = update.from_user.id if update.from_user else None
    if not user_id:
        return

    u_lang = (await get_user_language(user_id)) or "en" if user_id else "en"
    is_valid, error_msg = await validate_group_for_bot(bot, update.chat.id, lang=u_lang)
    if not is_valid:
        if error_msg:
            try:
                await bot.send_message(chat_id=update.chat.id, text=error_msg, parse_mode="HTML")
            except Exception:
                pass
        return

    group_title = update.chat.title or t("group_default_title", u_lang)
    await link_user_group(user_id, update.chat.id, group_title)

    try:
        await bot.send_message(
            chat_id=update.chat.id,
            text=t("group_connected_chat", u_lang, title=group_title, user_id=user_id),
            parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            chat_id=user_id,
            text=t("group_connected_user", u_lang, title=group_title),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(Command("start"))
async def cmd_start(message: Message, lang: str = "en"):
    """Handle /start command with user language detection and group deep-linking."""
    if not message.from_user:
        return

    # If triggered inside a group via deep link: /start connect_<uid>
    if message.chat.type in ["group", "supergroup"]:
        args = (message.text or "").split()
        target_uid = message.from_user.id
        if len(args) > 1 and "connect_" in args[1]:
            try:
                target_uid = int(args[1].split("connect_")[-1])
            except Exception:
                pass
        if message.bot:
            await process_group_connection(message, bot=message.bot, user_id=target_uid)
        return

    user_id = message.from_user.id
    existing_lang = await get_user_language(user_id)

    if not existing_lang or existing_lang not in LANGUAGES:
        # Prompt for language first
        await message.answer(
            t("select_language", "en"),
            reply_markup=get_language_keyboard(),
            parse_mode="HTML"
        )
    else:
        # User already registered, display main menu in their language
        await message.answer(
            t("welcome_message", existing_lang),
            reply_markup=get_main_menu_keyboard(existing_lang),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("set_lang_"))
async def callback_set_language(callback: CallbackQuery):
    """Set selected language, persist to DB and memory cache, and show main menu."""
    if not callback.data:
        await callback.answer()
        return

    target_lang = callback.data.replace("set_lang_", "").lower()
    if target_lang not in LANGUAGES:
        target_lang = "en"

    if not callback.from_user:
        await callback.answer()
        return

    user_id = callback.from_user.id
    await set_user_language(user_id, target_lang)
    set_cached_user_language(user_id, target_lang)

    success_text = (
        f"{t('language_saved', target_lang)}\n\n"
        f"{t('welcome_message', target_lang)}"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            success_text,
            reply_markup=get_main_menu_keyboard(target_lang),
            parse_mode="HTML"
        )
    await callback.answer()


# ==============================================================================
# /SETTINGS & NOTIFICATION DESTINATION
# ==============================================================================

@router.message(Command("settings"))
@router.callback_query(F.data == "btn_settings")
async def cmd_settings(event: Message | CallbackQuery, lang: str = "en"):
    """Show settings and allow language change, notification destination toggle, and Hot Deals toggle."""
    if not event.from_user:
        return
    user_id = event.from_user.id
    hot_deals_enabled = await get_user_hot_deals_status(user_id)
    notify_settings = await get_user_notification_settings(user_id)
    current_lang_name = LANGUAGES.get(lang, "English")
    status_label = t("status_active", lang) if hot_deals_enabled else t("status_disabled", lang)
    dest_label = t("btn_notify_dest_dm", lang) if notify_settings.get("notification_target") == "dm" else f"{t('btn_notify_dest_group', lang)} ({notify_settings.get('connected_group_title') or 'Topics'})"
    text = t("settings_title", lang, current_lang=current_lang_name, notify_dest=dest_label, hot_deals_status=status_label)
    kb = get_settings_keyboard(lang, hot_deals_enabled, notify_settings)

    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "toggle_hot_deals")
async def callback_toggle_hot_deals(callback: CallbackQuery, lang: str = "en"):
    """Toggle Hot Deals notifications on/off for user."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    new_status = await toggle_user_hot_deals(user_id)
    notify_settings = await get_user_notification_settings(user_id)
    alert_msg = t("hot_deals_enabled_alert", lang) if new_status else t("hot_deals_disabled_alert", lang)

    current_lang_name = LANGUAGES.get(lang, "English")
    status_label = t("status_active", lang) if new_status else t("status_disabled", lang)
    dest_label = t("btn_notify_dest_dm", lang) if notify_settings.get("notification_target") == "dm" else f"{t('btn_notify_dest_group', lang)} ({notify_settings.get('connected_group_title') or 'Topics'})"
    text = t("settings_title", lang, current_lang=current_lang_name, notify_dest=dest_label, hot_deals_status=status_label)
    kb = get_settings_keyboard(lang, new_status, notify_settings)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(alert_msg, show_alert=True)


@router.callback_query(F.data == "btn_connect_group_info")
async def callback_connect_group_info(callback: CallbackQuery, lang: str = "en"):
    """Display deep linking guide to connect a personal supergroup."""
    if not callback.from_user or not callback.bot:
        await callback.answer()
        return
    user_id = callback.from_user.id
    bot_info = await callback.bot.get_me()
    bot_user = bot_info.username or "dOOgagBot"
    deep_link = f"https://t.me/{bot_user}?startgroup=connect_{user_id}&admin=manage_topics+pin_messages"

    notify_settings = await get_user_notification_settings(user_id)
    connected_title = notify_settings.get("connected_group_title")

    text = t("group_connect_info", lang)
    if connected_title:
        text += f"\n\n{t('current_connected_group', lang, title=connected_title)}"

    buttons = [
        [
            InlineKeyboardButton(text=t("btn_select_group_add", lang), url=deep_link)
        ]
    ]
    if connected_title:
        buttons.append([
            InlineKeyboardButton(text=t("btn_disconnect_group", lang), callback_data="btn_disconnect_group")
        ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_back_to_settings", lang), callback_data="btn_settings")
    ])

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "btn_switch_to_dm")
async def callback_switch_to_dm(callback: CallbackQuery, lang: str = "en"):
    """Switch notification destination to Private Chat (DM)."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    await set_user_notification_target(user_id, "dm")
    await callback.answer(t("group_switch_dm_alert", lang), show_alert=True)
    await cmd_settings(callback, lang)


@router.callback_query(F.data == "btn_switch_to_group")
async def callback_switch_to_group(callback: CallbackQuery, lang: str = "en"):
    """Switch notification destination to Personal Group (Topics)."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    await set_user_notification_target(user_id, "group")
    await callback.answer(t("group_switch_group_alert", lang), show_alert=True)
    await cmd_settings(callback, lang)


@router.callback_query(F.data == "btn_disconnect_group")
async def callback_disconnect_group(callback: CallbackQuery, lang: str = "en"):
    """Disconnect linked group and revert destination to DM."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    await unlink_user_group(user_id)
    await callback.answer(t("group_disconnected_alert", lang), show_alert=True)
    await cmd_settings(callback, lang)


# ==============================================================================
# HOT DEALS DASHBOARD & PARAMETER HANDLERS
# ==============================================================================

@router.callback_query(F.data == "btn_hot_deals_menu")
async def callback_hot_deals_menu(callback: CallbackQuery, lang: str = "en"):
    """Show Hot Deals preferences dashboard."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    hd = await get_user_hot_deals_settings(user_id)
    text = build_hot_deals_dashboard_text(hd, lang)
    kb = build_hot_deals_dashboard_keyboard(hd, lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "hd_toggle_status")
async def callback_hd_toggle_status(callback: CallbackQuery, lang: str = "en"):
    """Toggle hot deals status from dashboard."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    current = await get_user_hot_deals_settings(user_id)
    new_enabled = not current["enabled"]
    updated = await update_user_hot_deals_settings(user_id, enabled=new_enabled)
    text = build_hot_deals_dashboard_text(updated, lang)
    kb = build_hot_deals_dashboard_keyboard(updated, lang)
    alert = t("hot_deals_enabled_alert", lang) if new_enabled else t("hot_deals_disabled_alert", lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(alert, show_alert=True)


@router.callback_query(F.data == "hd_param_profit")
async def callback_hd_param_profit(callback: CallbackQuery, lang: str = "en"):
    """Select minimum net profit."""
    text = t("choose_min_profit", lang)
    buttons = [
        [
            InlineKeyboardButton(text="≥ 1 000 €", callback_data="hd_set_profit_1000"),
            InlineKeyboardButton(text="≥ 1 500 €", callback_data="hd_set_profit_1500")
        ],
        [
            InlineKeyboardButton(text="≥ 2 000 €", callback_data="hd_set_profit_2000"),
            InlineKeyboardButton(text="≥ 3 000 €", callback_data="hd_set_profit_3000")
        ],
        [
            InlineKeyboardButton(text="≥ 5 000 €", callback_data="hd_set_profit_5000")
        ],
        [
            InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_menu")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("hd_set_profit_"))
async def callback_hd_set_profit(callback: CallbackQuery, lang: str = "en"):
    """Save selected profit and return to dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    val = float(callback.data.replace("hd_set_profit_", ""))
    user_id = callback.from_user.id
    updated = await update_user_hot_deals_settings(user_id, min_profit_eur=val)
    text = build_hot_deals_dashboard_text(updated, lang)
    kb = build_hot_deals_dashboard_keyboard(updated, lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(t("hd_param_updated", lang))


@router.callback_query(F.data == "hd_param_year")
async def callback_hd_param_year(callback: CallbackQuery, lang: str = "en"):
    """Select minimum car year."""
    text = t("choose_min_year", lang)
    buttons = [
        [
            InlineKeyboardButton(text=t("any_year", lang), callback_data="hd_set_year_0"),
            InlineKeyboardButton(text="2010+", callback_data="hd_set_year_2010")
        ],
        [
            InlineKeyboardButton(text="2012+", callback_data="hd_set_year_2012"),
            InlineKeyboardButton(text="2015+", callback_data="hd_set_year_2015")
        ],
        [
            InlineKeyboardButton(text="2018+", callback_data="hd_set_year_2018"),
            InlineKeyboardButton(text="2020+", callback_data="hd_set_year_2020")
        ],
        [
            InlineKeyboardButton(text="2022+", callback_data="hd_set_year_2022")
        ],
        [
            InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_menu")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("hd_set_year_"))
async def callback_hd_set_year(callback: CallbackQuery, lang: str = "en"):
    """Save selected year and return to dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    val = int(callback.data.replace("hd_set_year_", ""))
    user_id = callback.from_user.id
    updated = await update_user_hot_deals_settings(user_id, min_year=val)
    text = build_hot_deals_dashboard_text(updated, lang)
    kb = build_hot_deals_dashboard_keyboard(updated, lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(t("hd_param_updated", lang))


@router.callback_query(F.data == "hd_param_price")
async def callback_hd_param_price(callback: CallbackQuery, lang: str = "en"):
    """Select maximum car purchase price."""
    text = t("choose_max_price", lang)
    buttons = [
        [
            InlineKeyboardButton(text=t("unlimited_price", lang), callback_data="hd_set_price_0"),
            InlineKeyboardButton(text="≤ 10 000 €", callback_data="hd_set_price_10000")
        ],
        [
            InlineKeyboardButton(text="≤ 15 000 €", callback_data="hd_set_price_15000"),
            InlineKeyboardButton(text="≤ 20 000 €", callback_data="hd_set_price_20000")
        ],
        [
            InlineKeyboardButton(text="≤ 30 000 €", callback_data="hd_set_price_30000"),
            InlineKeyboardButton(text="≤ 50 000 €", callback_data="hd_set_price_50000")
        ],
        [
            InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_menu")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("hd_set_price_"))
async def callback_hd_set_price(callback: CallbackQuery, lang: str = "en"):
    """Save selected price and return to dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    val = float(callback.data.replace("hd_set_price_", ""))
    user_id = callback.from_user.id
    updated = await update_user_hot_deals_settings(user_id, max_price_eur=val)
    text = build_hot_deals_dashboard_text(updated, lang)
    kb = build_hot_deals_dashboard_keyboard(updated, lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(t("hd_param_updated", lang))


@router.callback_query(F.data == "hd_param_interval")
async def callback_hd_param_interval(callback: CallbackQuery, lang: str = "en"):
    """Select alert frequency interval."""
    text = t("choose_interval", lang)
    buttons = [
        [
            InlineKeyboardButton(text=t("interval_realtime", lang), callback_data="hd_set_interval_0"),
            InlineKeyboardButton(text=t("interval_1h", lang), callback_data="hd_set_interval_1")
        ],
        [
            InlineKeyboardButton(text=t("interval_3h", lang), callback_data="hd_set_interval_3"),
            InlineKeyboardButton(text=t("interval_6h", lang), callback_data="hd_set_interval_6")
        ],
        [
            InlineKeyboardButton(text=t("interval_24h", lang), callback_data="hd_set_interval_24")
        ],
        [
            InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_menu")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("hd_set_interval_"))
async def callback_hd_set_interval(callback: CallbackQuery, lang: str = "en"):
    """Save selected interval and return to dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    val = int(callback.data.replace("hd_set_interval_", ""))
    user_id = callback.from_user.id
    updated = await update_user_hot_deals_settings(user_id, interval_hours=val)
    text = build_hot_deals_dashboard_text(updated, lang)
    kb = build_hot_deals_dashboard_keyboard(updated, lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(t("hd_param_updated", lang))


@router.callback_query(F.data == "hd_param_pct")
async def callback_hd_param_pct(callback: CallbackQuery, lang: str = "en"):
    """Select minimum profit margin percentage."""
    text = t("choose_min_pct", lang)
    buttons = [
        [
            InlineKeyboardButton(text="≥ 15%", callback_data="hd_set_pct_15"),
            InlineKeyboardButton(text="≥ 20%", callback_data="hd_set_pct_20")
        ],
        [
            InlineKeyboardButton(text="≥ 25%", callback_data="hd_set_pct_25"),
            InlineKeyboardButton(text="≥ 30%", callback_data="hd_set_pct_30")
        ],
        [
            InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_menu")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("hd_set_pct_"))
async def callback_hd_set_pct(callback: CallbackQuery, lang: str = "en"):
    """Save selected profit percentage and return to dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    val = float(callback.data.replace("hd_set_pct_", ""))
    user_id = callback.from_user.id
    updated = await update_user_hot_deals_settings(user_id, min_profit_percent=val)
    text = build_hot_deals_dashboard_text(updated, lang)
    kb = build_hot_deals_dashboard_keyboard(updated, lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(t("hd_pct_updated", lang))


@router.callback_query(F.data == "hd_param_type")
async def callback_hd_param_type(callback: CallbackQuery, lang: str = "en"):
    """Select Hot Deal focus category."""
    text = t("choose_deal_type", lang)
    buttons = [
        [InlineKeyboardButton(text=get_deal_type_label("all", lang), callback_data="hd_set_type_all")],
        [InlineKeyboardButton(text=get_deal_type_label("top_profit", lang), callback_data="hd_set_type_top_profit")],
        [InlineKeyboardButton(text=get_deal_type_label("new_cars", lang), callback_data="hd_set_type_new_cars")],
        [InlineKeyboardButton(text=get_deal_type_label("low_mileage", lang), callback_data="hd_set_type_low_mileage")],
        [InlineKeyboardButton(text=get_deal_type_label("low_mileage_cheap", lang), callback_data="hd_set_type_low_mileage_cheap")],
        [InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_menu")]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("hd_set_type_"))
async def callback_hd_set_type(callback: CallbackQuery, lang: str = "en"):
    """Save selected focus category and return to dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    val = callback.data.replace("hd_set_type_", "")
    user_id = callback.from_user.id
    updated = await update_user_hot_deals_settings(user_id, deal_type=val)
    text = build_hot_deals_dashboard_text(updated, lang)
    kb = build_hot_deals_dashboard_keyboard(updated, lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(t("hd_type_updated", lang))


@router.callback_query(F.data == "hd_param_mileage")
async def callback_hd_param_mileage(callback: CallbackQuery, lang: str = "en"):
    """Select max mileage for Hot Deals."""
    text = t("choose_max_mileage", lang)
    buttons = [
        [
            InlineKeyboardButton(text=t("flim_unlimited", lang), callback_data="hd_set_mileage_0"),
            InlineKeyboardButton(text="≤ 60 000 km", callback_data="hd_set_mileage_60000")
        ],
        [
            InlineKeyboardButton(text="≤ 100 000 km", callback_data="hd_set_mileage_100000"),
            InlineKeyboardButton(text="≤ 150 000 km", callback_data="hd_set_mileage_150000")
        ],
        [
            InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_menu")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("hd_set_mileage_"))
async def callback_hd_set_mileage(callback: CallbackQuery, lang: str = "en"):
    """Save selected mileage and return to dashboard."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    val = int(callback.data.replace("hd_set_mileage_", ""))
    user_id = callback.from_user.id
    updated = await update_user_hot_deals_settings(user_id, max_mileage=val)
    text = build_hot_deals_dashboard_text(updated, lang)
    kb = build_hot_deals_dashboard_keyboard(updated, lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(t("hd_mileage_updated", lang))


# ==============================================================================
# HOT DEALS HUB & INTERACTIVE DEAL BROWSER
# ==============================================================================

@router.message(Command("hotdeals"))
@router.callback_query(F.data == "btn_hot_deals_hub")
async def cmd_hot_deals_hub(event: Message | CallbackQuery, lang: str = "en"):
    """Dedicated Hot Deals & Pan-European Arbitrage Explorer Hub."""
    user_id = event.from_user.id if event.from_user else 0
    hd = await get_user_hot_deals_settings(user_id)
    status_label = t("status_active", lang) if hd.get("enabled", True) else t("status_disabled", lang)
    min_profit_str = f"{int(hd.get('min_profit_eur', 1500)):,}".replace(",", " ")
    min_pct_str = f"{int(hd.get('min_profit_percent', 15))}%"
    deal_type_str = get_deal_type_label(hd.get("deal_type", "all"), lang)
    min_year_str = f"{hd.get('min_year', 2012)}+" if hd.get("min_year", 0) > 0 else t("any_label", lang)
    max_price_str = f"≤ {int(hd.get('max_price_eur', 0)):,} €".replace(",", " ") if hd.get("max_price_eur", 0) > 0 else t("unlimited", lang)

    titles = {
        "en": "🔥 <b>HOT DEALS & ARBITRAGE HUB</b>",
        "pl": "🔥 <b>CENTRUM HOT DEALS I ARBITRAŻU</b>",
        "ru": "🔥 <b>ЦЕНТР HOT DEALS И АРБИТРАЖА</b>"
    }
    subtitles = {
        "en": "High-arbitrage cars across European markets priced significantly below the Polish (Otomoto) benchmark.",
        "pl": "Samochody z wysokim arbitrażem w Europie o cenach znacznie niższych od mediany Otomoto.pl.",
        "ru": "Автомобили с высоким арбитражем в Европе по ценам существенно ниже польского рынка Otomoto.pl."
    }
    lbl_alerts = {"en": "Private Alerts", "pl": "Powiadomienia", "ru": "Уведомления"}.get(lang, "Alerts")
    lbl_profit = {"en": "Min. Net Profit", "pl": "Min. Zysk Netto", "ru": "Мин. Чистая Прибыль"}.get(lang, "Min. Profit")
    lbl_pct = {"en": "Min. Margin", "pl": "Min. Marża", "ru": "Мин. Маржа"}.get(lang, "Min. Margin")
    lbl_cat = {"en": "Category", "pl": "Kategoria", "ru": "Категория"}.get(lang, "Category")
    lbl_year = {"en": "Year", "pl": "Rocznik", "ru": "Год"}.get(lang, "Year")
    lbl_budget = {"en": "Budget", "pl": "Budżet", "ru": "Бюджет"}.get(lang, "Budget")
    lbl_hint = {
        "en": "<i>Browse live top deals below or customize your preferences:</i>",
        "pl": "<i>Przeglądaj okazje poniżej lub zmień preferencje:</i>",
        "ru": "<i>Смотрите актуальные сделки ниже или настройте фильтры:</i>"
    }.get(lang, "Browse deals:")

    hub_title = titles.get(lang, titles["en"])
    hub_sub = subtitles.get(lang, subtitles["en"])

    text = (
        f"{hub_title}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{hub_sub}\n\n"
        f"• <b>{lbl_alerts}:</b> {status_label}\n"
        f"• <b>{lbl_profit}:</b> ≥ {min_profit_str} €\n"
        f"• <b>{lbl_pct}:</b> ≥ {min_pct_str}\n"
        f"• <b>{lbl_cat}:</b> {deal_type_str}\n"
        f"• <b>{lbl_year}:</b> {min_year_str} | <b>{lbl_budget}:</b> {max_price_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{lbl_hint}"
    )

    btn_browse_txt = {"en": "🔍 Browse Live Deals (Top 10)", "pl": "🔍 Przeglądaj Okazje (Top 10)", "ru": "🔍 Смотреть Сделки (Топ 10)"}.get(lang, "🔍 Top 10")
    btn_pref_txt = t("btn_hot_deals_settings", lang)
    btn_alerts_txt = {"en": "🔔 Alerts Toggle", "pl": "🔔 Powiadomienia", "ru": "🔔 Уведомления"}.get(lang, "🔔 Alerts")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=btn_browse_txt, callback_data="hd_browse_0")
        ],
        [
            InlineKeyboardButton(text=btn_pref_txt, callback_data="btn_hot_deals_menu"),
            InlineKeyboardButton(text=btn_alerts_txt, callback_data="hd_toggle_status")
        ],
        [
            InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="btn_main_menu")
        ]
    ])

    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("hd_browse_"))
async def callback_hd_browse(callback: CallbackQuery, lang: str = "en"):
    """Browse live top 10 hot deals calculated against Poland market benchmarks."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    page = int(callback.data.replace("hd_browse_", ""))
    user_id = callback.from_user.id
    hd = await get_user_hot_deals_settings(user_id)

    deals = await get_top_arbitrage_deals(
        limit=10,
        deal_type=hd.get("deal_type", "all"),
        min_profit_eur=hd.get("min_profit_eur", 1000.0),
        min_profit_pct=hd.get("min_profit_percent", 15.0),
        min_year=hd.get("min_year", 0),
        max_price=hd.get("max_price_eur", 0.0),
        max_mileage=hd.get("max_mileage", 0)
    )

    if not deals:
        msg = {
            "en": "ℹ️ <b>No Hot Deals matching these criteria right now.</b>\n\nTry lowering the minimum net profit or margin in Preferences to see more deals.",
            "pl": "ℹ️ <b>Brak ofert spełniających te kryteria w tej chwili.</b>\n\nSpróbuj zmniejszyć minimalny zysk lub marżę w Preferencjach.",
            "ru": "ℹ️ <b>Сейчас нет сделок по этим критериям.</b>\n\nПопробуйте снизить порог минимальной прибыли в Настройках."
        }.get(lang, "No deals found.")
        buttons = [
            [InlineKeyboardButton(text=t("btn_hot_deals_settings", lang), callback_data="btn_hot_deals_menu")],
            [InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_hub")]
        ]
        if isinstance(callback.message, Message):
            await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
        await callback.answer()
        return

    total = len(deals)
    if page >= total:
        page = total - 1
    if page < 0:
        page = 0

    deal = deals[page]
    title = deal["title"]
    price_eur = deal["price_eur"]
    bench_eur = deal["benchmark_eur"]
    profit_eur = deal["est_profit_eur"]
    profit_pct = deal["est_profit_pct"]
    year = deal.get("year") or "-"
    mileage = f"{deal['mileage_km']:,} km".replace(",", " ") if deal.get("mileage_km") else "-"
    platform = deal["platform"]
    country = deal["country_code"]
    url = deal["url"]

    hd_header = {"en": "HOT DEAL", "pl": "OKAZJA", "ru": "ГОРЯЧАЯ СДЕЛКА"}.get(lang, "HOT DEAL")
    lbl_src = {"en": "Source", "pl": "Źródło", "ru": "Источник"}.get(lang, "Source")
    lbl_yr = {"en": "Year", "pl": "Rocznik", "ru": "Год"}.get(lang, "Year")
    lbl_mil = {"en": "Mileage", "pl": "Przebieg", "ru": "Пробег"}.get(lang, "Mileage")
    lbl_buy = {"en": "Purchase Price", "pl": "Cena Zakupu", "ru": "Цена Покупки"}.get(lang, "Price")
    lbl_bench = {"en": "Poland Benchmark (Otomoto)", "pl": "Rynek w Polsce (Otomoto)", "ru": "Рынок Польши (Otomoto)"}.get(lang, "Benchmark")
    lbl_prof = {"en": "Est. Net Profit", "pl": "Szacowany Zysk Netto", "ru": "Расчетная Прибыль"}.get(lang, "Est. Profit")
    lbl_margin = {"en": "Profit Margin", "pl": "Marża Zysku", "ru": "Маржа Прибыли"}.get(lang, "Margin")

    deal_card = (
        f"🔥 <b>{hd_header} ({page + 1}/{total})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚗 <b>{title}</b>\n"
        f"• <b>{lbl_src}:</b> {country} ({platform})\n"
        f"• <b>{lbl_yr}:</b> {year} | <b>{lbl_mil}:</b> {mileage}\n\n"
        f"💶 <b>{lbl_buy}:</b> <b>{price_eur:,.0f} €</b>\n"
        f"🇵🇱 <b>{lbl_bench}:</b> <b>~{bench_eur:,.0f} €</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>{lbl_prof}:</b> <b>+{profit_eur:,.0f} €</b>\n"
        f"📈 <b>{lbl_margin}:</b> <b>+{profit_pct}%</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

    nav_row = []
    btn_prev_txt = {"en": "⬅️ Prev", "pl": "⬅️ Poprzedni", "ru": "⬅️ Назад"}.get(lang, "⬅️")
    btn_next_txt = {"en": "Next ➡️", "pl": "Następny ➡️", "ru": "Вперед ➡️"}.get(lang, "➡️")
    if page > 0:
        nav_row.append(InlineKeyboardButton(text=btn_prev_txt, callback_data=f"hd_browse_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📌 {page + 1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav_row.append(InlineKeyboardButton(text=btn_next_txt, callback_data=f"hd_browse_{page + 1}"))

    btn_view_txt = {"en": "🔗 View Original Listing", "pl": "🔗 Zobacz Ofertę", "ru": "🔗 Смотреть Объявление"}.get(lang, "🔗 View")

    buttons = [
        nav_row,
        [InlineKeyboardButton(text=btn_view_txt, url=url)],
        [
            InlineKeyboardButton(text=t("btn_hot_deals_settings", lang), callback_data="btn_hot_deals_menu"),
            InlineKeyboardButton(text=t("btn_back_to_hd", lang), callback_data="btn_hot_deals_hub")
        ]
    ]

    if isinstance(callback.message, Message):
        await callback.message.edit_text(deal_card, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "btn_main_menu")
async def callback_main_menu(callback: CallbackQuery, lang: str = "en"):
    """Return to main menu."""
    text = t("welcome_message", lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(lang), parse_mode="HTML")
    await callback.answer()


# ==============================================================================
# /MY_TOPICS & PRIVATE DM FILTER MANAGEMENT
# ==============================================================================

@router.message(Command("my_topics"))
@router.message(Command("filters"))
@router.message(Command("myfilters"))
@router.callback_query(F.data.in_(["btn_my_topics", "btn_my_filters"]))
async def cmd_my_topics(event: Message | CallbackQuery, lang: str = "en"):
    """List and manage user's private search filters."""
    # Always answer callback early to stop client spinner immediately
    if isinstance(event, CallbackQuery):
        try:
            await event.answer()
        except Exception:
            pass

    if not event.from_user:
        return
    user_id = event.from_user.id
    filters = await get_user_filters(user_id)

    if not filters:
        no_topics_text = t("no_topics_found", lang)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_new_search", lang), callback_data="btn_new_search")],
            [InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="btn_main_menu")]
        ])
        if isinstance(event, CallbackQuery):
            if isinstance(event.message, Message):
                await event.message.edit_text(no_topics_text, reply_markup=kb, parse_mode="HTML")
        else:
            await event.answer(no_topics_text, reply_markup=kb, parse_mode="HTML")
        return

    # Build topic list message
    lines = [
        t("my_topics_subtitle", lang) + "\n"
    ]
    for idx, f in enumerate(filters, start=1):
        status_str = t("status_active", lang) if f["is_active"] == 1 else t("status_paused", lang)
        make = f["make"]
        model = f["model"] or t("all_models", lang)
        y_min, y_max = f.get("year_min"), f.get("year_max")
        price_max = f.get("price_max_eur")

        details = []
        if y_min and y_max:
            details.append(f"{y_min}-{y_max}")
        elif y_min:
            details.append(f"≥{y_min}")
        elif y_max:
            details.append(f"≤{y_max}")
        if price_max:
            details.append(f"≤{price_max:,.0f}€".replace(",", " "))

        details_str = f" ({', '.join(details)})" if details else ""
        lines.append(f"<b>{idx}.</b> 🚙 <b>{make} {model}</b>{details_str} — [{status_str}]")

    header_text = "\n".join(lines)
    
    # We display control keyboards for each filter
    buttons = []
    for f in filters[:10]:
        fid = f["id"]
        status_action = t("btn_pause_action", lang) if f["is_active"] == 1 else t("btn_resume_action", lang)
        make = f["make"]
        model = f["model"] or ""
        row = [
            InlineKeyboardButton(text=f"⚙️ #{fid} {make} {model}".strip(), callback_data=f"filter_details_{fid}"),
            InlineKeyboardButton(text=status_action, callback_data=f"topic_toggle_{fid}")
        ]
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text=t("btn_new_search", lang), callback_data="btn_new_search"),
        InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="btn_main_menu")
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        if isinstance(event, CallbackQuery):
            if isinstance(event.message, Message):
                await event.message.edit_text(header_text, reply_markup=kb, parse_mode="HTML")
        else:
            await event.answer(header_text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error rendering cmd_my_topics: {e}")


async def show_filter_details(event: Message | CallbackQuery, filter_id: int, lang: str = "en"):
    """Render full filter settings, editing dashboard, and live fetch action."""
    if isinstance(event, CallbackQuery):
        try:
            await event.answer()
        except Exception:
            pass

    flt = await get_filter_by_id(filter_id)
    if not flt:
        return
    fid = flt["id"]
    make = flt["make"]
    model = flt["model"] or t("all_models", lang)
    y_min = flt.get("year_min")
    y_max = flt.get("year_max")
    year_str = f"{y_min} - {y_max}" if (y_min and y_max) else (f"≥ {y_min}" if y_min else (f"≤ {y_max}" if y_max else t("any_label", lang)))
    
    p_min = flt.get("price_min_eur")
    p_max = flt.get("price_max_eur")
    price_str = f"{p_min:,.0f} € - {p_max:,.0f} €".replace(",", " ") if (p_min and p_max) else (f"≤ {p_max:,.0f} €".replace(",", " ") if p_max else t("unlimited", lang))
    
    mileage_max = flt.get("mileage_max")
    mileage_str = f"≤ {mileage_max:,} km".replace(",", " ") if mileage_max else t("unlimited", lang)
    
    limit_val = flt.get("daily_alert_limit", 0) or 0
    limit_label = format_limit_label(limit_val, lang)
    sent_today = flt.get("alerts_sent_today", 0) or 0
    
    age_val = flt.get("listing_age_hours", 0) or 0
    age_label = format_age_label(age_val, lang)
    
    status_str = t("status_active", lang) if flt["is_active"] == 1 else t("status_paused", lang)
    status_action = t("btn_pause_action", lang) if flt["is_active"] == 1 else t("btn_resume_action", lang)

    fuel_str = get_option_label("fuel", flt.get("fuel_type", "all"), lang)
    trans_str = get_option_label("transmission", flt.get("transmission", "all"), lang)
    country_str = get_option_label("country", flt.get("target_country", "ALL"), lang)

    title_text = t("filter_details_title", lang, fid=fid)
    car_lbl = t("filter_car_label", lang)
    year_lbl = t("filter_year_label", lang)
    price_lbl = t("filter_price_label", lang)
    mileage_lbl = t("filter_mileage_label", lang)
    fuel_lbl = t("filter_fuel_label", lang)
    gearbox_lbl = t("filter_gearbox_label", lang)
    market_lbl = t("filter_market_label", lang)
    limit_lbl = t("filter_limit_label", lang)
    age_lbl = t("filter_age_label", lang)
    status_lbl = t("filter_status_label", lang)
    edit_hint = t("filter_edit_hint", lang)
    sent_str = t("sent_today_label", lang, count=sent_today)

    text = (
        f"{title_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚙 <b>{car_lbl}:</b> {make} {model}\n"
        f"📅 <b>{year_lbl}:</b> {year_str}\n"
        f"💰 <b>{price_lbl}:</b> {price_str}\n"
        f"🧭 <b>{mileage_lbl}:</b> {mileage_str}\n"
        f"⛽ <b>{fuel_lbl}:</b> {fuel_str} | <b>{gearbox_lbl}:</b> {trans_str}\n"
        f"🌍 <b>{market_lbl}:</b> {country_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>{limit_lbl}:</b> {limit_label} ({sent_str})\n"
        f"⏱️ <b>{age_lbl}:</b> {age_label}\n"
        f"🔘 <b>{status_lbl}:</b> {status_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{edit_hint}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_edit_model", lang), callback_data=f"fedit_model_{fid}")
        ],
        [
            InlineKeyboardButton(text=t("btn_edit_year", lang), callback_data=f"fedit_year_{fid}"),
            InlineKeyboardButton(text=t("btn_edit_price", lang), callback_data=f"fedit_price_{fid}")
        ],
        [
            InlineKeyboardButton(text=t("btn_edit_mileage", lang), callback_data=f"fedit_mileage_{fid}"),
            InlineKeyboardButton(text=t("btn_edit_limit", lang), callback_data=f"fedit_limit_{fid}")
        ],
        [
            InlineKeyboardButton(text=t("btn_edit_age", lang), callback_data=f"fedit_age_{fid}")
        ],
        [
            InlineKeyboardButton(text=t("btn_fetch_now", lang), callback_data=f"filter_fetch_now_{fid}")
        ],
        [
            InlineKeyboardButton(text=status_action, callback_data=f"topic_toggle_{fid}"),
            InlineKeyboardButton(text=t("btn_delete_filter", lang), callback_data=f"topic_del_prompt_{fid}")
        ],
        [
            InlineKeyboardButton(text=t("btn_back_to_filters", lang), callback_data="btn_my_topics")
        ]
    ])

    try:
        if isinstance(event, CallbackQuery):
            if isinstance(event.message, Message):
                await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        else:
            await event.answer(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error rendering show_filter_details: {e}")


@router.callback_query(F.data.startswith("filter_details_"))
async def callback_filter_details(callback: CallbackQuery, lang: str = "en"):
    """Show details for a specific filter."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("filter_details_", ""))
    await show_filter_details(callback, fid, lang)


@router.callback_query(F.data.startswith("filter_fetch_now_"))
async def callback_filter_fetch_now(callback: CallbackQuery, bot: Bot, lang: str = "en"):
    """Instantly search existing database listings matching filter and send top matches to DM."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("filter_fetch_now_", ""))
    if not isinstance(callback.message, Message) or not callback.from_user:
        await callback.answer()
        return
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer(t("filter_not_found", lang), show_alert=True)
        return

    await callback.answer(t("fetch_searching", lang), show_alert=False)
    matches = await search_seen_listings_for_filter(flt, limit=5)
    if not matches:
        await callback.message.answer(
            t("fetch_not_found", lang, make_model=f"{flt['make']} {flt.get('model') or ''}"),
            parse_mode="HTML"
        )
        return

    await callback.message.answer(
        t("fetch_sending", lang, count=len(matches)),
        parse_mode="HTML"
    )

    for item in matches:
        title = item["title"]
        price = item["price_eur"]
        year = item.get("year") or "-"
        mileage = f"{item['mileage_km']:,} km".replace(",", " ") if item.get("mileage_km") else "-"
        url = item["url"]
        photo = item.get("photo_url")
        platform = item["platform"]
        country = item["country_code"]

        card_text = t(
            "fetch_card",
            lang,
            title=title,
            country=country,
            platform=platform,
            year=year,
            mileage=mileage,
            price=price,
            url=url
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_view_listing", lang), url=url)]
        ])
        try:
            if photo and photo.startswith("http"):
                await bot.send_photo(chat_id=callback.from_user.id, photo=photo, caption=card_text, reply_markup=kb, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=callback.from_user.id, text=card_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Could not send fetched listing: {e}")


# ==============================================================================
# INLINE FILTER EDITING (Model, Year, Price, Mileage, Limit, Age)
# ==============================================================================

@router.callback_query(F.data.startswith("fedit_limit_"))
async def callback_fedit_limit(callback: CallbackQuery, lang: str = "en"):
    """Select daily alert limit for this filter."""
    if not callback.data:
        await callback.answer()
        return
    fid = int(callback.data.replace("fedit_limit_", ""))
    text = t("daily_limit_title", lang)
    buttons = [
        [
            InlineKeyboardButton(text=t("flim_unlimited", lang), callback_data=f"flim_set_{fid}_0"),
            InlineKeyboardButton(text=t("flim_per_day", lang, n="🔟 10"), callback_data=f"flim_set_{fid}_10")
        ],
        [
            InlineKeyboardButton(text=t("flim_per_day", lang, n="2️⃣5️⃣ 25"), callback_data=f"flim_set_{fid}_25"),
            InlineKeyboardButton(text=t("flim_per_day", lang, n="5️⃣0️⃣ 50"), callback_data=f"flim_set_{fid}_50")
        ],
        [
            InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"filter_details_{fid}")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("flim_set_"))
async def callback_flim_set(callback: CallbackQuery, lang: str = "en"):
    """Save daily limit and return to filter details."""
    if not callback.data:
        await callback.answer()
        return
    parts = callback.data.split("_")
    fid = int(parts[2])
    val = int(parts[3])
    await update_user_filter(fid, daily_alert_limit=val)
    await callback.answer(t("daily_limit_updated", lang))
    await show_filter_details(callback, fid, lang)


@router.callback_query(F.data.startswith("fedit_age_"))
async def callback_fedit_age(callback: CallbackQuery, lang: str = "en"):
    """Select listing freshness / age window."""
    if not callback.data:
        await callback.answer()
        return
    fid = int(callback.data.replace("fedit_age_", ""))
    text = t("age_window_title", lang)
    buttons = [
        [
            InlineKeyboardButton(text=t("fage_realtime", lang), callback_data=f"fage_set_{fid}_0"),
            InlineKeyboardButton(text=t("fage_1h", lang), callback_data=f"fage_set_{fid}_1")
        ],
        [
            InlineKeyboardButton(text=t("fage_24h", lang), callback_data=f"fage_set_{fid}_24"),
            InlineKeyboardButton(text=t("fage_7d", lang), callback_data=f"fage_set_{fid}_168")
        ],
        [
            InlineKeyboardButton(text=t("fage_30d", lang), callback_data=f"fage_set_{fid}_720"),
            InlineKeyboardButton(text=t("fage_all", lang), callback_data=f"fage_set_{fid}_99999")
        ],
        [
            InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"filter_details_{fid}")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("fage_set_"))
async def callback_fage_set(callback: CallbackQuery, lang: str = "en"):
    """Save listing age window and return to filter details."""
    if not callback.data:
        await callback.answer()
        return
    parts = callback.data.split("_")
    fid = int(parts[2])
    val = int(parts[3])
    await update_user_filter(fid, listing_age_hours=val)
    await callback.answer(t("age_window_updated", lang))
    await show_filter_details(callback, fid, lang)


@router.callback_query(F.data.startswith("fedit_model_"))
async def callback_fedit_model(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Start model edit flow."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("fedit_model_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer(t("filter_not_found", lang), show_alert=True)
        return

    await state.update_data(edit_filter_id=fid)
    await state.set_state(FilterEditState.waiting_for_model)

    prompt = t("edit_model_prompt", lang, make=flt['make'], model=flt.get('model') or '')
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


@router.message(FilterEditState.waiting_for_model)
async def process_fedit_model(message: Message, state: FSMContext, lang: str = "en"):
    """Handle new model input and update filter."""
    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer(t("edit_cancelled", lang), reply_markup=get_main_menu_keyboard(lang))
        return

    data = await state.get_data()
    fid = data.get("edit_filter_id")
    if not fid:
        await state.clear()
        return

    flt = await get_filter_by_id(fid)
    if not flt:
        await state.clear()
        return

    all_models_label = {"en": "All Models", "pl": "Wszystkie Modele", "ru": "Все Модели"}.get(lang, "All Models")
    if text in ("-", "all"):
        await update_user_filter(fid, model="")
        new_label = f"{flt['make']} ({all_models_label})"
    else:
        # Check if user entered "Toyota Auris"
        parts = text.split(maxsplit=1)
        known_makes = {"Toyota", "Bmw", "Mercedes", "Mercedes-Benz", "Audi", "Volkswagen", "Ford", "Skoda", "Renault", "Peugeot", "Kia", "Hyundai", "Nissan", "Honda", "Volvo", "Opel", "Seat", "Porsche", "Mazda"}
        if len(parts) == 2 and parts[0].title() in known_makes:
            new_make = parts[0].title()
            new_model = parts[1].title()
            await update_user_filter(fid, make=new_make, model=new_model)
            new_label = f"{new_make} {new_model}"
        else:
            new_model = text.title()
            await update_user_filter(fid, model=new_model)
            new_label = f"{flt['make']} {new_model}"

    await state.clear()
    await message.answer(t("edit_model_success", lang, label=new_label), parse_mode="HTML")
    await show_filter_details(message, fid, lang)


@router.callback_query(F.data.startswith("fedit_year_"))
async def callback_fedit_year(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Start year range edit flow."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("fedit_year_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer(t("filter_not_found", lang), show_alert=True)
        return

    await state.update_data(edit_filter_id=fid)
    await state.set_state(FilterEditState.waiting_for_year)

    prompt = t("edit_year_prompt", lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


@router.message(FilterEditState.waiting_for_year)
async def process_fedit_year(message: Message, state: FSMContext, lang: str = "en"):
    """Handle new year range input."""
    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer(t("edit_cancelled", lang), reply_markup=get_main_menu_keyboard(lang))
        return

    data = await state.get_data()
    fid = data.get("edit_filter_id")
    if not fid:
        await state.clear()
        return

    if text in ("-", "0", "all"):
        await update_user_filter(fid, year_min=None, year_max=None)
        await state.clear()
        await message.answer(t("edit_year_cleared", lang), parse_mode="HTML")
        await show_filter_details(message, fid, lang)
        return

    parts = [int(p) for p in text.split() if p.isdigit()]
    if not parts:
        await message.answer(t("edit_year_invalid", lang), parse_mode="HTML")
        return

    y_min = parts[0]
    y_max = parts[1] if len(parts) > 1 else None
    if y_max and y_min > y_max:
        y_min, y_max = y_max, y_min

    await update_user_filter(fid, year_min=y_min, year_max=y_max)
    await state.clear()
    range_str = f"{y_min}{' - ' + str(y_max) if y_max else '+'}"
    await message.answer(t("edit_year_success", lang, range=range_str), parse_mode="HTML")
    await show_filter_details(message, fid, lang)


@router.callback_query(F.data.startswith("fedit_price_"))
async def callback_fedit_price(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Start price range edit flow."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("fedit_price_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer(t("filter_not_found", lang), show_alert=True)
        return

    await state.update_data(edit_filter_id=fid)
    await state.set_state(FilterEditState.waiting_for_price)

    prompt = t("edit_price_prompt", lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


@router.message(FilterEditState.waiting_for_price)
async def process_fedit_price(message: Message, state: FSMContext, lang: str = "en"):
    """Handle new price input."""
    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer(t("edit_cancelled", lang), reply_markup=get_main_menu_keyboard(lang))
        return

    data = await state.get_data()
    fid = data.get("edit_filter_id")
    if not fid:
        await state.clear()
        return

    if text in ("-", "0", "all"):
        await update_user_filter(fid, price_min_eur=None, price_max_eur=None)
        await state.clear()
        await message.answer(t("edit_price_cleared", lang), parse_mode="HTML")
        await show_filter_details(message, fid, lang)
        return

    nums = [float(p) for p in text.replace(",", " ").split() if p.replace(".", "", 1).isdigit()]
    if not nums:
        await message.answer(t("edit_price_invalid", lang), parse_mode="HTML")
        return

    if len(nums) == 1:
        p_min, p_max = None, nums[0]
    else:
        p_min, p_max = nums[0], nums[1]
        if p_min > p_max:
            p_min, p_max = p_max, p_min

    await update_user_filter(fid, price_min_eur=p_min, price_max_eur=p_max)
    await state.clear()
    price_label = f"{p_min:,.0f} € - {p_max:,.0f} €" if p_min else f"≤ {p_max:,.0f} €"
    await message.answer(t("edit_price_success", lang, price=price_label), parse_mode="HTML")
    await show_filter_details(message, fid, lang)


@router.callback_query(F.data.startswith("fedit_mileage_"))
async def callback_fedit_mileage(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Start mileage edit flow."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("fedit_mileage_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer(t("filter_not_found", lang), show_alert=True)
        return

    await state.update_data(edit_filter_id=fid)
    await state.set_state(FilterEditState.waiting_for_mileage)

    prompt = t("edit_mileage_prompt", lang)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


@router.message(FilterEditState.waiting_for_mileage)
async def process_fedit_mileage(message: Message, state: FSMContext, lang: str = "en"):
    """Handle new mileage input."""
    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer(t("edit_cancelled", lang), reply_markup=get_main_menu_keyboard(lang))
        return

    data = await state.get_data()
    fid = data.get("edit_filter_id")
    if not fid:
        await state.clear()
        return

    if text in ("-", "0", "all"):
        await update_user_filter(fid, mileage_max=None)
        await state.clear()
        await message.answer(t("edit_mileage_cleared", lang), parse_mode="HTML")
        await show_filter_details(message, fid, lang)
        return

    digits = [int(p) for p in text.replace(",", "").replace(" ", "").split() if p.isdigit()]
    if not digits:
        await message.answer(t("edit_mileage_invalid", lang), parse_mode="HTML")
        return

    m_max = digits[0]
    await update_user_filter(fid, mileage_max=m_max)
    await state.clear()
    await message.answer(t("edit_mileage_success", lang, mileage=f"{m_max:,}".replace(",", " ")), parse_mode="HTML")
    await show_filter_details(message, fid, lang)


@router.callback_query(F.data.startswith("topic_toggle_"))
async def callback_topic_toggle(callback: CallbackQuery, lang: str = "en"):
    """Toggle a filter between active and paused."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("topic_toggle_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer(t("filter_not_found", lang), show_alert=True)
        return

    new_st = await toggle_filter_status(fid)
    st_text = t("filter_toggle_activated", lang) if new_st == 1 else t("filter_toggle_paused", lang)
    await callback.answer(t("filter_toggle_alert", lang, fid=fid, status=st_text))
    await show_filter_details(callback, fid, lang)


@router.callback_query(F.data.startswith("topic_del_prompt_"))
async def callback_topic_delete_prompt(callback: CallbackQuery, lang: str = "en"):
    """Confirm filter deletion."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("topic_del_prompt_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer(t("filter_not_found", lang), show_alert=True)
        return

    text = t("confirm_delete_filter", lang, make_model=f"{flt['make']} {flt.get('model') or ''}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_yes_delete", lang), callback_data=f"topic_del_confirm_{fid}"),
            InlineKeyboardButton(text=t("btn_no_cancel", lang), callback_data=f"filter_details_{fid}")
        ]
    ])

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("topic_del_confirm_"))
async def callback_topic_delete_confirm(callback: CallbackQuery, bot: Bot, lang: str = "en"):
    """Execute filter deletion from DB."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    fid = int(callback.data.replace("topic_del_confirm_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer(t("filter_not_found", lang), show_alert=True)
        return

    topic_id = flt.get("topic_id")
    if topic_id and topic_id > 0:
        try:
            await bot.close_forum_topic(chat_id=settings.GROUP_CHAT_ID, message_thread_id=topic_id)
        except Exception as e:
            logger.debug(f"Could not close forum topic {topic_id}: {e}")

    await delete_filter(fid)
    
    if isinstance(callback.message, Message):
        await callback.message.edit_text(t("filter_deleted_msg", lang), reply_markup=get_main_menu_keyboard(lang), parse_mode="HTML")
    await callback.answer(t("filter_deleted_alert", lang))


# ==============================================================================
# /STATS & /HELP
# ==============================================================================

@router.message(Command("stats"))
@router.callback_query(F.data == "btn_stats")
async def cmd_stats(event: Message | CallbackQuery, lang: str = "en"):
    """Display real-time statistics."""
    stats = await get_database_stats()
    text = t(
        "stats_template",
        lang,
        total_users=stats.get("total_users", 0),
        active_filters=stats.get("active_filters", 0),
        total_topics=stats.get("total_topics", 0),
        seen_listings=f"{stats.get('seen_listings', 0):,}".replace(",", " "),
        cached_benchmarks=f"{stats.get('cached_benchmarks', 0):,}".replace(",", " ")
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="btn_main_menu")]
    ])

    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("help"))
@router.callback_query(F.data == "btn_help")
async def cmd_help(event: Message | CallbackQuery, lang: str = "en"):
    """Display detailed help guide."""
    help_text = (
        "📖 <b>Pan-European Arbitrage System & Rules</b>\n\n"
        "1️⃣ <b>Filter Setup & Dynamic Topic:</b>\n"
        "Use <code>/newfilter</code> to choose country, make, model, year range, budget, mileage, and fuel type. "
        "The bot will automatically create a dedicated topic in the group and pin filter parameters as the first message.\n\n"
        "2️⃣ <b>Multi-Tier Live Scanner:</b>\n"
        "• Tier 1 (Simple HTML): SS.com (LV), Bazos.sk (SK), Bazos.cz (CZ)\n"
        "• Tier 2 (Moderate Protection): Autoplius.lt (LT), Sauto.cz (CZ)\n"
        "• Tier 3 (Major Western Markets): Mobile.de (DE), Kleinanzeigen.de (DE), Leboncoin.fr (FR), Subito.it (IT)\n\n"
        "3️⃣ <b>Net Arbitrage Calculation:</b>\n"
        "<code>Net Profit = Otomoto Price - (Purchase + Logistics + Excise + Registration)</code>\n"
        "• Logistics: Baltics ~400€, Czech/Slovakia ~300€, Germany ~500€, Western Europe ~850€\n"
        "• Akcyza (Excise): Engine ≤2.0L 3.1%, >2.0L 18.6%, Hybrid 1.55%, EV 0%\n"
        "• Registration/Inspection: 300 PLN (~70€)\n\n"
        "4️⃣ <b>🔥 Hot Deals:</b>\n"
        "If net profit is <b>≥1 500 €</b> or <b>≥15% below market price</b>, the listing is instantly forwarded to <code>#HotDeals</code>!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="btn_main_menu")]
    ])

    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await event.message.edit_text(help_text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(help_text, reply_markup=kb, parse_mode="HTML")
