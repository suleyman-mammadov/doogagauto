import sys
from pathlib import Path
import asyncio
import logging
import random
import time
from typing import List, Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot  # type: ignore
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton  # type: ignore
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError  # type: ignore

from config.settings import settings
from database.queries import (
    get_active_topics,
    get_all_user_ids,
    create_broadcast_history,
    update_broadcast_progress,
    update_campaign_progress,
    save_broadcast_message,
    get_broadcast_messages
)

logger = logging.getLogger(__name__)


def generate_progress_bar(percent: float, length: int = 16) -> str:
    """Render a text progress bar e.g. [████████░░░░░░░░] 50%."""
    filled = int(round(length * (percent / 100.0)))
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


class BroadcastEngine:
    """Asynchronous background mass broadcast engine with anti-flood jitter and live progress updates."""

    def __init__(self):
        self._is_running: bool = False
        self._current_task: Optional[asyncio.Task] = None
        self._cancel_requested: bool = False
        self._campaign_id: Optional[int] = None
        self._total_targets: int = 0
        self._current_index: int = 0
        self._sent_count: int = 0
        self._failed_count: int = 0
        self._last_delay: float = 0.0
        self._status: str = "idle"
        self._target_type: str = ""

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def live_status(self) -> Dict[str, Any]:
        """Return real-time broadcast statistics for web polling."""
        pct = round((self._current_index / self._total_targets * 100.0), 1) if self._total_targets > 0 else 0.0
        return {
            "is_running": self._is_running,
            "campaign_id": self._campaign_id,
            "target_type": self._target_type,
            "total_targets": self._total_targets,
            "current_index": self._current_index,
            "sent_count": self._sent_count,
            "failed_count": self._failed_count,
            "percent": pct,
            "last_delay": self._last_delay,
            "status": self._status
        }

    def request_cancel(self):
        """Signal running broadcast to cancel."""
        if self._is_running:
            self._cancel_requested = True
            self._status = "cancelling"
            logger.info("Cancellation requested for current broadcast.")

    async def start_broadcast(
        self,
        bot: Bot,
        admin_id: int,
        admin_chat_id: int,
        status_message_id: int,
        target_type: str,  # 'topics' or 'users'
        message_text: str,
        photo_file_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        campaign_id: Optional[int] = None
    ) -> None:
        """Start broadcast as an asynchronous background task."""
        if self._is_running:
            raise RuntimeError("Another broadcast is already currently in progress.")

        self._is_running = True
        self._cancel_requested = False
        self._campaign_id = campaign_id
        self._total_targets = 0
        self._current_index = 0
        self._sent_count = 0
        self._failed_count = 0
        self._last_delay = 0.0
        self._status = "running"
        self._target_type = target_type

        self._current_task = asyncio.create_task(
            self._execute_broadcast(
                bot=bot,
                admin_id=admin_id,
                admin_chat_id=admin_chat_id,
                status_message_id=status_message_id,
                target_type=target_type,
                message_text=message_text,
                photo_file_id=photo_file_id,
                reply_markup=reply_markup,
                campaign_id=campaign_id
            )
        )

    async def _execute_broadcast(
        self,
        bot: Bot,
        admin_id: int,
        admin_chat_id: int,
        status_message_id: int,
        target_type: str,
        message_text: str,
        photo_file_id: Optional[str],
        reply_markup: Optional[InlineKeyboardMarkup],
        campaign_id: Optional[int] = None
    ):
        """Execute the broadcast loop with jitter and live throttled progress bar."""
        # 1. Resolve targets
        if target_type == "topics":
            targets = await get_active_topics()
            target_desc = f"All Active Topics ({len(targets)} topics)"
        else:
            targets = await get_all_user_ids()
            target_desc = f"All Users (DM - {len(targets)} users)"

        total_targets = len(targets)
        self._total_targets = total_targets
        sent_count = 0
        failed_count = 0
        last_delay = 0.0

        # Create record in broadcast_history if no campaign_id
        broadcast_id = campaign_id or await create_broadcast_history(
            admin_id=admin_id,
            message_text=message_text,
            target_type=target_type,
            total_targets=total_targets
        )
        self._campaign_id = broadcast_id

        logger.info(f"Broadcast #{broadcast_id} started: {total_targets} targets (type: {target_type})")

        last_status_edit_time = time.time()
        last_status_edit_count = 0

        cancel_button_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 Stop Broadcast", callback_data="admin_broadcast_cancel")]
        ])

        try:
            for idx, target in enumerate(targets, start=1):
                if self._cancel_requested:
                    logger.info("Broadcast cancelled by admin request.")
                    break

                success = False
                retries = 2
                while retries > 0 and not self._cancel_requested:
                    try:
                        sent_msg = None
                        if target_type == "topics":
                            # Deliver to group forum topic
                            group_chat_id = settings.GROUP_CHAT_ID
                            if photo_file_id:
                                sent_msg = await bot.send_photo(
                                    chat_id=group_chat_id,
                                    photo=photo_file_id,
                                    caption=message_text,
                                    reply_markup=reply_markup,
                                    message_thread_id=target,
                                    parse_mode="HTML"
                                )
                            else:
                                sent_msg = await bot.send_message(
                                    chat_id=group_chat_id,
                                    text=message_text,
                                    reply_markup=reply_markup,
                                    message_thread_id=target,
                                    parse_mode="HTML"
                                )
                            if sent_msg and hasattr(sent_msg, "message_id"):
                                await save_broadcast_message(
                                    campaign_id=broadcast_id,
                                    chat_id=group_chat_id,
                                    message_id=sent_msg.message_id,
                                    message_thread_id=target
                                )
                        else:
                            # Deliver to direct user message
                            if photo_file_id:
                                sent_msg = await bot.send_photo(
                                    chat_id=target,
                                    photo=photo_file_id,
                                    caption=message_text,
                                    reply_markup=reply_markup,
                                    parse_mode="HTML"
                                )
                            else:
                                sent_msg = await bot.send_message(
                                    chat_id=target,
                                    text=message_text,
                                    reply_markup=reply_markup,
                                    parse_mode="HTML"
                                )
                            if sent_msg and hasattr(sent_msg, "message_id"):
                                await save_broadcast_message(
                                    campaign_id=broadcast_id,
                                    chat_id=target,
                                    message_id=sent_msg.message_id,
                                    message_thread_id=0
                                )
                        success = True
                        break
                    except TelegramRetryAfter as e:
                        logger.warning(f"Flood control hit during broadcast: sleep {e.retry_after}s")
                        await asyncio.sleep(e.retry_after + 1.0)
                        retries -= 1
                    except TelegramAPIError as api_err:
                        logger.debug(f"Target {target} delivery failed: {api_err}")
                        retries = 0
                        break
                    except Exception as err:
                        logger.debug(f"Unexpected error delivering to {target}: {err}")
                        retries = 0
                        break

                if success:
                    sent_count += 1
                else:
                    failed_count += 1

                self._current_index = idx
                self._sent_count = sent_count
                self._failed_count = failed_count

                # Random Jitter delay (1.5s - 3.5s) to avoid Telegram anti-spam detection
                last_delay = round(random.uniform(1.5, 3.5), 1)
                self._last_delay = last_delay
                await asyncio.sleep(last_delay)

                # Live Throttled Progress Bar update: every 5 targets or minimum 3.0 seconds
                now = time.time()
                is_batch_trigger = (idx - last_status_edit_count >= 5)
                is_time_trigger = (now - last_status_edit_time >= 3.0)

                if is_batch_trigger or is_time_trigger or idx == total_targets:
                    percent = (idx / total_targets * 100.0) if total_targets > 0 else 100.0
                    bar_str = generate_progress_bar(percent)
                    remaining = total_targets - idx

                    # Also update campaign table in DB
                    try:
                        await update_campaign_progress(broadcast_id, sent_count, failed_count, status="running")
                    except Exception:
                        pass

                    progress_text = (
                        "📡 <b>BROADCAST IN PROGRESS...</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━━\n"
                        f"<b>Target:</b> {target_desc}\n"
                        f"<b>Progress:</b> [{bar_str}] {percent:.0f}%\n"
                        f"✅ <b>Successful:</b> {sent_count}\n"
                        f"❌ <b>Failed / Blocked:</b> {failed_count}\n"
                        f"⏳ <b>Remaining:</b> {remaining}\n"
                        f"⏱ <b>Last delay:</b> {last_delay}s\n"
                        "━━━━━━━━━━━━━━━━━━━━━\n"
                        "<i>⚠️ To cancel broadcast, click the button below or type /cancel_broadcast.</i>"
                    )

                    try:
                        if admin_chat_id and status_message_id:
                            await bot.edit_message_text(
                                chat_id=admin_chat_id,
                                message_id=status_message_id,
                                text=progress_text,
                                reply_markup=cancel_button_kb,
                                parse_mode="HTML"
                            )
                        last_status_edit_time = now
                        last_status_edit_count = idx
                    except Exception as edit_err:
                        logger.debug(f"Progress bar edit throttled/skipped: {edit_err}")

            # Finalize status
            status_word = "cancelled" if self._cancel_requested else "completed"
            self._status = status_word
            await update_broadcast_progress(
                broadcast_id=broadcast_id,
                sent_count=sent_count,
                failed_count=failed_count,
                status=status_word
            )
            try:
                await update_campaign_progress(
                    campaign_id=broadcast_id,
                    sent_count=sent_count,
                    failed_count=failed_count,
                    status=status_word,
                    completed=True
                )
            except Exception:
                pass

            status_icon = "⚠️" if self._cancel_requested else "🎉"
            final_title = "Broadcast Cancelled" if self._cancel_requested else "Broadcast Completed!"

            summary_text = (
                f"{status_icon} <b>{final_title}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Total Targets:</b> {total_targets}\n"
                f"✅ <b>Successfully Delivered:</b> {sent_count}\n"
                f"❌ <b>Failed / Undelivered:</b> {failed_count}\n"
                f"📁 <b>Campaign ID:</b> #{broadcast_id}\n"
                "━━━━━━━━━━━━━━━━━━━━━"
            )

            try:
                if admin_chat_id and status_message_id:
                    await bot.edit_message_text(
                        chat_id=admin_chat_id,
                        message_id=status_message_id,
                        text=summary_text,
                        reply_markup=None,
                        parse_mode="HTML"
                    )
            except Exception:
                if admin_chat_id:
                    await bot.send_message(chat_id=admin_chat_id, text=summary_text, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Fatal broadcast execution error: {e}", exc_info=True)
            self._status = "failed"
            await update_broadcast_progress(broadcast_id, sent_count, failed_count, status="failed")
            try:
                await update_campaign_progress(broadcast_id, sent_count, failed_count, status="failed", completed=True)
            except Exception:
                pass
        finally:
            self._is_running = False
            self._cancel_requested = False
            self._current_task = None

    async def delete_campaign_messages(self, bot: Bot, campaign_id: int) -> Dict[str, Any]:
        """Delete all sent Telegram messages for a given campaign."""
        messages = await get_broadcast_messages(campaign_id)
        deleted = 0
        failed = 0
        for m in messages:
            try:
                await bot.delete_message(chat_id=m["chat_id"], message_id=m["message_id"])
                deleted += 1
            except Exception as e:
                logger.debug(f"Could not delete message {m['message_id']} in chat {m['chat_id']}: {e}")
                failed += 1
            await asyncio.sleep(0.05)  # slight throttle
        await update_campaign_progress(
            campaign_id=campaign_id,
            sent_count=0,
            failed_count=failed,
            status="deleted",
            completed=True
        )
        return {"total": len(messages), "deleted": deleted, "failed": failed}


# Singleton instance
broadcast_engine = BroadcastEngine()
