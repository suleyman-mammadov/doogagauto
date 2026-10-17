import sys
from pathlib import Path
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot  # type: ignore

from config.settings import settings
from database.queries import (
    get_active_filters,
    is_listing_seen,
    save_seen_listing,
    get_ad_settings,
    get_hot_deals_topic_id,
    set_hot_deals_topic_id,
    get_proxy_settings,
    increment_filter_alert_count,
    get_eligible_hot_deals_users,
    update_user_hot_deals_sent_timestamp,
    update_user_filter,
    set_user_notification_target,
    get_user_language
)
from bot.locales.texts import t
from scrapers.base_scraper import BaseScraper, CarListing, set_cached_proxy_settings
from scrapers.baltic.ss_latvia import SSLatviaScraper
from scrapers.baltic.autoplius_lt import AutopliusLtScraper
from scrapers.central.bazos_sk import BazosSkScraper
from scrapers.central.bazos_cz import BazosCzScraper
from scrapers.central.sauto_cz import SautoCzScraper
from scrapers.western.mobile_de import MobileDeScraper
from scrapers.western.kleinanzeigen_de import KleinanzeigenDeScraper
from scrapers.western.leboncoin_fr import LeboncoinFrScraper
from scrapers.western.subito_it import SubitoItScraper
from scrapers.poland_benchmarks.otomoto_pl import OtomotoBenchmarkScraper

from engine.arbitrage import ArbitrageEngine, ArbitrageResult
from bot.views.listing_card import (
    format_listing_card_html,
    create_listing_card_keyboard,
    set_cached_ad_settings
)

logger = logging.getLogger(__name__)


class ArbitrageScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.arbitrage_engine = ArbitrageEngine(eur_to_pln=settings.EUR_TO_PLN_RATE)
        self.otomoto_scraper = OtomotoBenchmarkScraper()
        
        # Pan-European Multi-Platform Scrapers Matrix
        self.scrapers: List[BaseScraper] = [
            # Baltic
            SSLatviaScraper(),
            AutopliusLtScraper(),
            # Central
            BazosSkScraper(),
            BazosCzScraper(),
            SautoCzScraper(),
            # Western
            MobileDeScraper(),
            KleinanzeigenDeScraper(),
            LeboncoinFrScraper(),
            SubitoItScraper()
        ]

        self.last_run: Dict[str, float] = {
            scraper.name: 0.0 for scraper in self.scrapers
        }
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._hot_deals_sent_today: int = 0
        self._hot_deals_today_date: str = ""

    async def start(self):
        """Start background Pan-European scheduler task."""
        if self._running:
            return
        self._running = True
        try:
            ad_conf = await get_ad_settings()
            set_cached_ad_settings(ad_conf)
            proxy_conf = await get_proxy_settings()
            set_cached_proxy_settings(proxy_conf)
        except Exception as e:
            logger.debug(f"Failed to prime caches: {e}")

        # Load persisted Hot Deals topic ID from SQLite DB to prevent duplicate topic creation
        try:
            persisted_topic_id = await get_hot_deals_topic_id()
            if persisted_topic_id:
                settings.HOT_DEALS_TOPIC_ID = persisted_topic_id
                logger.info(f"Loaded persistent Hot Deals topic ID: {persisted_topic_id}")
            elif settings.HOT_DEALS_TOPIC_ID:
                await set_hot_deals_topic_id(settings.HOT_DEALS_TOPIC_ID)
                logger.info(f"Initialized persistent Hot Deals topic ID from settings: {settings.HOT_DEALS_TOPIC_ID}")
        except Exception as topic_err:
            logger.warning(f"Failed to load persistent Hot Deals topic ID: {topic_err}")

        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"ArbitrageScheduler started with {len(self.scrapers)} Pan-European platform scrapers.")

    async def stop(self):
        """Gracefully stop background scheduler and close sessions."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        for scraper in self.scrapers:
            await scraper.close()
        await self.otomoto_scraper.close()
        logger.info("ArbitrageScheduler stopped.")

    async def _recreate_hot_deals_topic(self) -> Optional[int]:
        """Auto-create or recreate '🔥 Hot Deals' forum topic in Telegram supergroup and persist its ID."""
        try:
            topic = await self.bot.create_forum_topic(
                chat_id=settings.GROUP_CHAT_ID,
                name="🔥 Hot Deals"
            )
            settings.HOT_DEALS_TOPIC_ID = topic.message_thread_id
            await set_hot_deals_topic_id(topic.message_thread_id)
            logger.info(f"Auto-created '🔥 Hot Deals' forum topic with ID {topic.message_thread_id} in {settings.GROUP_CHAT_ID} and persisted to DB.")
            return topic.message_thread_id
        except Exception as e:
            logger.error(f"Failed to auto-create '🔥 Hot Deals' topic in {settings.GROUP_CHAT_ID}: {e}")
            return None

    async def _send_listing_alert(
        self,
        result: ArbitrageResult,
        target_chat_id: Optional[Any] = None,
        topic_id: Optional[int] = None,
        is_hot_deal_feed: bool = False
    ):
        """Deliver car alert to a specified chat (private user DM or group topic)."""
        chat_id = target_chat_id or settings.GROUP_CHAT_ID
        if not chat_id:
            logger.debug("No chat_id configured, skipping alert delivery.")
            return

        html_text = format_listing_card_html(result, is_hot_deal_feed=is_hot_deal_feed)
        keyboard = create_listing_card_keyboard(result)
        image_url = result.listing.image_url

        try:
            # Try sending with photo if available
            if image_url and image_url.startswith("http"):
                try:
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=html_text,
                        reply_markup=keyboard,
                        message_thread_id=topic_id if topic_id else None,
                        parse_mode="HTML"
                    )
                    return
                except Exception as photo_err:
                    err_msg = str(photo_err).lower()
                    if ("thread not found" in err_msg or "message thread not found" in err_msg) and is_hot_deal_feed and not target_chat_id:
                        logger.warning(f"Hot Deals topic {topic_id} was deleted in group. Auto-recreating topic...")
                        new_topic_id = await self._recreate_hot_deals_topic()
                        if new_topic_id:
                            await self._send_listing_alert(result, topic_id=new_topic_id, is_hot_deal_feed=True)
                            return
                    logger.debug(f"Failed to send with photo, falling back to text: {photo_err}")

            # Send HTML text message
            await self.bot.send_message(
                chat_id=chat_id,
                text=html_text,
                reply_markup=keyboard,
                message_thread_id=topic_id if topic_id else None,
                parse_mode="HTML"
            )
        except Exception as e:
            err_msg = str(e).lower()
            if ("thread not found" in err_msg or "message thread not found" in err_msg) and is_hot_deal_feed and not target_chat_id:
                logger.warning(f"Hot Deals topic {topic_id} was deleted in group. Auto-recreating topic...")
                new_topic_id = await self._recreate_hot_deals_topic()
                if new_topic_id:
                    await self._send_listing_alert(result, topic_id=new_topic_id, is_hot_deal_feed=True)
                    return
            logger.error(f"Error sending listing alert {result.listing.platform}/{result.listing.external_id} to chat {chat_id} (topic {topic_id}): {e}")
            if target_chat_id:
                raise e

    async def _process_listing(self, listing: CarListing, active_filters: List[dict]):
        """Evaluate a new listing against active filters and Otomoto market benchmarks."""
        # 1. Deduplication check
        if await is_listing_seen(listing.platform, listing.external_id):
            return

        # 2. Save into seen_listings with make and model
        await save_seen_listing(
            platform=listing.platform,
            external_id=listing.external_id,
            country_code=listing.country,
            title=listing.title,
            url=listing.url,
            price_eur=listing.price_eur,
            year=listing.year,
            mileage_km=listing.mileage_km,
            fuel_type=listing.fuel_type,
            photo_url=listing.image_url,
            created_in_source=listing.created_in_source,
            make=listing.make,
            model=listing.model
        )

        # 3. Check matching user filters
        matching_filters = [
            f for f in active_filters
            if self.arbitrage_engine.matches_filter(listing, f)
        ]

        if not matching_filters and not listing.year:
            return

        # 4. Fetch Polish Otomoto market benchmark
        benchmark = None
        if listing.make and listing.year:
            benchmark = await self.otomoto_scraper.get_market_price(
                make=listing.make,
                model=listing.model or "",
                year=listing.year,
                fuel_type=listing.fuel_type,
                use_cache=True
            )

        if not benchmark:
            logger.debug(f"No Otomoto benchmark for {listing.make} {listing.model} ({listing.year})")
            return

        # 5. Calculate Pan-European arbitrage model
        result = self.arbitrage_engine.calculate_arbitrage(listing, benchmark)
        logger.info(
            f"[{listing.platform.upper()}] Car evaluated: {listing.title} | "
            f"Price: {listing.price_eur:,.0f}€ | Polish Median: {result.poland_median_pln:,.0f} PLN | "
            f"Profit: {result.profit_eur:+.0f}€ ({result.profit_percent:+.1f}%)"
        )

        # 6. Deliver to matching filter owner DIRECTLY in Private Chat (DM) with Daily Limits
        today_str = time.strftime("%Y-%m-%d")
        for flt in matching_filters:
            user_id = flt.get("user_id")
            if not user_id:
                continue

            # Daily limit check
            daily_limit = flt.get("daily_alert_limit", 0) or 0
            sent_today = flt.get("alerts_sent_today", 0) or 0
            last_date = flt.get("last_alert_date", "")
            if last_date != today_str:
                sent_today = 0

            if daily_limit > 0 and sent_today >= daily_limit:
                logger.info(f"Filter #{flt['id']} reached daily alert limit ({daily_limit}). Skipping DM for user {user_id}.")
                continue

            # Minimum profit check for filter if specified
            min_filter_profit = flt.get("min_profit_eur", 0.0) or 0.0
            if min_filter_profit > 0 and result.profit_eur < min_filter_profit:
                continue

            target_chat_id = flt.get("target_chat_id") or user_id
            topic_id = flt.get("topic_id", 0) or 0

            # If user selected Group mode and has a valid topic_id
            if target_chat_id != user_id and topic_id > 0:
                try:
                    await self._send_listing_alert(
                        result=result,
                        target_chat_id=target_chat_id,
                        topic_id=topic_id,
                        is_hot_deal_feed=False
                    )
                    await increment_filter_alert_count(flt["id"])
                    logger.info(f"✅ Alert for {listing.title} delivered to group {target_chat_id} (topic {topic_id})")
                except Exception as group_err:
                    logger.warning(
                        f"Failed delivering alert to group {target_chat_id} topic {topic_id}: {group_err}. "
                        f"Executing Fallback to DM for user {user_id}!"
                    )
                    # 1. Fallback immediately to user's private DM (User never misses deal!)
                    try:
                        await self._send_listing_alert(
                            result=result,
                            target_chat_id=user_id,
                            topic_id=None,
                            is_hot_deal_feed=False
                        )
                        await increment_filter_alert_count(flt["id"])
                        logger.info(f"✅ Fallback alert for {listing.title} delivered to user {user_id} DM")
                    except Exception as fallback_err:
                        logger.error(f"Fallback DM delivery failed for user {user_id}: {fallback_err}")

                    # 2. Inform user in DM about the group error
                    try:
                        u_lang = await get_user_language(user_id) or "en"
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=t("group_error_fallback", u_lang),
                            parse_mode="HTML"
                        )
                    except Exception as notify_err:
                        logger.debug(f"Could not send fallback warning to user {user_id}: {notify_err}")

                    # 3. Reset database status to DM
                    try:
                        await set_user_notification_target(user_id, "dm")
                        await update_user_filter(flt["id"], target_chat_id=user_id, topic_id=0)
                    except Exception as db_err:
                        logger.warning(f"Error resetting user notification target: {db_err}")
            else:
                # Default: Deliver directly to user's private Telegram DM
                try:
                    await self._send_listing_alert(
                        result=result,
                        target_chat_id=user_id,
                        topic_id=None,
                        is_hot_deal_feed=False
                    )
                    await increment_filter_alert_count(flt["id"])
                    logger.info(f"✅ Alert for {listing.title} delivered to user {user_id} DM (Filter #{flt['id']})")
                except Exception as dm_err:
                    logger.warning(f"Failed to deliver filter alert to user {user_id}: {dm_err}")

        # 7. Hot deal delivery to public #HotDeals (Group Showcase) + Personalized User DMs
        if result.is_hot_deal:
            today_str = time.strftime("%Y-%m-%d")
            if self._hot_deals_today_date != today_str:
                self._hot_deals_today_date = today_str
                self._hot_deals_sent_today = 0

            daily_limit = getattr(settings, "HOT_DEAL_DAILY_LIMIT", 10)
            if daily_limit > 0 and self._hot_deals_sent_today >= daily_limit:
                logger.info(
                    f"Daily Hot Deals limit ({daily_limit}) reached for {today_str}. "
                    f"Skipping public #HotDeals alert for: {listing.title}"
                )
            else:
                self._hot_deals_sent_today += 1
                logger.info(
                    f"🔥 HOT DEAL DETECTED ({self._hot_deals_sent_today}/{daily_limit or '∞'} today): "
                    f"{listing.title} ({result.profit_percent:+.1f}%, +{result.profit_eur:,.0f}€)"
                )
                try:
                    hot_deals_topic = settings.HOT_DEALS_TOPIC_ID
                    if not hot_deals_topic:
                        hot_deals_topic = await self._recreate_hot_deals_topic()
                    if hot_deals_topic:
                        await self._send_listing_alert(result, target_chat_id=settings.GROUP_CHAT_ID, topic_id=hot_deals_topic, is_hot_deal_feed=True)
                except Exception as group_hd_err:
                    logger.warning(f"Failed to post public hot deal to group {settings.GROUP_CHAT_ID}: {group_hd_err}")

            # Also deliver to eligible users who opted into personalized Hot Deals in their DM!
            try:
                eligible_users = await get_eligible_hot_deals_users(
                    profit_eur=result.profit_eur,
                    year=listing.year,
                    price_eur=listing.price_eur,
                    profit_percent=result.profit_percent,
                    mileage_km=listing.mileage_km
                )
                for u_id in eligible_users:
                    try:
                        await self._send_listing_alert(result, target_chat_id=u_id, topic_id=None, is_hot_deal_feed=True)
                        await update_user_hot_deals_sent_timestamp(u_id)
                        logger.info(f"🔥 Personalized Hot Deal delivered to user {u_id} DM")
                    except Exception as u_err:
                        logger.debug(f"Could not deliver Hot Deal to user {u_id}: {u_err}")
            except Exception as elig_err:
                logger.warning(f"Error checking eligible Hot Deals users: {elig_err}")

    async def _run_loop(self):
        """Main periodic scheduling loop across all Pan-European platforms."""
        logger.info("Pan-European Scheduler loop started.")
        while self._running:
            try:
                # Refresh ad settings and active filters
                try:
                    ad_conf = await get_ad_settings()
                    set_cached_ad_settings(ad_conf)
                except Exception:
                    pass

                active_filters = await get_active_filters()
                now = time.time()

                for scraper in self.scrapers:
                    if not self._running:
                        break

                    time_since_last = now - self.last_run.get(scraper.name, 0.0)
                    if time_since_last >= scraper.interval_seconds:
                        logger.info(f"Running scraper: {scraper.name} (interval {scraper.interval_seconds}s)")
                        self.last_run[scraper.name] = now
                        
                        try:
                            listings = await scraper.scrape(filters=active_filters)
                            for listing in listings:
                                if not self._running:
                                    break
                                await self._process_listing(listing, active_filters)
                        except Exception as scrape_err:
                            logger.error(f"Error during scrape in {scraper.name}: {scrape_err}")

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                logger.error(f"Unexpected error in scheduler loop: {loop_err}", exc_info=True)
                await asyncio.sleep(10)
