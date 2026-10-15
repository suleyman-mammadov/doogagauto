import sys
from pathlib import Path
import asyncio
import logging

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # type: ignore
from aiogram import Bot, Dispatcher  # type: ignore
from aiogram.fsm.storage.memory import MemoryStorage  # type: ignore

from config.settings import settings
from database.db import init_db
from database.queries import get_ad_settings
from bot.middlewares.i18n import I18nMiddleware
from bot.handlers.admin import router as admin_router
from bot.handlers.filter_fsm import router as filter_router
from bot.handlers.management import router as management_router
from bot.views.listing_card import set_cached_ad_settings
from engine.scheduler import ArbitrageScheduler
from web.app import create_web_app


def setup_logging():
    reconfig = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfig):
        try:
            reconfig(encoding="utf-8")
        except Exception:
            pass

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


async def main():
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Initializing Schengen Car Arbitrage & Live Scanner System (Pan-European Edition)...")

    # 1. Initialize SQLite Database with WAL and complete schemas
    await init_db()

    # 2. Prime ad settings and dynamic caches in memory
    try:
        from web.routes.admin import sync_all_caches
        ad_conf = await get_ad_settings()
        set_cached_ad_settings(ad_conf)
        await sync_all_caches()
        logger.info("Monetization, templates, dynamic menus and button labels loaded successfully.")
    except Exception as ad_err:
        logger.warning(f"Failed to load ad settings / caches on startup: {ad_err}")

    # 3. Create FastAPI Web Application
    web_app = create_web_app()

    # 4. Configure Uvicorn Server
    uvicorn_config = uvicorn.Config(
        app=web_app,
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(uvicorn_config)

    # 5. Check Bot Token
    token = settings.BOT_TOKEN.strip()
    bot = None
    dp = None
    scheduler = None

    if not token or token == "your_bot_token_here":
        logger.warning(
            "====================================================\n"
            "[!] BOT_TOKEN is not set or contains default placeholder!\n"
            "Telegram bot features disabled until token is configured.\n"
            f"Web Admin Panel is running at: http://{settings.WEB_HOST}:{settings.WEB_PORT}/admin\n"
            "===================================================="
        )
    else:
        # Setup Bot and Dispatcher
        bot = Bot(token=token)
        dp = Dispatcher(storage=MemoryStorage())

        # Attach bot to FastAPI app state
        web_app.state.bot = bot

        # Register Middlewares
        i18n_middleware = I18nMiddleware()
        dp.message.middleware(i18n_middleware)
        dp.callback_query.middleware(i18n_middleware)

        # Register Routers
        dp.include_router(admin_router)
        dp.include_router(filter_router)
        dp.include_router(management_router)

        # Initialize Arbitrage Scheduler
        scheduler = ArbitrageScheduler(bot=bot)

    try:
        tasks = [asyncio.create_task(server.serve())]
        logger.info(f"🌐 Web Admin Panel active at: http://localhost:{settings.WEB_PORT}/admin (Login: {settings.WEB_ADMIN_USERNAME})")
        logger.info(f"🔗 Click Tracking Gateway active at: http://localhost:{settings.WEB_PORT}/r/")

        if bot and dp and scheduler:
            # Verify Bot identity
            bot_info = await bot.get_me()
            logger.info(f"🤖 Telegram Bot connected: @{bot_info.username} (ID: {bot_info.id})")
            logger.info(f"Target Telegram Supergroup: {settings.GROUP_CHAT_ID}")
            if settings.ADMIN_USER_IDS:
                logger.info(f"Configured Admin User IDs: {settings.ADMIN_USER_IDS}")

            # Start Scheduler
            await scheduler.start()

            # Delete any pending webhook updates and start polling
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Starting Telegram Bot Polling with i18n & Dashboard FSM...")
            tasks.append(asyncio.create_task(dp.start_polling(bot)))

        # Wait for all background tasks
        await asyncio.gather(*tasks)

    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received.")
    except Exception as e:
        logger.error(f"Fatal error during execution: {e}", exc_info=True)
    finally:
        logger.info("Stopping services gracefully...")
        server.should_exit = True
        if scheduler:
            await scheduler.stop()
        if bot:
            await bot.session.close()
        logger.info("System gracefully stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
