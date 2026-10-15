import sys
from pathlib import Path
import asyncio
import logging

sys.path.insert(0, str(Path(__file__).resolve().parent))

reconfig = getattr(sys.stdout, "reconfigure", None)
if callable(reconfig):
    try:
        reconfig(encoding="utf-8")
    except Exception:
        pass

from config.settings import settings
from database.db import init_db, get_db
from database.queries import (
    set_user_language,
    get_user_language,
    get_all_user_ids,
    get_total_users_count,
    create_user_filter,
    get_active_filters,
    get_user_filters,
    get_filter_by_id,
    toggle_filter_status,
    delete_filter,
    get_active_topics,
    get_ad_settings,
    update_ad_settings,
    create_broadcast_history,
    update_broadcast_progress,
    get_database_stats
)
from bot.locales.texts import t, LANGUAGES, OPTIONS_MAP, get_option_label
from bot.handlers.filter_fsm import format_dashboard_text, build_dashboard_keyboard, get_topic_link
from bot.handlers.admin import is_admin
from bot.views.listing_card import (
    format_listing_card_html,
    create_listing_card_keyboard,
    set_cached_ad_settings,
    get_cached_ad_settings
)
from engine.arbitrage import ArbitrageEngine, ArbitrageResult
from engine.broadcaster import generate_progress_bar, broadcast_engine
from scrapers.base_scraper import CarListing

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_upgrade")


async def test_all():
    logger.info("==================================================")
    logger.info("STARTING TELEGRAM UPGRADE SPECIFICATION TEST SUITE")
    logger.info("==================================================")

    # 1. DATABASE & WAL PRAGMAS TEST
    logger.info("\n--- 1. Testing SQLite WAL Pragmas & Initialization ---")
    await init_db()

    async with get_db() as db:
        async with db.execute("PRAGMA journal_mode;") as cur:
            mode = (await cur.fetchone())[0]
            logger.info(f"PRAGMA journal_mode: {mode}")
            assert str(mode).lower() == "wal", f"Expected WAL mode, got {mode}"

        async with db.execute("PRAGMA busy_timeout;") as cur:
            timeout = (await cur.fetchone())[0]
            logger.info(f"PRAGMA busy_timeout: {timeout} ms")
            assert int(timeout) >= 30000, f"Expected timeout >= 30000, got {timeout}"

        async with db.execute("PRAGMA synchronous;") as cur:
            sync = (await cur.fetchone())[0]
            logger.info(f"PRAGMA synchronous: {sync}")

    # 2. USER SETTINGS & i18n
    logger.info("\n--- 2. Testing user_settings & Multilingual Localization ---")
    test_user_id = 9988776655
    await set_user_language(test_user_id, "pl")
    lang = await get_user_language(test_user_id)
    assert lang == "pl", f"Expected 'pl', got {lang}"
    logger.info(f"User language set and retrieved: {lang}")

    # Check 3 active languages in texts.py (en, pl, ru)
    for l_code in ["en", "pl", "ru"]:
        welcome = t("welcome_message", l_code)
        btn_search = t("btn_new_search", l_code)
        fuel_label = get_option_label("fuel", "hybrid", l_code)
        assert welcome and btn_search and fuel_label, f"Missing translations for {l_code}"
        logger.info(f"[{l_code.upper()}] Button: '{btn_search}' | Fuel: '{fuel_label}'")

    # 3. USER FILTERS WITH SPEC SCHEMA
    logger.info("\n--- 3. Testing user_filters with Complete Schema ---")
    filter_id = await create_user_filter(
        user_id=test_user_id,
        make="BMW",
        model="X5",
        year_min=2015,
        year_max=2022,
        mileage_min=0,
        mileage_max=180000,
        price_min_eur=4000,
        price_max_eur=9000,
        fuel_type="petrol",
        condition="undamaged",
        transmission="automatic",
        body_type="suv",
        target_country="DE",
        topic_id=456,
        pinned_message_id=789,
        is_active=1
    )
    assert filter_id > 0, "Failed to create user filter"
    logger.info(f"Created filter ID: #{filter_id}")

    saved_filter = await get_filter_by_id(filter_id)
    assert saved_filter is not None
    assert saved_filter["make"] == "Bmw"
    assert saved_filter["model"] == "X5"
    assert saved_filter["topic_id"] == 456
    assert saved_filter["pinned_message_id"] == 789
    assert saved_filter["target_country"] == "DE"
    logger.info(f"Verified filter data: {saved_filter['make']} {saved_filter['model']}, Topic: {saved_filter['topic_id']}")

    # Test toggle status
    new_status = await toggle_filter_status(filter_id)
    assert new_status == 0, f"Expected paused status 0, got {new_status}"
    new_status = await toggle_filter_status(filter_id)
    assert new_status == 1, f"Expected active status 1, got {new_status}"
    logger.info("Filter toggle status verified (1 -> 0 -> 1).")

    active_topics = await get_active_topics()
    assert 456 in active_topics
    logger.info(f"Active topics list includes 456: {active_topics}")

    # 4. SINGLE-MESSAGE DASHBOARD FSM TEXT & KEYBOARD
    logger.info("\n--- 4. Testing Single-Message Dashboard FSM ---")
    mock_fsm_data = {
        "make": "BMW",
        "model": "X5",
        "year_min": 2015,
        "year_max": 2022,
        "mileage_min": 0,
        "mileage_max": 180000,
        "price_min_eur": 4000.0,
        "price_max_eur": 9000.0,
        "fuel_type": "petrol",
        "condition": "undamaged",
        "transmission": "automatic",
        "body_type": "suv",
        "target_country": "DE"
    }
    dash_text = format_dashboard_text(mock_fsm_data, lang="en")
    logger.info("Generated Dashboard Message (EN):")
    print(dash_text)
    assert "SEARCH DASHBOARD: BMW" in dash_text
    assert "2015 - 2022" in dash_text
    assert "4 000 € - 9 000 €" in dash_text or "4000" in dash_text

    dash_kb = build_dashboard_keyboard("en")
    assert len(dash_kb.inline_keyboard) == 7, f"Expected 7 rows in dashboard keyboard, got {len(dash_kb.inline_keyboard)}"
    logger.info(f"Dashboard keyboard rows: {len(dash_kb.inline_keyboard)} rows verified.")

    # 5. MONETIZATION, REDIRECT URL & SPONSOR BUTTON
    logger.info("\n--- 5. Testing Monetization, Redirect URL & Sponsor Settings ---")
    # Set ad settings
    updated_ads = await update_ad_settings(
        is_redirect_enabled=True,
        redirect_base_url="https://mycardomain.com/go",
        sponsor_text="Contact our partner for competitive car financing and insurance!",
        sponsor_button_name="Calculate Insurance",
        sponsor_button_url="https://insurance-partner.com"
    )
    set_cached_ad_settings(updated_ads)

    assert updated_ads["is_redirect_enabled"] == 1
    assert updated_ads["redirect_base_url"] == "https://mycardomain.com/go"
    logger.info(f"Ad settings updated: redirect={updated_ads['is_redirect_enabled']}, url={updated_ads['redirect_base_url']}")

    # Create dummy car listing and arbitrage result
    test_listing = CarListing(
        external_id="bmw_test_1",
        platform="mobile_de",
        country="DE",
        title="BMW X5 xDrive30d M Sport",
        make="BMW",
        model="X5",
        year=2018,
        price_eur=24500.0,
        mileage_km=142000,
        fuel_type="Diesel",
        location="Munich",
        url="https://www.mobile.de/cz/osobni-vuz/bmw-x5/test.html"
    )

    arb_engine = ArbitrageEngine(eur_to_pln=4.30)
    mock_benchmark = {
        "make": "BMW",
        "model": "X5",
        "year": 2018,
        "median_price_pln": 155000.0,
        "median_price_eur": 36046.0,
        "sample_count": 28,
        "url": "https://www.otomoto.pl/osobowe/bmw/x5"
    }

    arb_res = arb_engine.calculate_arbitrage(test_listing, mock_benchmark)
    
    # Generate HTML with monetization
    html_card = format_listing_card_html(arb_res, ad_settings=updated_ads)
    assert "Contact our partner for competitive car financing and insurance!" in html_card
    logger.info("Verified sponsor text appears in car card HTML.")

    # Generate keyboard with redirect URL and sponsor button
    card_kb = create_listing_card_keyboard(arb_res, ad_settings=updated_ads)
    first_btn = card_kb.inline_keyboard[0][0]
    assert "mycardomain.com/go?target=" in first_btn.url
    logger.info(f"Verified redirect URL masked on button: {first_btn.url}")

    # Check sponsor button
    sponsor_btn = card_kb.inline_keyboard[-1][0]
    assert "Calculate Insurance" in sponsor_btn.text
    assert sponsor_btn.url == "https://insurance-partner.com"
    logger.info(f"Verified sponsor button attached: text='{sponsor_btn.text}', url='{sponsor_btn.url}'")

    # 6. BROADCASTER & LIVE PROGRESS BAR
    logger.info("\n--- 6. Testing Broadcast History & Progress Bar Renderer ---")
    bar_25 = generate_progress_bar(25.0)
    bar_52 = generate_progress_bar(52.0)
    bar_100 = generate_progress_bar(100.0)
    logger.info(f"Progress 25%:  [{bar_25}]")
    logger.info(f"Progress 52%:  [{bar_52}]")
    logger.info(f"Progress 100%: [{bar_100}]")
    assert "█" in bar_52 and "░" in bar_52

    bcast_id = await create_broadcast_history(
        admin_id=123456,
        message_text="Test announcement",
        target_type="topics",
        total_targets=10
    )
    assert bcast_id > 0
    await update_broadcast_progress(bcast_id, sent_count=9, failed_count=1, status="completed")
    logger.info(f"Broadcast history entry #{bcast_id} recorded and updated.")

    # 7. ADMIN AUTHORIZATION & STATS
    logger.info("\n--- 7. Testing Admin Security & System Statistics ---")
    settings.ADMIN_USER_IDS = [123456, 998877]
    assert is_admin(123456) is True
    assert is_admin(999999) is False
    logger.info(f"Admin authorization check passed: ID 123456 is Admin -> {is_admin(123456)}")

    stats = await get_database_stats()
    logger.info(f"Database Stats Summary: {stats}")
    assert stats["total_users"] >= 1
    assert stats["total_topics"] >= 1

    # Clean up test filter
    await delete_filter(filter_id)
    logger.info("Test filter cleaned up.")

    logger.info("\n==================================================")
    logger.info("✅ ALL SPECIFICATION TESTS PASSED SUCCESSFULLY!")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(test_all())
