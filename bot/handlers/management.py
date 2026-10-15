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
from bot.locales.texts import t, LANGUAGES
from bot.middlewares.i18n import set_cached_user_language

logger = logging.getLogger(__name__)

router = Router()


class FilterEditState(StatesGroup):
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_price = State()
    waiting_for_mileage = State()


DEAL_TYPE_LABELS = {
    "all": "💎 Bütün Fürsətlər",
    "top_profit": "🚀 Ən Yüksək Marja (>25%)",
    "new_cars": "⚡ Təzə Modellər (2018+)",
    "low_mileage": "🛣️ Az Probeg (<100k km)",
    "low_mileage_cheap": "🌟 Az Probeg + Çox Ucuz"
}


def format_limit_label(limit: int) -> str:
    if not limit or limit <= 0:
        return "♾️ Limitsiz"
    return f"{limit} elan / gün"


def format_age_label(age_hours: int) -> str:
    if not age_hours or age_hours <= 0:
        return "⚡ Real-Time (Canlı)"
    elif age_hours == 1:
        return "⏱️ Son 1 Saat"
    elif age_hours == 24:
        return "📅 Son 24 Saat (1 gün)"
    elif age_hours == 168:
        return "🗓️ Son 7 Gün (1 həftə)"
    elif age_hours == 720:
        return "🗓️ Son 30 Gün (1 ay)"
    return f"🌐 {age_hours}h / Bütün"


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Build language selection inline buttons with Azerbaijani, English, Polish, Russian."""
    buttons = [
        [
            InlineKeyboardButton(text="🇦🇿 Azərbaycan", callback_data="set_lang_az"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")
        ],
        [
            InlineKeyboardButton(text="🇵🇱 Polski", callback_data="set_lang_pl"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_keyboard(lang: str, hot_deals_enabled: bool = True, notify_settings: Optional[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
    """Build settings keyboard with language selection, notification destination, Hot Deals toggle, detailed preferences, and main menu."""
    hd_btn_text = t("btn_hot_deals_on", lang) if hot_deals_enabled else t("btn_hot_deals_off", lang)
    buttons = [
        [
            InlineKeyboardButton(text="🇦🇿 Azərbaycan", callback_data="set_lang_az"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")
        ],
        [
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
                InlineKeyboardButton(text=f"👥 Qrupa Keçir ({group_title or 'Topics'})", callback_data="btn_switch_to_group")
            ])
            buttons.append([
                InlineKeyboardButton(text="🔄 Qrupu Dəyiş / Yenisini Qoş", callback_data="btn_connect_group_info")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="👥 Şəxsi Qrupu Qoş (Topics Pro)", callback_data="btn_connect_group_info")
            ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🟢 Şəxsi Çata (DM) Keçir", callback_data="btn_switch_to_dm")
        ])
        buttons.append([
            InlineKeyboardButton(text="🔄 Qrupu Dəyiş / Ayır", callback_data="btn_connect_group_info")
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
    deal_type_str = DEAL_TYPE_LABELS.get(hd.get("deal_type", "all"), "💎 Bütün")
    min_year_str = f"{hd.get('min_year', 2012)}+" if hd.get("min_year", 0) > 0 else t("any_year", lang)
    max_price_str = f"≤ {int(hd.get('max_price_eur', 0)):,} €".replace(",", " ") if hd.get("max_price_eur", 0) > 0 else t("unlimited_price", lang)
    max_mileage_str = f"≤ {int(hd.get('max_mileage', 0)):,} km".replace(",", " ") if hd.get("max_mileage", 0) > 0 else "♾️ Limitsiz"
    interval_str = format_interval_label(hd.get("interval_hours", 0), lang)

    return (
        f"🔥 <b>FƏRDİ HOT DEALS PARAMETRLƏRİ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Status:</b> {status_label}\n"
        f"• <b>Min. Xalis Qazanc:</b> ≥ {min_profit_str} €\n"
        f"• <b>Min. Xeyir Faizi:</b> ≥ {min_profit_pct}\n"
        f"• <b>Fokus Kateqoriyası:</b> {deal_type_str}\n"
        f"• <b>Min. İl:</b> {min_year_str}\n"
        f"• <b>Maks. Qiymət:</b> {max_price_str}\n"
        f"• <b>Maks. Yürüş:</b> {max_mileage_str}\n"
        f"• <b>Bildiriş Tezliyi:</b> {interval_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Dəyişmək istədiyiniz parametri seçin:"
    )


def build_hot_deals_dashboard_keyboard(hd: Dict[str, Any], lang: str) -> InlineKeyboardMarkup:
    """Build Hot Deals preferences dashboard buttons."""
    status_text = f"🔘 Status: {t('status_active', lang)}" if hd.get("enabled", True) else f"🔘 Status: {t('status_disabled', lang)}"
    min_profit_str = f"≥ {int(hd.get('min_profit_eur', 1500))} €"
    min_pct_str = f"≥ {int(hd.get('min_profit_percent', 15))}%"
    min_year_str = f"{hd.get('min_year', 2012)}+" if hd.get("min_year", 0) > 0 else t("any_year", lang)
    max_price_str = f"≤ {int(hd.get('max_price_eur', 0))} €" if hd.get("max_price_eur", 0) > 0 else t("unlimited_price", lang)
    deal_type_label = DEAL_TYPE_LABELS.get(hd.get("deal_type", "all"), "💎 Bütün")
    interval_str = format_interval_label(hd.get("interval_hours", 0), lang)

    buttons = [
        [
            InlineKeyboardButton(text=status_text, callback_data="hd_toggle_status")
        ],
        [
            InlineKeyboardButton(text=f"💰 Min Qazanc: {min_profit_str}", callback_data="hd_param_profit"),
            InlineKeyboardButton(text=f"📈 Qazanc Faizi: {min_pct_str}", callback_data="hd_param_pct")
        ],
        [
            InlineKeyboardButton(text=f"🎯 Fokus: {deal_type_label}", callback_data="hd_param_type")
        ],
        [
            InlineKeyboardButton(text=f"📅 İl: {min_year_str}", callback_data="hd_param_year"),
            InlineKeyboardButton(text=f"🏷️ Qiymət: {max_price_str}", callback_data="hd_param_price")
        ],
        [
            InlineKeyboardButton(text=f"🧭 Yürüş Limiti", callback_data="hd_param_mileage"),
            InlineKeyboardButton(text=f"⏱️ Tezlik: {interval_str}", callback_data="hd_param_interval")
        ],
        [
            InlineKeyboardButton(text="🔥 Hot Deals Hub", callback_data="btn_hot_deals_hub"),
            InlineKeyboardButton(text=t("btn_back_to_settings", lang), callback_data="btn_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build localized main menu buttons."""
    buttons = [
        [
            InlineKeyboardButton(text=t("btn_new_search", lang), callback_data="btn_new_search"),
            InlineKeyboardButton(text="📋 Filtrlərim", callback_data="btn_my_topics")
        ],
        [
            InlineKeyboardButton(text="🔥 Hot Deals Skaneri", callback_data="btn_hot_deals_hub"),
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
# /START & LANGUAGE SELECTION
# ==============================================================================

async def validate_group_for_bot(bot: Bot, chat_id: int) -> Tuple[bool, Optional[str]]:
    """Verify that group is a forum, bot is administrator, and has manage_topics & pin permissions."""
    try:
        chat = await bot.get_chat(chat_id)
        if not getattr(chat, "is_forum", False):
            return False, (
                "⚠️ <b>Bu qrupda 'Mövzular (Topics)' funksiyası bağlıdır.</b>\n\n"
                "Qrup tənzimləmələrinə girib 'Topics' (Mövzular) seçimini aktiv edin və yenidən <code>/connect</code> yazın."
            )

        bot_info = await bot.get_me()
        member = await bot.get_chat_member(chat_id, bot_info.id)
        if member.status != "administrator":
            return False, (
                "⚠️ <b>Mənə qrupda Administrator hüququ verilməyib.</b>\n\n"
                "Zəhmət olmasa məni qrupda admin edin və yenidən <code>/connect</code> yazın."
            )

        if not getattr(member, "can_manage_topics", False):
            return False, (
                "⚠️ <b>Mənim yeni Topic açmaq icazəm yoxdur.</b>\n\n"
                "Admin parametrlərində 'Manage Topics' (Mövzuları İdarə Etmək) icazəsini açın və yenidən <code>/connect</code> yazın."
            )

        if not getattr(member, "can_pin_messages", False):
            return False, (
                "⚠️ <b>Filtr məlumatını yuxarı bərkitmək üçün 'Pin Messages' icazəsini aktiv edin.</b>"
            )

        return True, None
    except Exception as e:
        return False, f"⚠️ Qrup yoxlanılarkən xəta baş verdi: {e}"


async def process_group_connection(message: Message, bot: Bot, user_id: int):
    """Link a validated group to user settings and notify user."""
    is_valid, error_msg = await validate_group_for_bot(bot, message.chat.id)
    if not is_valid:
        await message.answer(error_msg, parse_mode="HTML")
        return

    group_title = message.chat.title or "Şəxsi Qrup"
    await link_user_group(user_id, message.chat.id, group_title)

    await message.answer(
        f"✅ <b>Qrupunuz uğurla qoşuldu!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Qrup:</b> {group_title}\n"
        f"👤 <b>Sahib ID:</b> <code>{user_id}</code>\n\n"
        f"İndi yaratdığınız yeni axtarışlar üçün bu qrupda avtomatik xüsusi Topic-lər (Mövzular) açılacaq və elanlar birbaşa bura göndəriləcək.",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 <b>Şəxsi Qrupunuz Qoşuldu!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 <b>Qrup:</b> {group_title}\n"
                f"🔔 <b>Bildiriş Yeri:</b> Qrup (Topics) 👥\n\n"
                f"Bundan sonra yeni yaratdığınız axtarışlar üçün həmin qrupda avtomatik xüsusi Mövzular açılacaq.\n"
                f"İstədiyiniz vaxt Ayarlardan tək kliklə yenidən Şəxsi Çata keçə bilərsiniz."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(Command("connect"))
async def cmd_connect_group(message: Message, bot: Bot):
    """Handle /connect command inside a personal group."""
    if message.chat.type not in ["group", "supergroup"]:
        await message.answer("ℹ️ Bu əmr yalnız şəxsi superqrup daxilində işlədilir.")
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

    is_valid, error_msg = await validate_group_for_bot(bot, update.chat.id)
    if not is_valid:
        try:
            await bot.send_message(chat_id=update.chat.id, text=error_msg, parse_mode="HTML")
        except Exception:
            pass
        return

    group_title = update.chat.title or "Şəxsi Qrup"
    await link_user_group(user_id, update.chat.id, group_title)

    try:
        await bot.send_message(
            chat_id=update.chat.id,
            text=(
                f"✅ <b>Qrupunuz uğurla qoşuldu!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 <b>Qrup:</b> {group_title}\n"
                f"👤 <b>Sahib ID:</b> <code>{user_id}</code>\n\n"
                f"İndi yaratdığınız axtarışlar üçün bu qrupda avtomatik xüsusi Topic-lər (Mövzular) açılacaq və elanlar birbaşa bura göndəriləcək."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 <b>Şəxsi Qrupunuz Qoşuldu!</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 <b>Qrup:</b> {group_title}\n"
                f"🔔 <b>Bildiriş Yeri:</b> Qrup (Topics) 👥\n\n"
                f"Bundan sonra yeni yaratdığınız axtarışlar üçün həmin qrupda avtomatik xüsusi Mövzular açılacaq.\n"
                f"İstədiyiniz vaxt Ayarlardan tək kliklə yenidən Şəxsi Çata keçə bilərsiniz."
            ),
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
        await process_group_connection(message, bot=message.bot, user_id=target_uid)
        return

    user_id = message.from_user.id
    existing_lang = await get_user_language(user_id)

    if not existing_lang:
        # Prompt for language first
        await message.answer(
            t("select_language", "az"),
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
        target_lang = "az"

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
    current_lang_name = LANGUAGES.get(lang, "Azərbaycan")
    status_label = t("status_active", lang) if hot_deals_enabled else t("status_disabled", lang)
    dest_label = "Şəxsi Çat (DM) 🟢" if notify_settings.get("notification_target") == "dm" else f"Qrup 👥 ({notify_settings.get('connected_group_title') or 'Mövzular'})"
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

    current_lang_name = LANGUAGES.get(lang, "Azərbaycan")
    status_label = t("status_active", lang) if new_status else t("status_disabled", lang)
    dest_label = "Şəxsi Çat (DM) 🟢" if notify_settings.get("notification_target") == "dm" else f"Qrup 👥 ({notify_settings.get('connected_group_title') or 'Mövzular'})"
    text = t("settings_title", lang, current_lang=current_lang_name, notify_dest=dest_label, hot_deals_status=status_label)
    kb = get_settings_keyboard(lang, new_status, notify_settings)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(alert_msg, show_alert=True)


@router.callback_query(F.data == "btn_connect_group_info")
async def callback_connect_group_info(callback: CallbackQuery, lang: str = "en"):
    """Display deep linking guide to connect a personal supergroup."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    bot_info = await callback.bot.get_me()
    bot_user = bot_info.username or "dOOgagBot"
    deep_link = f"https://t.me/{bot_user}?startgroup=connect_{user_id}&admin=manage_topics+pin_messages"

    notify_settings = await get_user_notification_settings(user_id)
    connected_title = notify_settings.get("connected_group_title")

    text = (
        f"👥 <b>ŞƏXSİ QRUPUNUZUN QOŞULMASI (Topics Pro)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Elanların bir-birinə qarışmaması və hər avtomobil axtarışınızın ayrı <b>Topic-də (Mövzuda)</b> səliqəli toplanması üçün şəxsi qrupunuzu bota bağlaya bilərsiniz.\n\n"
        f"<b>Qoşulma Qaydası:</b>\n"
        f"1. Aşağıdakı düyməyə basaraq öz qrupunuzu seçin (və ya yeni qrup yaradın).\n"
        f"2. Qrupun tənzimləmələrində <b>Topics (Mövzular)</b> seçiminin açıq olduğundan əmin olun.\n"
        f"3. Botu qrupda <b>Admin</b> edin və <i>Manage Topics</i> icazəsini verin.\n"
        f"4. Bot qrupa daxil olan kimi avtomatik təsdiqlənəcək (və ya qrup daxilində <code>/connect</code> yazın)."
    )
    if connected_title:
        text += f"\n\n🔗 <b>Hazırda Qoşulu Qrup:</b> {connected_title}"

    buttons = [
        [
            InlineKeyboardButton(text="👥 Qrup Seç və Məni Əlavə Et", url=deep_link)
        ]
    ]
    if connected_title:
        buttons.append([
            InlineKeyboardButton(text="🔄 Qrupu Bağlantıdan Ayır", callback_data="btn_disconnect_group")
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
    await callback.answer("✅ Bildiriş yeri Şəxsi Çata (DM) dəyişdirildi!", show_alert=True)
    await cmd_settings(callback, lang)


@router.callback_query(F.data == "btn_switch_to_group")
async def callback_switch_to_group(callback: CallbackQuery, lang: str = "en"):
    """Switch notification destination to Personal Group (Topics)."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    await set_user_notification_target(user_id, "group")
    await callback.answer("✅ Bildiriş yeri Şəxsi Qrupa (Topics) dəyişdirildi!", show_alert=True)
    await cmd_settings(callback, lang)


@router.callback_query(F.data == "btn_disconnect_group")
async def callback_disconnect_group(callback: CallbackQuery, lang: str = "en"):
    """Disconnect linked group and revert destination to DM."""
    if not callback.from_user:
        await callback.answer()
        return
    user_id = callback.from_user.id
    await unlink_user_group(user_id)
    await callback.answer("✅ Şəxsi qrup ayrıldı. Bildirişlər şəxsi çatınıza yönləndirildi.", show_alert=True)
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
    text = "📈 <b>Minimum Xeyir / Marja Faizini Seçin:</b>\nYalnız hesablanmış xalis qazanc faizi bu həddə bərabər və ya yuxarı olan elanlar göndəriləcək:"
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
            InlineKeyboardButton(text="🔙 Hot Deals Parametrləri", callback_data="btn_hot_deals_menu")
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
    await callback.answer("✅ Qazanc faizi yeniləndi!")


@router.callback_query(F.data == "hd_param_type")
async def callback_hd_param_type(callback: CallbackQuery, lang: str = "en"):
    """Select Hot Deal focus category."""
    text = "🎯 <b>Hot Deals Fokus Kateqoriyasını Seçin:</b>\nHansı növ qaynar təkliflərə üstünlük verirsiniz?"
    buttons = [
        [InlineKeyboardButton(text="💎 Bütün Qaynar Fürsətlər", callback_data="hd_set_type_all")],
        [InlineKeyboardButton(text="🚀 Ən Yüksək Marja (>25%)", callback_data="hd_set_type_top_profit")],
        [InlineKeyboardButton(text="⚡ Ən Yeni Modellər (2018+)", callback_data="hd_set_type_new_cars")],
        [InlineKeyboardButton(text="🛣️ Çox Az Probeg (<100k km)", callback_data="hd_set_type_low_mileage")],
        [InlineKeyboardButton(text="🌟 Az Probeg + Çox Ucuz", callback_data="hd_set_type_low_mileage_cheap")],
        [InlineKeyboardButton(text="🔙 Hot Deals Parametrləri", callback_data="btn_hot_deals_menu")]
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
    await callback.answer("✅ Kateqoriya yeniləndi!")


@router.callback_query(F.data == "hd_param_mileage")
async def callback_hd_param_mileage(callback: CallbackQuery, lang: str = "en"):
    """Select max mileage for Hot Deals."""
    text = "🧭 <b>Maksimum Yürüş Həddini Seçin:</b>\nBu yürüşdən çox olan maşınlar Hot Deals-dan kənarlaşdırılacaq:"
    buttons = [
        [
            InlineKeyboardButton(text="♾️ Limitsiz", callback_data="hd_set_mileage_0"),
            InlineKeyboardButton(text="≤ 60 000 km", callback_data="hd_set_mileage_60000")
        ],
        [
            InlineKeyboardButton(text="≤ 100 000 km", callback_data="hd_set_mileage_100000"),
            InlineKeyboardButton(text="≤ 150 000 km", callback_data="hd_set_mileage_150000")
        ],
        [
            InlineKeyboardButton(text="🔙 Hot Deals Parametrləri", callback_data="btn_hot_deals_menu")
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
    await callback.answer("✅ Yürüş limiti yeniləndi!")


# ==============================================================================
# HOT DEALS HUB & INTERACTIVE DEAL BROWSER
# ==============================================================================

@router.message(Command("hotdeals"))
@router.callback_query(F.data == "btn_hot_deals_hub")
async def cmd_hot_deals_hub(event: Message | CallbackQuery, lang: str = "en"):
    """Dedicated Hot Deals & Pan-European Arbitrage Explorer Hub."""
    user_id = event.from_user.id if event.from_user else 0
    hd = await get_user_hot_deals_settings(user_id)
    status_label = "Aktiv 🟢" if hd.get("enabled", True) else "Deaktiv ❌"
    min_profit_str = f"{int(hd.get('min_profit_eur', 1500)):,}".replace(",", " ")
    min_pct_str = f"{int(hd.get('min_profit_percent', 15))}%"
    deal_type_str = DEAL_TYPE_LABELS.get(hd.get("deal_type", "all"), "💎 Bütün Fürsətlər")
    min_year_str = f"{hd.get('min_year', 2012)}+" if hd.get("min_year", 0) > 0 else "İstənilən"
    max_price_str = f"≤ {int(hd.get('max_price_eur', 0)):,} €".replace(",", " ") if hd.get("max_price_eur", 0) > 0 else "Limitsiz ♾️"

    text = (
        f"🔥 <b>HOT DEALS & ARBİTRAJ MERKEZİ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Avropanın ən böyük avtomobil bazarlarında qiyməti Polşa (Otomoto) bazarından kəskin ucuz olan yüksək qazanclı avtomobillər.\n\n"
        f"• <b>Şəxsi Çat Bildirişləri:</b> {status_label}\n"
        f"• <b>Min. Xalis Qazanc:</b> ≥ {min_profit_str} €\n"
        f"• <b>Min. Qazanc Faizi:</b> ≥ {min_pct_str}\n"
        f"• <b>Fokus Kateqoriyası:</b> {deal_type_str}\n"
        f"• <b>İl Həddi:</b> {min_year_str} | <b>Büdcə:</b> {max_price_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Aşağıdakı menyudan dərhal ən son tapılmış qaynar təkliflərə baxa və ya fərdi filtrlərinizi tənzimləyə bilərsiniz:</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Canlı Fürsətlərə Bax (Top 10)", callback_data="hd_browse_0")
        ],
        [
            InlineKeyboardButton(text="⚙️ Fərdi Hot Deals Parametrləri", callback_data="btn_hot_deals_menu"),
            InlineKeyboardButton(text="🔘 Bildirişlər", callback_data="hd_toggle_status")
        ],
        [
            InlineKeyboardButton(text="🏠 Əsas Menyu", callback_data="btn_main_menu")
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
        msg = (
            "ℹ️ <b>Hazırda bu parametrlərə uyğun qaynar təklif tapılmadı.</b>\n\n"
            "Hot Deals parametrlərindən minimum qazanc və ya faiz həddini aşağı salaraq daha çox təklif görə bilərsiniz."
        )
        buttons = [
            [InlineKeyboardButton(text="⚙️ Parametrləri Dəyiş", callback_data="btn_hot_deals_menu")],
            [InlineKeyboardButton(text="🔙 Hot Deals Hub", callback_data="btn_hot_deals_hub")]
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

    deal_card = (
        f"🔥 <b>QAYNAR FÜRSƏT ({page + 1}/{total})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚗 <b>{title}</b>\n"
        f"• <b>Mənbə:</b> {country} ({platform})\n"
        f"• <b>İl:</b> {year} | <b>Yürüş:</b> {mileage}\n\n"
        f"💶 <b>Alış Qiyməti:</b> <b>{price_eur:,.0f} €</b>\n"
        f"🇵🇱 <b>Polşa Bazar Qiyməti (Otomoto):</b> <b>~{bench_eur:,.0f} €</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Təxmini Xalis Qazanc:</b> <b>+{profit_eur:,.0f} €</b>\n"
        f"📈 <b>Xeyir Marjası:</b> <b>+{profit_pct}%</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Əvvəlki", callback_data=f"hd_browse_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📌 {page + 1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav_row.append(InlineKeyboardButton(text="Sonrakı ➡️", callback_data=f"hd_browse_{page + 1}"))

    buttons = [
        nav_row,
        [InlineKeyboardButton(text="🔗 Orijinal Elana Bax", url=url)],
        [
            InlineKeyboardButton(text="⚙️ Parametrlər", callback_data="btn_hot_deals_menu"),
            InlineKeyboardButton(text="🔙 Hot Deals Hub", callback_data="btn_hot_deals_hub")
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
    if not event.from_user:
        return
    user_id = event.from_user.id
    filters = await get_user_filters(user_id)

    if not filters:
        no_topics_text = (
            "ℹ️ <b>Sizin hələlik aktiv axtarış filtriniz yoxdur.</b>\n\n"
            "Avropa bazarlarını canlı izləmək üçün aşağıdakı düymə ilə yeni axtarış qurun."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yeni Axtarış Əlavə Et", callback_data="btn_new_search")],
            [InlineKeyboardButton(text="🏠 Əsas Menyu", callback_data="btn_main_menu")]
        ])
        if isinstance(event, CallbackQuery):
            if isinstance(event.message, Message):
                await event.message.edit_text(no_topics_text, reply_markup=kb, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(no_topics_text, reply_markup=kb, parse_mode="HTML")
        return

    # Build topic list message
    lines = [
        "📋 <b>ŞƏXSİ AXTARIŞ FİLTRLƏRİNİZ:</b>\n"
        "<i>Tənzimləmək, redaktə etmək və ya elanları gətirmək üçün filtrin üzərinə toxunun:</i>\n"
    ]
    for idx, f in enumerate(filters, start=1):
        status_str = "Aktiv 🟢" if f["is_active"] == 1 else "Pauzada ⏸️"
        make = f["make"]
        model = f["model"] or "Bütün"
        y_min, y_max = f.get("year_min"), f.get("year_max")
        price_max = f.get("price_max_eur")

        details = []
        if y_min and y_max:
            details.append(f"{y_min}-{y_max}")
        elif y_min:
            details.append(f">{y_min}")
        if price_max:
            details.append(f"<{price_max:,.0f}€".replace(",", ""))

        details_str = f" ({', '.join(details)})" if details else ""
        lines.append(f"<b>{idx}.</b> 🚙 <b>{make} {model}</b>{details_str} — [{status_str}]")

    header_text = "\n".join(lines)
    
    # We display control keyboards for each filter
    buttons = []
    for f in filters[:10]:
        fid = f["id"]
        status_action = "⏸️ Dayandır" if f["is_active"] == 1 else "▶️ Aktiv et"
        make = f["make"]
        model = f["model"] or ""
        row = [
            InlineKeyboardButton(text=f"⚙️ #{fid} {make} {model}".strip(), callback_data=f"filter_details_{fid}"),
            InlineKeyboardButton(text=status_action, callback_data=f"topic_toggle_{fid}")
        ]
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="➕ Yeni Axtarış Əlavə Et", callback_data="btn_new_search"),
        InlineKeyboardButton(text="🏠 Əsas Menyu", callback_data="btn_main_menu")
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await event.message.edit_text(header_text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(header_text, reply_markup=kb, parse_mode="HTML")


async def show_filter_details(event: Message | CallbackQuery, filter_id: int, lang: str = "en"):
    """Render full filter settings, editing dashboard, and live fetch action."""
    flt = await get_filter_by_id(filter_id)
    if not flt:
        return
    fid = flt["id"]
    make = flt["make"]
    model = flt["model"] or "Bütün Modellər"
    y_min = flt.get("year_min")
    y_max = flt.get("year_max")
    year_str = f"{y_min} - {y_max}" if (y_min and y_max) else (f">{y_min}" if y_min else (f"<{y_max}" if y_max else "İstənilən"))
    
    p_min = flt.get("price_min_eur")
    p_max = flt.get("price_max_eur")
    price_str = f"{p_min:,.0f} € - {p_max:,.0f} €".replace(",", " ") if (p_min and p_max) else (f"≤ {p_max:,.0f} €" if p_max else "Limitsiz")
    
    mileage_max = flt.get("mileage_max")
    mileage_str = f"≤ {mileage_max:,} km".replace(",", " ") if mileage_max else "Limitsiz"
    
    limit_val = flt.get("daily_alert_limit", 0) or 0
    limit_label = format_limit_label(limit_val)
    sent_today = flt.get("alerts_sent_today", 0) or 0
    
    age_val = flt.get("listing_age_hours", 0) or 0
    age_label = format_age_label(age_val)
    
    status_str = "Aktiv 🟢" if flt["is_active"] == 1 else "Pauzada ⏸️"
    status_action = "⏸️ Dayandır" if flt["is_active"] == 1 else "▶️ Aktiv et"

    fuel_str = flt.get("fuel_type", "all").capitalize()
    trans_str = flt.get("transmission", "all").capitalize()
    country_str = flt.get("target_country", "ALL")

    text = (
        f"🛠 <b>FİLTR PARAMETRLƏRİ: #{fid}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚙 <b>Avtomobil:</b> {make} {model}\n"
        f"📅 <b>İl Aralığı:</b> {year_str}\n"
        f"💰 <b>Qiymət Büdcəsi:</b> {price_str}\n"
        f"🧭 <b>Maks. Yürüş:</b> {mileage_str}\n"
        f"⛽ <b>Yanacaq:</b> {fuel_str} | <b>Korobka:</b> {trans_str}\n"
        f"🌍 <b>Bazar / Ölkə:</b> {country_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Gündəlik Limit:</b> {limit_label} (Bugün göndərildi: {sent_today})\n"
        f"⏱️ <b>Elan Vaxt Aralığı:</b> {age_label}\n"
        f"🔘 <b>Status:</b> {status_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Parametrləri redaktə etmək və ya elan gətirmək üçün seçin:</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚘 Marka / Model Dəyiş", callback_data=f"fedit_model_{fid}")
        ],
        [
            InlineKeyboardButton(text="📅 İl Aralığı", callback_data=f"fedit_year_{fid}"),
            InlineKeyboardButton(text="💰 Qiymət Büdcəsi", callback_data=f"fedit_price_{fid}")
        ],
        [
            InlineKeyboardButton(text="🧭 Maks. Yürüş", callback_data=f"fedit_mileage_{fid}"),
            InlineKeyboardButton(text="📊 Gündəlik Limit", callback_data=f"fedit_limit_{fid}")
        ],
        [
            InlineKeyboardButton(text="⏱️ Vaxt Aralığı (Keçmiş/Yeni)", callback_data=f"fedit_age_{fid}")
        ],
        [
            InlineKeyboardButton(text="📥 Mövcud Elanları İndi Gətir", callback_data=f"filter_fetch_now_{fid}")
        ],
        [
            InlineKeyboardButton(text=status_action, callback_data=f"topic_toggle_{fid}"),
            InlineKeyboardButton(text="🗑️ Filtri Sil", callback_data=f"topic_del_prompt_{fid}")
        ],
        [
            InlineKeyboardButton(text="🔙 Filtrlərim Siyahısı", callback_data="btn_my_topics")
        ]
    ])

    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


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
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer("Filtr tapılmadı", show_alert=True)
        return

    await callback.answer("🔍 Mövcud elanlar axtarılır...", show_alert=False)
    matches = await search_seen_listings_for_filter(flt, limit=5)
    if not matches:
        await callback.message.answer(
            f"ℹ️ <b>Bazada hələlik bu parametrlərə uyğun keçmiş elan tapılmadı:</b>\n"
            f"🚙 <b>{flt['make']} {flt.get('model') or ''}</b>\n\n"
            f"<i>Avropa skaneri 24/7 aktivdir. Uyğun yeni elan dərc olunan kimi dərhal sizin bu şəxsi çatınıza göndəriləcək!</i>",
            parse_mode="HTML"
        )
        return

    await callback.message.answer(
        f"✅ <b>Bazada tapılan {len(matches)} ən son elan göndərilir:</b>",
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

        card_text = (
            f"🚗 <b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Mənbə:</b> {country} ({platform})\n"
            f"• <b>İl:</b> {year} | <b>Yürüş:</b> {mileage}\n"
            f"• <b>Qiymət:</b> <b>{price:,.0f} €</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href='{url}'>Elana Keçid (Orijinal Elan)</a>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Elana Bax", url=url)]
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
    fid = int(callback.data.replace("fedit_limit_", ""))
    text = "📊 <b>Gündəlik Bildiriş Limitini Seçin:</b>\nBu filtr üzrə gün ərzində şəxsi çatınıza ən çox neçə elan göndərilə bilər?"
    buttons = [
        [
            InlineKeyboardButton(text="♾️ Limitsiz", callback_data=f"flim_set_{fid}_0"),
            InlineKeyboardButton(text="🔟 10 elan / gün", callback_data=f"flim_set_{fid}_10")
        ],
        [
            InlineKeyboardButton(text="2️⃣5️⃣ 25 elan / gün", callback_data=f"flim_set_{fid}_25"),
            InlineKeyboardButton(text="5️⃣0️⃣ 50 elan / gün", callback_data=f"flim_set_{fid}_50")
        ],
        [
            InlineKeyboardButton(text="🔙 Geri", callback_data=f"filter_details_{fid}")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("flim_set_"))
async def callback_flim_set(callback: CallbackQuery, lang: str = "en"):
    """Save daily limit and return to filter details."""
    parts = callback.data.split("_")
    fid = int(parts[2])
    val = int(parts[3])
    await update_user_filter(fid, daily_alert_limit=val)
    await callback.answer("✅ Gündəlik limit yeniləndi!")
    await show_filter_details(callback, fid, lang)


@router.callback_query(F.data.startswith("fedit_age_"))
async def callback_fedit_age(callback: CallbackQuery, lang: str = "en"):
    """Select listing freshness / age window."""
    fid = int(callback.data.replace("fedit_age_", ""))
    text = (
        "⏱️ <b>Elan Vaxt Aralığını Seçin:</b>\n"
        "Skaner yalnız bu vaxt ərzində çıxan elanları çatdırsın:"
    )
    buttons = [
        [
            InlineKeyboardButton(text="⚡ Real-Time (Yalnız Canlı)", callback_data=f"fage_set_{fid}_0"),
            InlineKeyboardButton(text="⏱️ Son 1 Saat", callback_data=f"fage_set_{fid}_1")
        ],
        [
            InlineKeyboardButton(text="📅 Son 24 Saat (1 gün)", callback_data=f"fage_set_{fid}_24"),
            InlineKeyboardButton(text="🗓️ Son 7 Gün (1 həftə)", callback_data=f"fage_set_{fid}_168")
        ],
        [
            InlineKeyboardButton(text="🗓️ Son 30 Gün (1 ay)", callback_data=f"fage_set_{fid}_720"),
            InlineKeyboardButton(text="🌐 Bütün Mövcud Elanlar", callback_data=f"fage_set_{fid}_99999")
        ],
        [
            InlineKeyboardButton(text="🔙 Geri", callback_data=f"filter_details_{fid}")
        ]
    ]
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("fage_set_"))
async def callback_fage_set(callback: CallbackQuery, lang: str = "en"):
    """Save listing age window and return to filter details."""
    parts = callback.data.split("_")
    fid = int(parts[2])
    val = int(parts[3])
    await update_user_filter(fid, listing_age_hours=val)
    await callback.answer("✅ Vaxt aralığı yeniləndi!")
    await show_filter_details(callback, fid, lang)


@router.callback_query(F.data.startswith("fedit_model_"))
async def callback_fedit_model(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Start model edit flow."""
    fid = int(callback.data.replace("fedit_model_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer("Filtr tapılmadı", show_alert=True)
        return

    await state.update_data(edit_filter_id=fid)
    await state.set_state(FilterEditState.waiting_for_model)

    prompt = (
        f"🚘 <b>Model və ya Marka Dəyişdirilməsi:</b>\n\n"
        f"Hazırkı axtarış: <b>{flt['make']} {flt.get('model') or ''}</b>\n\n"
        f"Yeni modeli yazın (məsələn: <code>Auris</code>, <code>Prius</code>, <code>X5</code>, <code>Passat</code>).\n"
        f"Həm markanı, həm də modeli dəyişmək üçün birlikdə yazın (məsələn: <code>Toyota Auris</code> və ya <code>BMW 520</code>).\n"
        f"Bütün modelləri seçmək üçün <code>-</code> yazın.\n\n"
        f"<i>Ləğv etmək üçün /cancel yazın.</i>"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


@router.message(FilterEditState.waiting_for_model)
async def process_fedit_model(message: Message, state: FSMContext, lang: str = "en"):
    """Handle new model input and update filter."""
    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Dəyişiklik ləğv edildi.", reply_markup=get_main_menu_keyboard(lang))
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

    if text in ("-", "all", "bütün"):
        await update_user_filter(fid, model="")
        new_label = f"{flt['make']} (Bütün Modellər)"
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
    await message.answer(f"✅ Filtr uğurla yeniləndi: <b>{new_label}</b>", parse_mode="HTML")
    await show_filter_details(message, fid, lang)


@router.callback_query(F.data.startswith("fedit_year_"))
async def callback_fedit_year(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Start year range edit flow."""
    fid = int(callback.data.replace("fedit_year_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer("Filtr tapılmadı", show_alert=True)
        return

    await state.update_data(edit_filter_id=fid)
    await state.set_state(FilterEditState.waiting_for_year)

    prompt = (
        f"📅 <b>İl Aralığını Daxil Edin:</b>\n\n"
        f"Məsələn: <code>2016 2023</code> (min və max il) və ya yalnız minimum il üçün <code>2015</code> yazın.\n"
        f"İl məhdudiyyətini silmək üçün <code>-</code> yazın.\n\n"
        f"<i>Ləğv etmək üçün /cancel yazın.</i>"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


@router.message(FilterEditState.waiting_for_year)
async def process_fedit_year(message: Message, state: FSMContext, lang: str = "en"):
    """Handle new year range input."""
    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Dəyişiklik ləğv edildi.", reply_markup=get_main_menu_keyboard(lang))
        return

    data = await state.get_data()
    fid = data.get("edit_filter_id")
    if not fid:
        await state.clear()
        return

    if text in ("-", "0", "all"):
        await update_user_filter(fid, year_min=None, year_max=None)
        await state.clear()
        await message.answer("✅ İl məhdudiyyəti silindi.", parse_mode="HTML")
        await show_filter_details(message, fid, lang)
        return

    parts = [int(p) for p in text.split() if p.isdigit()]
    if not parts:
        await message.answer("⚠️ Zəhmət olmasa düzgün il daxil edin (məs: <code>2015</code> və ya <code>2015 2022</code>):", parse_mode="HTML")
        return

    y_min = parts[0]
    y_max = parts[1] if len(parts) > 1 else None
    if y_max and y_min > y_max:
        y_min, y_max = y_max, y_min

    await update_user_filter(fid, year_min=y_min, year_max=y_max)
    await state.clear()
    await message.answer(f"✅ İl aralığı yeniləndi: <b>{y_min}{' - ' + str(y_max) if y_max else '+'}</b>", parse_mode="HTML")
    await show_filter_details(message, fid, lang)


@router.callback_query(F.data.startswith("fedit_price_"))
async def callback_fedit_price(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Start price range edit flow."""
    fid = int(callback.data.replace("fedit_price_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer("Filtr tapılmadı", show_alert=True)
        return

    await state.update_data(edit_filter_id=fid)
    await state.set_state(FilterEditState.waiting_for_price)

    prompt = (
        f"💰 <b>Qiymət Büdcəsini Daxil Edin (EUR):</b>\n\n"
        f"Məsələn: <code>4000 9000</code> (min və max) və ya yalnız maksimum büdcə üçün <code>9000</code> yazın.\n"
        f"Məhdudiyyəti silmək üçün <code>-</code> yazın.\n\n"
        f"<i>Ləğv etmək üçün /cancel yazın.</i>"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


@router.message(FilterEditState.waiting_for_price)
async def process_fedit_price(message: Message, state: FSMContext, lang: str = "en"):
    """Handle new price input."""
    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Dəyişiklik ləğv edildi.", reply_markup=get_main_menu_keyboard(lang))
        return

    data = await state.get_data()
    fid = data.get("edit_filter_id")
    if not fid:
        await state.clear()
        return

    if text in ("-", "0", "all"):
        await update_user_filter(fid, price_min_eur=None, price_max_eur=None)
        await state.clear()
        await message.answer("✅ Qiymət məhdudiyyəti silindi.", parse_mode="HTML")
        await show_filter_details(message, fid, lang)
        return

    nums = [float(p) for p in text.replace(",", " ").split() if p.replace(".", "", 1).isdigit()]
    if not nums:
        await message.answer("⚠️ Zəhmət olmasa düzgün qiymət daxil edin (məs: <code>5000 12000</code>):", parse_mode="HTML")
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
    await message.answer(f"✅ Qiymət büdcəsi yeniləndi: <b>{price_label}</b>", parse_mode="HTML")
    await show_filter_details(message, fid, lang)


@router.callback_query(F.data.startswith("fedit_mileage_"))
async def callback_fedit_mileage(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Start mileage edit flow."""
    fid = int(callback.data.replace("fedit_mileage_", ""))
    flt = await get_filter_by_id(fid)
    if not flt or flt["user_id"] != callback.from_user.id:
        await callback.answer("Filtr tapılmadı", show_alert=True)
        return

    await state.update_data(edit_filter_id=fid)
    await state.set_state(FilterEditState.waiting_for_mileage)

    prompt = (
        f"🧭 <b>Maksimum Yürüşü Daxil Edin (km):</b>\n\n"
        f"Məsələn: <code>150000</code> və ya <code>180000</code>.\n"
        f"Məhdudiyyəti silmək üçün <code>-</code> yazın.\n\n"
        f"<i>Ləğv etmək üçün /cancel yazın.</i>"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


@router.message(FilterEditState.waiting_for_mileage)
async def process_fedit_mileage(message: Message, state: FSMContext, lang: str = "en"):
    """Handle new mileage input."""
    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Dəyişiklik ləğv edildi.", reply_markup=get_main_menu_keyboard(lang))
        return

    data = await state.get_data()
    fid = data.get("edit_filter_id")
    if not fid:
        await state.clear()
        return

    if text in ("-", "0", "all"):
        await update_user_filter(fid, mileage_max=None)
        await state.clear()
        await message.answer("✅ Yürüş məhdudiyyəti silindi.", parse_mode="HTML")
        await show_filter_details(message, fid, lang)
        return

    digits = [int(p) for p in text.replace(",", "").replace(" ", "").split() if p.isdigit()]
    if not digits:
        await message.answer("⚠️ Zəhmət olmasa rəqəm daxil edin (məs: <code>150000</code>):", parse_mode="HTML")
        return

    m_max = digits[0]
    await update_user_filter(fid, mileage_max=m_max)
    await state.clear()
    await message.answer(f"✅ Maksimum yürüş yeniləndi: <b>{m_max:,} km</b>", parse_mode="HTML")
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
        await callback.answer("Filtr tapılmadı", show_alert=True)
        return

    new_st = await toggle_filter_status(fid)
    st_text = "aktivləşdirildi ▶️" if new_st == 1 else "dayandırıldı ⏸️"
    await callback.answer(f"Filtr #{fid} {st_text}!")
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
        await callback.answer("Filtr tapılmadı", show_alert=True)
        return

    text = f"⚠️ <b>Bu axtarış filtrini silmək istədiyinizə əminsiniz?</b>\n\n🚙 <b>{flt['make']} {flt.get('model') or ''}</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Bəli, Sil", callback_data=f"topic_del_confirm_{fid}"),
            InlineKeyboardButton(text="❌ Xeyr, Ləğv et", callback_data=f"filter_details_{fid}")
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
        await callback.answer("Filtr tapılmadı", show_alert=True)
        return

    topic_id = flt.get("topic_id")
    if topic_id and topic_id > 0:
        try:
            await bot.close_forum_topic(chat_id=settings.GROUP_CHAT_ID, message_thread_id=topic_id)
        except Exception as e:
            logger.debug(f"Could not close forum topic {topic_id}: {e}")

    await delete_filter(fid)
    
    if isinstance(callback.message, Message):
        await callback.message.edit_text("🗑 <b>Filtr uğurla silindi.</b>", reply_markup=get_main_menu_keyboard(lang), parse_mode="HTML")
    await callback.answer("Filtr silindi!")


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
