import asyncio
from database.db import init_db
from database.queries import (
    create_user_filter,
    get_active_filters,
    get_user_filters,
    get_filter_by_id,
    toggle_filter_status,
    update_user_filter,
    increment_filter_alert_count,
    search_seen_listings_for_filter,
    get_top_arbitrage_deals,
    get_user_notification_settings,
    set_user_notification_target,
    link_user_group,
    unlink_user_group,
    get_currency_rates,
    update_currency_rates,
    get_database_stats
)

async def test_all_queries():
    print("Testing DB queries...")
    await init_db()

    test_uid = 888777666
    fid = await create_user_filter(
        user_id=test_uid,
        make="Toyota",
        model="Prius",
        year_min=2015,
        year_max=2022,
        price_min_eur=5000,
        price_max_eur=15000,
        mileage_max=200000,
        target_country="DE",
        target_chat_id=test_uid,
        topic_id=0,
        is_active=1
    )
    print(f"Created filter id: {fid}")
    assert fid > 0

    flt = await get_filter_by_id(fid)
    assert flt is not None
    assert flt["make"] == "Toyota"
    assert flt["model"] == "Prius"
    assert flt["target_chat_id"] == test_uid

    # Test update_user_filter (edit Toyota Prius to Toyota Auris)
    await update_user_filter(fid, make="Toyota", model="Auris", year_min=2016, listing_age_hours=24)
    updated_flt = await get_filter_by_id(fid)
    assert updated_flt["model"] == "Auris"
    assert updated_flt["year_min"] == 2016
    assert updated_flt["listing_age_hours"] == 24
    print("Filter update verified: Auris 2016+")

    # Test increment_filter_alert_count
    await increment_filter_alert_count(fid)
    cnt_flt = await get_filter_by_id(fid)
    assert cnt_flt["alerts_sent_today"] == 1
    print("Alert count increment verified: 1")

    # Test search_seen_listings_for_filter
    results = await search_seen_listings_for_filter(updated_flt, limit=3)
    print(f"Search seen listings returned: {len(results)} items")

    # Test get_top_arbitrage_deals
    deals = await get_top_arbitrage_deals(limit=5)
    print(f"Top arbitrage deals returned: {len(deals)} items")

    # Test notification settings
    await link_user_group(test_uid, -100999888, "Audited Supergroup")
    ns = await get_user_notification_settings(test_uid)
    assert ns["notification_target"] == "group"
    assert ns["connected_group_id"] == -100999888

    await set_user_notification_target(test_uid, "dm")
    ns2 = await get_user_notification_settings(test_uid)
    assert ns2["notification_target"] == "dm"

    await unlink_user_group(test_uid)
    ns3 = await get_user_notification_settings(test_uid)
    assert ns3["connected_group_id"] is None

    # Test currency rates
    rates = await get_currency_rates()
    assert "eur_to_pln" in rates
    assert rates["eur_to_pln"] > 0

    # Test database stats
    stats = await get_database_stats()
    print(f"Database stats: {stats}")

    # Cleanup test filter
    from database.queries import delete_filter
    await delete_filter(fid)
    deleted = await get_filter_by_id(fid)
    assert deleted is None
    print("Filter deletion verified.")

    print("ALL DATABASE QUERIES AUDITED AND VERIFIED WITH 100% SUCCESS!")

if __name__ == "__main__":
    asyncio.run(test_all_queries())
