import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request  # type: ignore

from database.queries import (
    get_database_stats,
    get_clicks_per_day,
    get_country_distribution,
    toggle_filter_status,
    archive_filter,
    unarchive_filter,
    get_filter_by_id
)
from engine.broadcaster import broadcast_engine
from web.auth import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API Endpoints"])


def api_auth(request: Request) -> str:
    """Ensure user is logged in for API calls."""
    admin = get_current_admin(request)
    if not admin:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return admin


@router.get("/stats")
async def get_stats_api(_admin: str = Depends(api_auth)) -> Dict[str, Any]:
    """Retrieve real-time database and system statistics."""
    return await get_database_stats()


@router.get("/charts/clicks")
async def get_clicks_chart_api(_admin: str = Depends(api_auth)) -> Dict[str, Any]:
    """Retrieve 7-day daily click analytics for Chart.js."""
    clicks_data = await get_clicks_per_day(days=7)
    labels = [row["click_date"] for row in clicks_data]
    counts = [row["click_count"] for row in clicks_data]
    return {
        "labels": labels,
        "counts": counts
    }


@router.get("/charts/countries")
async def get_countries_chart_api(_admin: str = Depends(api_auth)) -> Dict[str, Any]:
    """Retrieve target countries distribution for Chart.js."""
    dist = await get_country_distribution()
    return {
        "labels": list(dist.keys()),
        "counts": list(dist.values())
    }


@router.get("/broadcast/status")
async def get_broadcast_status_api(_admin: str = Depends(api_auth)) -> Dict[str, Any]:
    """Check active broadcast status with real-time counters and progress metrics."""
    return broadcast_engine.live_status


@router.post("/templates/preview")
async def preview_template_api(request: Request, _admin: str = Depends(api_auth)) -> Dict[str, Any]:
    """Render sample car listing card preview with provided custom template."""
    try:
        body = await request.json()
        tpl = body.get("template", "")
        is_hd = bool(body.get("is_hot_deal", False))
        
        from engine.arbitrage import ArbitrageResult
        from scrapers.base_scraper import CarListing
        from bot.views.listing_card import format_listing_card_html

        dummy_listing = CarListing(
            external_id="preview_demo_1",
            platform="otomoto",
            country="DE",
            title="BMW 530d xDrive M-Sport",
            make="BMW",
            model="5 Series",
            year=2021,
            price_eur=28500.0,
            url="https://example.com/demo-car",
            mileage_km=84500,
            fuel_type="Diesel",
            transmission="Automatic",
            engine_size="3.0L",
            location="Munich, Germany"
        )
        dummy_res = ArbitrageResult(
            listing=dummy_listing,
            listing_price_pln=122550.0,
            poland_median_pln=154000.0,
            poland_median_eur=35800.0,
            transport_cost_pln=2500.0,
            transport_cost_eur=580.0,
            akcyza_rate=0.186,
            akcyza_cost_pln=22794.0,
            akcyza_cost_eur=5300.0,
            registration_cost_pln=1200.0,
            registration_cost_eur=280.0,
            total_landed_cost_pln=149044.0,
            total_landed_cost_eur=34660.0,
            profit_pln=4956.0,
            profit_eur=1140.0,
            profit_percent=3.2,
            is_hot_deal=is_hd,
            sample_count=24
        )
        rendered = format_listing_card_html(dummy_res, is_hot_deal_feed=is_hd, custom_template=tpl)
        return {"success": True, "html": rendered}
    except Exception as e:
        logger.error(f"Failed to render preview: {e}")
        return {"success": False, "error": str(e)}


@router.get("/makes/{make_id}/models")
async def get_models_by_make_api(make_id: int, _admin: str = Depends(api_auth)) -> Dict[str, Any]:
    """Retrieve models for a specific car make."""
    from database.queries import get_car_models_by_make_id
    models = await get_car_models_by_make_id(make_id)
    return {"models": models}


@router.post("/topics/{filter_id}/toggle")
async def toggle_topic_api(filter_id: int, _admin: str = Depends(api_auth)) -> Dict[str, Any]:
    """Toggle a topic filter status (Active <-> Paused)."""
    flt = await get_filter_by_id(filter_id)
    if not flt:
        raise HTTPException(status_code=404, detail="Filter not found")

    new_status = await toggle_filter_status(filter_id)
    return {
        "success": True,
        "filter_id": filter_id,
        "is_active": new_status
    }


@router.post("/topics/{filter_id}/archive")
async def archive_topic_api(request: Request, filter_id: int, _admin: str = Depends(api_auth)) -> Dict[str, Any]:
    """Archive a topic and optionally close Telegram forum topic."""
    flt = await get_filter_by_id(filter_id)
    if not flt:
        raise HTTPException(status_code=404, detail="Filter not found")

    # If bot is attached to app state, try closing forum topic in Telegram
    bot = getattr(request.app.state, "bot", None)
    topic_id = flt.get("topic_id")
    if bot and topic_id and topic_id > 0:
        try:
            from config.settings import settings
            await bot.close_forum_topic(chat_id=settings.GROUP_CHAT_ID, message_thread_id=topic_id)
        except Exception as e:
            logger.debug(f"Could not close Telegram topic {topic_id}: {e}")

    await archive_filter(filter_id)
    return {
        "success": True,
        "filter_id": filter_id,
        "is_archived": 1
    }

