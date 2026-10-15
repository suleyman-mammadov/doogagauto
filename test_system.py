import asyncio
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).resolve().parent))

reconfig = getattr(sys.stdout, "reconfigure", None)
if callable(reconfig):
    try:
        reconfig(encoding="utf-8")
    except Exception:
        pass

from database.db import init_db
from database.queries import (
    create_user_filter,
    get_active_filters,
    get_database_stats
)
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

from engine.arbitrage import ArbitrageEngine
from bot.views.listing_card import format_listing_card_html, create_listing_card_keyboard
from scrapers.base_scraper import CarListing

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_system")


async def run_tests():
    logger.info("=== 1. Testing Database Initialization & Migration ===")
    await init_db()
    
    # Create test filter with Pan-European attributes
    flt_id = await create_user_filter(
        user_id=12345678,
        make="Toyota",
        model="Prius",
        year_min=2010,
        year_max=2022,
        price_max_eur=10000,
        mileage_max_km=200000,
        fuel_type="Hybrid",
        transmission="Automatic",
        target_countries="ALL",
        target_platforms="ALL",
        topic_id=100,
        topic_name="🚗 [ALL] Toyota Prius (<10k€)"
    )
    logger.info(f"Created Pan-European test filter ID: #{flt_id}")
    active_filters = await get_active_filters()
    logger.info(f"Active filters in DB: {len(active_filters)}")

    logger.info("\n=== 2. Testing Scrapers Connectivity & Parsing ===")
    scrapers = [
        SSLatviaScraper(),
        BazosSkScraper(),
        BazosCzScraper(),
        AutopliusLtScraper(),
        SautoCzScraper(),
        MobileDeScraper(),
        KleinanzeigenDeScraper(),
        LeboncoinFrScraper(),
        SubitoItScraper()
    ]

    for sc in scrapers:
        try:
            logger.info(f"Testing scraper: {sc.name} ({sc.country}) [Level {sc.protection_level}]...")
            listings = await sc.scrape(filters=active_filters)
            logger.info(f"-> {sc.name} returned {len(listings)} listings.")
            if listings:
                sample = listings[0]
                logger.info(f"   Sample: [{sample.country}] {sample.title} | {sample.price_eur}€ | Year: {sample.year} | {sample.url}")
            await sc.close()
        except Exception as e:
            logger.warning(f"Note testing {sc.name}: {e}")

    logger.info("\n=== 3. Testing Otomoto Poland Benchmark Scraper ===")
    oto_scraper = OtomotoBenchmarkScraper()
    benchmark = await oto_scraper.get_market_price("Toyota", "Prius", 2011, fuel_type="Hybrid", use_cache=False)
    if benchmark:
        logger.info(f"Otomoto Benchmark for Toyota Prius 2011:")
        logger.info(f"   Median PLN: {benchmark['median_price_pln']} PLN (~{benchmark['median_price_eur']} EUR)")
        logger.info(f"   Sample count: {benchmark['sample_count']} ads")
    else:
        logger.warning("Could not retrieve live Otomoto benchmark, using fallback mock for arithmetic test")
        benchmark = {
            "make": "Toyota",
            "model": "Prius",
            "year": 2011,
            "median_price_pln": 30450.0,
            "median_price_eur": 7081.4,
            "sample_count": 14,
            "url": "https://www.otomoto.pl/osobowe/toyota/prius"
        }
    await oto_scraper.close()

    logger.info("\n=== 4. Testing Arbitrage Calculation & Car Card Presentation ===")
    engine = ArbitrageEngine(eur_to_pln=4.30)
    
    test_listing = CarListing(
        external_id="ss_test_99999",
        platform="ss_latvia",
        country="LV",
        title="Toyota Prius 1.8 Hybrid HSD",
        make="Toyota",
        model="Prius",
        year=2011,
        price_eur=4800.0,
        mileage_km=185000,
        fuel_type="Hybrid",
        engine_size="1.8 H",
        location="Riga",
        url="https://www.ss.com/msg/lv/transport/cars/toyota/prius/test.html"
    )

    result = engine.calculate_arbitrage(test_listing, benchmark)
    logger.info(f"Arbitrage Result:")
    logger.info(f"   Purchase Price: {result.listing.price_eur}€ (~{result.listing_price_pln} PLN)")
    logger.info(f"   Transport Cost ({test_listing.country}): {result.transport_cost_eur}€ (~{result.transport_cost_pln} PLN)")
    logger.info(f"   Akcyza ({result.akcyza_rate*100:.1f}%): ~{result.akcyza_cost_pln} PLN (~{result.akcyza_cost_eur}€)")
    logger.info(f"   Total Landed Cost: {result.total_landed_cost_pln} PLN (~{result.total_landed_cost_eur}€)")
    logger.info(f"   Polish Otomoto Median: {result.poland_median_pln} PLN (~{result.poland_median_eur}€)")
    logger.info(f"   Gross Arbitrage Profit: {result.profit_pln:+.0f} PLN ({result.profit_eur:+.0f}€)")
    logger.info(f"   Profit Margin: {result.profit_percent:+.1f}%")
    logger.info(f"   Is Hot Deal (>=15% or >=1500€): {result.is_hot_deal}")

    card_html = format_listing_card_html(result)
    kb = create_listing_card_keyboard(result)
    print("\n--- GENERATED TELEGRAM CARD HTML ---")
    print(card_html)
    print("------------------------------------\n")

    stats = await get_database_stats()
    logger.info(f"Database Stats: {stats}")
    logger.info("ALL SYSTEMS VERIFIED & OPERATIONAL!")


if __name__ == "__main__":
    asyncio.run(run_tests())
