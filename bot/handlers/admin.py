import sys
from pathlib import Path
import logging
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aiogram import Router, F, Bot  # type: ignore
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton  # type: ignore
from aiogram.fsm.context import FSMContext  # type: ignore
from aiogram.fsm.state import State, StatesGroup  # type: ignore
from aiogram.filters import Command  # type: ignore

from config.settings import settings
from database.queries import (
    get_ad_settings,
    update_ad_settings,
    get_database_stats
)
from bot.views.listing_card import set_cached_ad_settings
from engine.broadcaster import broadcast_engine

logger = logging.getLogger(__name__)

router = Router()


class AdminMonetizationStates(StatesGroup):
    waiting_redirect_url = State()
    waiting_sponsor_text = State()
    waiting_sponsor_button = State()


class AdminBroadcastStates(StatesGroup):
    waiting_content = State()
    waiting_target = State()


def is_admin(user_id: Optional[int]) -> bool:
    """Check if Telegram user is authorized in ADMIN_USER_IDS."""
    if user_id is None:
        return False
    admin_ids = settings.ADMIN_USER_IDS
    if not admin_ids:
        # If no admin IDs are configured, fallback to False for security
        return False
    return user_id in admin_ids


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Build root admin menu keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="⚙️ Monetization Settings", callback_data="admin_monetization"),
            InlineKeyboardButton(text="📊 System Statistics", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast Campaign", callback_data="admin_broadcast_start")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def build_monetization_text_and_keyboard() -> tuple[str, InlineKeyboardMarkup]:
    """Render monetization configuration view and buttons."""
    ad_conf = await get_ad_settings()
    # Synchronize cache
    set_cached_ad_settings(ad_conf)

    is_redirect = "Active 🟢" if ad_conf.get("is_redirect_enabled") else "Disabled 🔴"
    base_url = ad_conf.get("redirect_base_url") or "<i>Not configured</i>"
    s_text = ad_conf.get("sponsor_text") or "<i>Not configured</i>"
    s_name = ad_conf.get("sponsor_button_name") or "<i>Not configured</i>"
    s_url = ad_conf.get("sponsor_button_url") or "<i>Not configured</i>"

    text = (
        "⚙️ <b>MONETIZATION & AD SETTINGS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Redirect Gateway:</b> {is_redirect}\n"
        f"• <b>Base URL:</b> {base_url}\n"
        f"• <b>Sponsor Text:</b> {s_text}\n"
        f"• <b>Sponsor Button Label:</b> {s_name}\n"
        f"• <b>Sponsor Button Link:</b> {s_url}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Select parameter to modify:"
    )

    toggle_btn_text = "🔴 Disable Redirect" if ad_conf.get("is_redirect_enabled") else "🟢 Enable Redirect"

    buttons = [
        [
            InlineKeyboardButton(text=toggle_btn_text, callback_data="admin_toggle_redirect")
        ],
        [
            InlineKeyboardButton(text="🔗 Change Base URL", callback_data="admin_edit_redirect_url"),
            InlineKeyboardButton(text="📝 Change Sponsor Text", callback_data="admin_edit_sponsor_text")
        ],
        [
            InlineKeyboardButton(text="🌟 Change Sponsor Button", callback_data="admin_edit_sponsor_btn")
        ],
        [
            InlineKeyboardButton(text="🔙 Admin Menu", callback_data="admin_main_menu")
        ]
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


# ==============================================================================
# /ADMIN ROOT HANDLER
# ==============================================================================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Entry point for /admin dashboard."""
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("⛔ This command is only for authorized administrators.")
        return

    text = (
        "🛡️ <b>ADMIN CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Select a section to manage system parameters or broadcasts:"
    )
    await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_main_menu")
async def callback_admin_main(callback: CallbackQuery):
    """Return to admin root menu."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    text = (
        "🛡️ <b>ADMIN CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Select a section to manage system parameters or broadcasts:"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    await callback.answer()


# ==============================================================================
# MONETIZATION SETTINGS
# ==============================================================================

@router.callback_query(F.data == "admin_monetization")
async def callback_admin_monetization(callback: CallbackQuery):
    """Show monetization settings view."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    text, kb = await build_monetization_text_and_keyboard()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_toggle_redirect")
async def callback_toggle_redirect(callback: CallbackQuery):
    """Toggle redirect on/off."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    current = await get_ad_settings()
    new_state = False if current.get("is_redirect_enabled") else True
    await update_ad_settings(is_redirect_enabled=new_state)

    text, kb = await build_monetization_text_and_keyboard()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_edit_redirect_url")
async def callback_edit_redirect_url(callback: CallbackQuery, state: FSMContext):
    """Prompt for new base redirect URL."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminMonetizationStates.waiting_redirect_url)
    text = (
        "🔗 <b>Enter Redirect Base URL:</b>\n\n"
        "e.g.: <code>https://mycardomain.com/go</code>\n"
        "Enter <code>-</code> to reset."
    )
    if isinstance(callback.message, Message):
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(AdminMonetizationStates.waiting_redirect_url)
async def process_redirect_url_input(message: Message, state: FSMContext):
    """Save new redirect base url."""
    if not message.from_user or not is_admin(message.from_user.id):
        return

    url = (message.text or "").strip()
    val = "" if url == "-" else url
    await update_ad_settings(redirect_base_url=val)
    await state.clear()

    await message.answer(f"✅ Base URL updated: <code>{val or 'Reset'}</code>", parse_mode="HTML")
    text, kb = await build_monetization_text_and_keyboard()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_edit_sponsor_text")
async def callback_edit_sponsor_text(callback: CallbackQuery, state: FSMContext):
    """Prompt for sponsor text."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminMonetizationStates.waiting_sponsor_text)
    text = (
        "📝 <b>Enter Sponsor Text:</b>\n\n"
        "This text will be appended under every listing card.\n"
        "Enter <code>-</code> to reset."
    )
    if isinstance(callback.message, Message):
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(AdminMonetizationStates.waiting_sponsor_text)
async def process_sponsor_text_input(message: Message, state: FSMContext):
    """Save new sponsor text."""
    if not message.from_user or not is_admin(message.from_user.id):
        return

    raw = (message.text or "").strip()
    val = "" if raw == "-" else raw
    await update_ad_settings(sponsor_text=val)
    await state.clear()

    await message.answer(f"✅ Sponsor text updated: <b>{val or 'Reset'}</b>", parse_mode="HTML")
    text, kb = await build_monetization_text_and_keyboard()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_edit_sponsor_btn")
async def callback_edit_sponsor_btn(callback: CallbackQuery, state: FSMContext):
    """Prompt for sponsor button name and url."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminMonetizationStates.waiting_sponsor_button)
    text = (
        "🌟 <b>Enter Sponsor Button:</b>\n\n"
        "Format: <code>Button Label | https://link.com</code>\n"
        "Enter <code>-</code> to reset."
    )
    if isinstance(callback.message, Message):
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(AdminMonetizationStates.waiting_sponsor_button)
async def process_sponsor_btn_input(message: Message, state: FSMContext):
    """Save sponsor button name and url."""
    if not message.from_user or not is_admin(message.from_user.id):
        return

    raw = (message.text or "").strip()
    if raw == "-":
        await update_ad_settings(sponsor_button_name="", sponsor_button_url="")
        await state.clear()
        await message.answer("✅ Sponsor button reset.")
    elif "|" in raw:
        parts = raw.split("|", 1)
        b_name = parts[0].strip()
        b_url = parts[1].strip()
        await update_ad_settings(sponsor_button_name=b_name, sponsor_button_url=b_url)
        await state.clear()
        await message.answer(f"✅ Sponsor button configured:\nLabel: <b>{b_name}</b>\nLink: <code>{b_url}</code>", parse_mode="HTML")
    else:
        await message.answer("⚠️ Invalid format! Please use format: <code>Button Label | https://link.com</code> or <code>-</code>", parse_mode="HTML")
        return

    text, kb = await build_monetization_text_and_keyboard()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ==============================================================================
# ADMIN STATISTICS
# ==============================================================================

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Show detailed administrative statistics."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    stats = await get_database_stats()
    text = (
        "📊 <b>ADMIN SYSTEM STATISTICS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Registered Users: <b>{stats.get('total_users', 0)}</b>\n"
        f"🚘 Active Filters: <b>{stats.get('active_filters', 0)}</b>\n"
        f"📁 Total Filters: <b>{stats.get('total_filters', 0)}</b>\n"
        f"🏷️ Total Forum Topics: <b>{stats.get('total_topics', 0)}</b>\n"
        f"🔍 Scanned Listings: <b>{stats.get('seen_listings', 0):,}</b>\n"
        f"🇵🇱 Otomoto Market Benchmarks: <b>{stats.get('cached_benchmarks', 0):,}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    ).replace(",", " ")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Menu", callback_data="admin_main_menu")]
    ])
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ==============================================================================
# BROADCAST WIZARD
# ==============================================================================

@router.callback_query(F.data == "admin_broadcast_start")
async def callback_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Start broadcast wizard."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    if broadcast_engine.is_running:
        await callback.answer("Another broadcast is currently in progress!", show_alert=True)
        return

    await state.set_state(AdminBroadcastStates.waiting_content)
    text = (
        "📢 <b>BROADCAST CAMPAIGN</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Send the message you want to broadcast (Text or Photo + Text).\n\n"
        "To attach an action button, specify it on the last line in this format:\n"
        "<code>BUTTON: Button Label | https://link.com</code>\n\n"
        "<i>To cancel, type /cancel.</i>"
    )
    if isinstance(callback.message, Message):
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_content)
async def process_broadcast_content(message: Message, state: FSMContext):
    """Receive broadcast message, extract optional button and preview."""
    if not message.from_user or not is_admin(message.from_user.id):
        return

    photo_id = None
    caption_or_text = message.caption or message.text or ""

    if message.photo:
        photo_id = message.photo[-1].file_id

    if not caption_or_text and not photo_id:
        await message.answer("⚠️ Please send text or photo.")
        return

    # Check for optional button format
    btn_name, btn_url = None, None
    clean_lines = []
    for line in caption_or_text.splitlines():
        if line.strip().startswith("BUTTON:"):
            payload = line.strip().replace("BUTTON:", "").strip()
            if "|" in payload:
                parts = payload.split("|", 1)
                btn_name = parts[0].strip()
                btn_url = parts[1].strip()
        else:
            clean_lines.append(line)

    final_text = "\n".join(clean_lines).strip()
    await state.update_data(
        broadcast_text=final_text,
        broadcast_photo_id=photo_id,
        broadcast_btn_name=btn_name,
        broadcast_btn_url=btn_url
    )
    await state.set_state(AdminBroadcastStates.waiting_target)

    # Preview keyboard
    reply_kb = None
    if btn_name and btn_url and btn_url.startswith("http"):
        reply_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_name, url=btn_url)]
        ])

    await message.answer("👀 <b>Broadcast Message Preview:</b>", parse_mode="HTML")
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=final_text, reply_markup=reply_kb, parse_mode="HTML")
    else:
        await message.answer(final_text, reply_markup=reply_kb, parse_mode="HTML")

    target_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Send to All Active Topics", callback_data="bcast_target_topics")],
        [InlineKeyboardButton(text="👤 Send to All Users (DM)", callback_data="bcast_target_users")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_main_menu")]
    ])
    await message.answer("🎯 <b>Select target audience:</b>", reply_markup=target_kb, parse_mode="HTML")


@router.callback_query(AdminBroadcastStates.waiting_target, F.data.in_(["bcast_target_topics", "bcast_target_users"]))
async def process_broadcast_launch(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Launch broadcast in background."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    data = await state.get_data()
    target_type = "topics" if callback.data == "bcast_target_topics" else "users"

    text = data.get("broadcast_text", "")
    photo_id = data.get("broadcast_photo_id")
    btn_name = data.get("broadcast_btn_name")
    btn_url = data.get("broadcast_btn_url")

    reply_markup = None
    if btn_name and btn_url and btn_url.startswith("http"):
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_name, url=btn_url)]
        ])

    status_msg = None
    if isinstance(callback.message, Message):
        status_msg = await callback.message.edit_text("📡 <b>Starting broadcast... Please wait.</b>", parse_mode="HTML")
    else:
        status_msg = await bot.send_message(chat_id=callback.from_user.id, text="📡 <b>Starting broadcast...</b>", parse_mode="HTML")

    await state.clear()
    await callback.answer()

    # Launch background task
    try:
        await broadcast_engine.start_broadcast(
            bot=bot,
            admin_id=callback.from_user.id,
            admin_chat_id=status_msg.chat.id,
            status_message_id=status_msg.message_id,
            target_type=target_type,
            message_text=text,
            photo_file_id=photo_id,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to start broadcast: {e}")
        await bot.send_message(chat_id=status_msg.chat.id, text=f"❌ Error: {e}")


@router.message(Command("cancel_broadcast"))
@router.callback_query(F.data == "admin_broadcast_cancel")
async def cancel_running_broadcast(event: Message | CallbackQuery):
    """Stop active broadcast."""
    if not event.from_user or not is_admin(event.from_user.id):
        return

    if not broadcast_engine.is_running:
        msg = "ℹ️ No active broadcast currently running."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    broadcast_engine.request_cancel()
    feedback = "🛑 Broadcast cancellation requested..."
    if isinstance(event, CallbackQuery):
        await event.answer(feedback, show_alert=True)
    else:
        await event.answer(feedback)
