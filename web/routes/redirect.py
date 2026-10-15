import hashlib
import logging
from typing import Optional
from urllib.parse import quote, unquote

from fastapi import APIRouter, Request, Query  # type: ignore
from fastapi.responses import RedirectResponse, PlainTextResponse  # type: ignore

from database.queries import record_click, get_ad_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Redirect Gateway"])


def get_client_ip(request: Request) -> str:
    """Extract real client IP considering forward headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def get_device_summary(user_agent: str) -> str:
    """Classify user agent into Mobile or Desktop."""
    ua = user_agent.lower()
    if any(m in ua for m in ["iphone", "android", "mobile", "ipad"]):
        return "Mobile"
    return "Desktop"


@router.get("/r/{listing_id}")
@router.get("/r/")
async def handle_click_redirect(
    request: Request,
    listing_id: Optional[str] = None,
    target: Optional[str] = Query(None, description="Destination URL"),
    topic: Optional[int] = Query(None, description="Source Telegram topic ID"),
    ref: Optional[str] = Query("tg_bot", description="Referral source")
):
    """
    Click Gateway & Tracking Endpoint.
    Records click into click_analytics and redirects user to target destination.
    """
    raw_target = target or ""
    if not raw_target:
        # Fallback if target missing
        return PlainTextResponse("No redirect target specified.", status_code=400)

    # Clean destination URL
    final_destination = unquote(raw_target)
    if not final_destination.startswith("http://") and not final_destination.startswith("https://"):
        final_destination = "https://" + final_destination

    # Check custom affiliate network replacement
    try:
        ads = await get_ad_settings()
        custom_affiliate = (ads.get("custom_affiliate_url") or "").strip()
        if custom_affiliate and custom_affiliate.startswith("http"):
            sep = "&" if "?" in custom_affiliate else "?"
            final_destination = f"{custom_affiliate}{sep}url={quote(final_destination)}&ref={ref}"
    except Exception as e:
        logger.debug(f"Affiliate formatting note: {e}")

    # Track click
    ip = get_client_ip(request)
    ip_hash = hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]
    user_agent = request.headers.get("user-agent", "")
    device = get_device_summary(user_agent)
    ua_recorded = f"{device} | {user_agent[:120]}"

    try:
        await record_click(
            listing_id=listing_id,
            source_topic_id=topic,
            target_url=final_destination,
            ip_hash=ip_hash,
            user_agent=ua_recorded
        )
        logger.info(f"[CLICK] Listing: {listing_id} | Topic: {topic} | Device: {device} -> {final_destination[:60]}...")
    except Exception as click_err:
        logger.warning(f"Failed to record click in analytics: {click_err}")

    return RedirectResponse(url=final_destination, status_code=302)
