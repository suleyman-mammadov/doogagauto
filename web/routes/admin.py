import sys
from pathlib import Path
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status  # type: ignore
from fastapi.responses import HTMLResponse, RedirectResponse  # type: ignore
from fastapi.templating import Jinja2Templates  # type: ignore
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton  # type: ignore

from config.settings import settings
from database.queries import (
    get_database_stats,
    get_all_filters_admin,
    get_filter_by_id,
    toggle_filter_status,
    archive_filter,
    unarchive_filter,
    update_filter_admin,
    get_ad_settings,
    update_ad_settings,
    get_recent_clicks,
    get_broadcast_campaigns,
    create_broadcast_campaign,
    update_campaign_progress,
    get_active_topics,
    get_all_topics,
    get_all_user_ids,
    verify_admin_credentials,
    change_admin_password,
    get_all_car_makes,
    add_car_make,
    delete_car_make,
    get_car_models_by_make_id,
    get_car_models_by_make_name,
    add_car_model,
    delete_car_model,
    get_bot_menu_buttons,
    update_bot_menu_button,
    get_message_templates,
    update_message_templates,
    delete_broadcast_campaign_record,
    get_proxy_settings,
    update_proxy_settings,
    record_proxy_test_result,
    get_proxy_pool,
    get_active_proxy_urls,
    bulk_insert_proxies,
    delete_proxy,
    toggle_proxy,
    clear_all_proxies,
    clear_failed_proxies,
    record_proxy_usage,
    get_proxy_pool_stats,
    get_currency_rates,
    update_currency_rates,
    fetch_live_exchange_rates,
    apply_currency_rates_to_runtime
)
from bot.views.listing_card import set_cached_ad_settings, set_cached_templates, get_cached_templates
from bot.handlers.filter_fsm import set_cached_makes_and_models
from bot.locales.texts import set_custom_button_labels
from scrapers.base_scraper import set_cached_proxy_settings
from engine.broadcaster import broadcast_engine
from web.auth import (
    create_session_token,
    get_current_admin,
    require_admin,
    SESSION_COOKIE_NAME,
    SESSION_DURATION_SECONDS
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Web Admin Panel"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


async def sync_all_caches():
    """Refresh memory caches for templates, makes/models, button labels, and proxy pool."""
    try:
        tpls = await get_message_templates()
        if tpls and (tpls.get("standard_template") or tpls.get("hot_deal_template")):
            set_cached_templates(tpls)

        p_conf = await get_proxy_settings()
        pool_urls = await get_active_proxy_urls()
        set_cached_proxy_settings(p_conf, pool_urls)

        # Currency exchange rates sync
        c_rates = await get_currency_rates()
        apply_currency_rates_to_runtime(c_rates)

        makes = await get_all_car_makes()
        if makes:
            makes_list = [m["name"] for m in makes]
            models_map = {}
            for mk in makes_list:
                mdls = await get_car_models_by_make_name(mk)
                if mdls:
                    models_map[mk.upper()] = mdls
            set_cached_makes_and_models(makes_list, models_map)

        btns = await get_bot_menu_buttons()
        if btns:
            btn_map = {}
            for b in btns:
                btn_map[b["button_key"]] = {
                    "en": b["label_en"],
                    "pl": b["label_pl"],
                    "ru": b["label_ru"]
                }
            set_custom_button_labels(btn_map)
    except Exception as e:
        logger.warning(f"Error syncing caches: {e}")



def clean_chat_id(chat_id: Any) -> str:
    """Clean chat ID for Telegram web links."""
    s = str(chat_id).strip()
    if s.startswith("-100"):
        return s[4:]
    if s.startswith("-"):
        return s[1:]
    return s.lstrip("@")


# ==============================================================================
# AUTHENTICATION (LOGIN / LOGOUT)
# ==============================================================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login form."""
    if get_current_admin(request):
        return RedirectResponse(url="/admin/", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@router.post("/login", response_class=HTMLResponse)
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authenticate admin and issue session cookie."""
    is_valid = await verify_admin_credentials(username.strip(), password.strip())
    if not is_valid:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "İstifadəçi adı və ya şifrə yanlışdır! Zəhmət olmasa yenidən yoxlayın."},
            status_code=400
        )

    response = RedirectResponse(url="/admin/", status_code=302)
    token = create_session_token(username.strip())
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_DURATION_SECONDS,
        httponly=True,
        samesite="lax"
    )
    return response


@router.post("/change-password")
async def change_password_action(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    admin_user: str = Depends(require_admin)
):
    """Change admin password securely from the Web Admin dashboard."""
    is_valid = await verify_admin_credentials(admin_user, current_password.strip())
    if not is_valid:
        return RedirectResponse(
            url="/admin/?error=Cari+%C5%9Fifr%C9%99+yanl%C4%B1%C5%9Fd%C4%B1r!",
            status_code=302
        )

    if len(new_password.strip()) < 6:
        return RedirectResponse(
            url="/admin/?error=Yeni+%C5%9Fifr%C9%99+%C9%99n+az+6+simvoldan+ibar%C9%99t+olmal%C4%B1d%C4%B1r!",
            status_code=302
        )

    if new_password.strip() != confirm_password.strip():
        return RedirectResponse(
            url="/admin/?error=Yeni+%C5%9Fifr%C9%99+v%C9%99+t%C9%99sdiqi+uy%C4%9Fun+g%C9%99lmir!",
            status_code=302
        )

    await change_admin_password(admin_user, new_password.strip())
    return RedirectResponse(
        url="/admin/?message=%E2%9C%85+Admin+%C5%9Fifr%C9%99si+u%C4%9Furla+d%C9%99yi%C5%9Fdirildi!+N%C3%B6vb%C9%99ti+giri%C5%9Fd%C9%99+yeni+%C5%9Fifr%C9%99+t%C9%99l%C9%99b+olunacaq.",
        status_code=302
    )


@router.get("/logout")
async def handle_logout():
    """Clear session and log out."""
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response


# ==============================================================================
# DASHBOARD
# ==============================================================================

@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request, admin_user: str = Depends(require_admin)):
    """Render main KPI dashboard."""
    stats = await get_database_stats()
    recent_clicks = await get_recent_clicks(limit=5)
    recent_topics = (await get_all_filters_admin())[:5]

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "admin_user": admin_user,
        "active_page": "dashboard",
        "stats": stats,
        "recent_clicks": recent_clicks,
        "recent_topics": recent_topics
    })


# ==============================================================================
# TOPICS / FILTERS MANAGEMENT
# ==============================================================================

@router.get("/topics", response_class=HTMLResponse)
async def topics_view(
    request: Request,
    search: Optional[str] = None,
    status: Optional[str] = None,
    admin_user: str = Depends(require_admin)
):
    """Render topics management table."""
    topics = await get_all_filters_admin(search=search, status=status)
    clean_id = clean_chat_id(settings.GROUP_CHAT_ID)

    return templates.TemplateResponse(request=request, name="topics.html", context={
        "admin_user": admin_user,
        "active_page": "topics",
        "topics": topics,
        "search": search,
        "status": status,
        "clean_group_id": clean_id
    })


@router.post("/topics/{filter_id}/toggle")
async def toggle_topic_status(filter_id: int, admin_user: str = Depends(require_admin)):
    """Toggle topic status between active and paused."""
    await toggle_filter_status(filter_id)
    return RedirectResponse(url="/admin/topics", status_code=302)


@router.post("/topics/{filter_id}/edit")
async def edit_topic_params(
    filter_id: int,
    price_max_eur: Optional[float] = Form(None),
    year_min: Optional[int] = Form(None),
    year_max: Optional[int] = Form(None),
    admin_notes: Optional[str] = Form(None),
    admin_user: str = Depends(require_admin)
):
    """Edit topic filter parameters."""
    await update_filter_admin(
        filter_id=filter_id,
        price_max_eur=price_max_eur,
        year_min=year_min,
        year_max=year_max,
        admin_notes=admin_notes
    )
    return RedirectResponse(url="/admin/topics", status_code=302)


@router.post("/topics/{filter_id}/archive")
async def archive_topic_action(request: Request, filter_id: int, admin_user: str = Depends(require_admin)):
    """Close Telegram forum topic and mark filter as archived."""
    flt = await get_filter_by_id(filter_id)
    if flt and flt.get("topic_id"):
        bot = getattr(request.app.state, "bot", None)
        if bot:
            try:
                await bot.close_forum_topic(
                    chat_id=settings.GROUP_CHAT_ID,
                    message_thread_id=flt["topic_id"]
                )
                logger.info(f"Closed Telegram forum topic {flt['topic_id']}")
            except Exception as e:
                logger.debug(f"Could not close Telegram topic {flt['topic_id']}: {e}")

    await archive_filter(filter_id)
    return RedirectResponse(url="/admin/topics", status_code=302)


@router.post("/topics/{filter_id}/unarchive")
async def unarchive_topic_action(filter_id: int, admin_user: str = Depends(require_admin)):
    """Restore an archived topic."""
    await unarchive_filter(filter_id)
    return RedirectResponse(url="/admin/topics", status_code=302)


# ==============================================================================
# MONETIZATION & AD SETTINGS
# ==============================================================================

@router.get("/monetization", response_class=HTMLResponse)
async def monetization_view(request: Request, saved: Optional[int] = None, admin_user: str = Depends(require_admin)):
    """Render monetization settings page."""
    ads = await get_ad_settings()
    set_cached_ad_settings(ads)

    msg = "Settings saved successfully!" if saved else None
    return templates.TemplateResponse(request=request, name="monetization.html", context={
        "admin_user": admin_user,
        "active_page": "monetization",
        "ads": ads,
        "message": msg
    })


@router.post("/monetization")
async def update_monetization_action(
    is_redirect_enabled: Optional[int] = Form(0),
    redirect_base_url: Optional[str] = Form("/r/"),
    custom_affiliate_url: Optional[str] = Form(""),
    sponsor_text: Optional[str] = Form(""),
    sponsor_button_name: Optional[str] = Form(""),
    sponsor_button_url: Optional[str] = Form(""),
    admin_user: str = Depends(require_admin)
):
    """Save ad settings, update memory cache, and redirect."""
    updated = await update_ad_settings(
        is_redirect_enabled=bool(is_redirect_enabled),
        redirect_base_url=redirect_base_url,
        custom_affiliate_url=custom_affiliate_url,
        sponsor_text=sponsor_text,
        sponsor_button_name=sponsor_button_name,
        sponsor_button_url=sponsor_button_url
    )
    set_cached_ad_settings(updated)
    return RedirectResponse(url="/admin/monetization?saved=1", status_code=302)


# ==============================================================================
# BROADCAST WIZARD
# ==============================================================================

@router.get("/broadcast", response_class=HTMLResponse)
async def broadcast_view(request: Request, admin_user: str = Depends(require_admin)):
    """Render broadcast manager page."""
    campaigns = await get_broadcast_campaigns(limit=20)
    is_running = broadcast_engine.is_running

    return templates.TemplateResponse(request=request, name="broadcast.html", context={
        "admin_user": admin_user,
        "active_page": "broadcast",
        "campaigns": campaigns,
        "is_running": is_running
    })


@router.post("/broadcast/launch")
async def launch_broadcast_action(
    request: Request,
    title: str = Form(...),
    message_text: str = Form(...),
    target_type: str = Form(...),
    image_url: Optional[str] = Form(None),
    button_name: Optional[str] = Form(None),
    button_url: Optional[str] = Form(None),
    admin_user: str = Depends(require_admin)
):
    """Create broadcast campaign and launch background worker."""
    if broadcast_engine.is_running:
        return RedirectResponse(url="/admin/broadcast", status_code=302)

    bot = getattr(request.app.state, "bot", None)
    if not bot:
        logger.error("Bot instance not available on app.state")
        return RedirectResponse(url="/admin/broadcast", status_code=302)

    # Resolve target count
    if target_type == "active_topics":
        targets = await get_active_topics()
        engine_target = "topics"
    elif target_type == "all_topics":
        targets = await get_all_topics()
        engine_target = "topics"
    else:
        targets = await get_all_user_ids()
        engine_target = "users"

    total = len(targets)
    clean_img = image_url.strip() if image_url and image_url.strip() else None
    clean_bname = button_name.strip() if button_name and button_name.strip() else None
    clean_burl = button_url.strip() if button_url and button_url.strip() else None

    # Record in broadcast campaigns table
    camp_id = await create_broadcast_campaign(
        title=title.strip(),
        message_text=message_text.strip(),
        target_type=target_type,
        total_targets=total,
        image_url=clean_img,
        button_name=clean_bname,
        button_url=clean_burl
    )

    # Build reply markup if button specified
    reply_kb = None
    if clean_bname and clean_burl and clean_burl.startswith("http"):
        reply_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=clean_bname, url=clean_burl)]
        ])

    # Admin notification chat (use settings.ADMIN_USER_IDS[0] if available)
    admin_chat_id = settings.ADMIN_USER_IDS[0] if settings.ADMIN_USER_IDS else 0

    try:
        # Start background broadcaster
        await broadcast_engine.start_broadcast(
            bot=bot,
            admin_id=1,
            admin_chat_id=admin_chat_id,
            status_message_id=0,
            target_type=engine_target,
            message_text=message_text.strip(),
            photo_file_id=clean_img,
            reply_markup=reply_kb,
            campaign_id=camp_id
        )
    except Exception as e:
        logger.error(f"Failed to start web broadcast: {e}", exc_info=True)

    return RedirectResponse(url="/admin/broadcast", status_code=302)


@router.post("/broadcast/cancel")
async def cancel_broadcast_action(admin_user: str = Depends(require_admin)):
    """Stop active broadcast."""
    broadcast_engine.request_cancel()
    return RedirectResponse(url="/admin/broadcast", status_code=302)


@router.post("/broadcast/{campaign_id}/delete-messages")
async def delete_broadcast_messages_action(
    request: Request,
    campaign_id: int,
    admin_user: str = Depends(require_admin)
):
    """Delete all sent Telegram messages for this campaign."""
    bot = getattr(request.app.state, "bot", None)
    if bot:
        try:
            await broadcast_engine.delete_campaign_messages(bot, campaign_id)
        except Exception as e:
            logger.error(f"Failed to delete campaign {campaign_id} messages from Telegram: {e}")
    return RedirectResponse(url="/admin/broadcast", status_code=302)


@router.post("/broadcast/{campaign_id}/delete")
async def delete_broadcast_campaign_action(
    campaign_id: int,
    admin_user: str = Depends(require_admin)
):
    """Delete broadcast campaign audit record and message logs."""
    try:
        await delete_broadcast_campaign_record(campaign_id)
    except Exception as e:
        logger.error(f"Failed to delete campaign record {campaign_id}: {e}")
    return RedirectResponse(url="/admin/broadcast", status_code=302)


# ==============================================================================
# ANALYTICS
# ==============================================================================

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_view(request: Request, admin_user: str = Depends(require_admin)):
    """Render click analytics table."""
    clicks = await get_recent_clicks(limit=100)
    mobile_clicks = sum(1 for c in clicks if "Mobile" in (c.get("user_agent") or ""))
    desktop_clicks = len(clicks) - mobile_clicks
    return templates.TemplateResponse(request=request, name="analytics.html", context={
        "admin_user": admin_user,
        "active_page": "analytics",
        "clicks": clicks,
        "mobile_clicks": mobile_clicks,
        "desktop_clicks": desktop_clicks
    })


# ==============================================================================
# MENU & SUBMENU EDITOR (CAR MAKES, MODELS & BUTTON LABELS)
# ==============================================================================

@router.get("/menus", response_class=HTMLResponse)
async def menus_view(request: Request, admin_user: str = Depends(require_admin)):
    """Render bot menu and filter editor page."""
    makes = await get_all_car_makes()
    buttons = await get_bot_menu_buttons()
    
    # Preload models for the first make if exists
    first_make_models = []
    if makes:
        first_make_models = await get_car_models_by_make_id(makes[0]["id"])

    return templates.TemplateResponse(request=request, name="menus.html", context={
        "admin_user": admin_user,
        "active_page": "menus",
        "makes": makes,
        "first_make_models": first_make_models,
        "buttons": buttons
    })


@router.post("/menus/makes/add")
async def add_make_action(
    request: Request,
    name: str = Form(...),
    admin_user: str = Depends(require_admin)
):
    """Add a new car make dynamically."""
    if name.strip():
        await add_car_make(name.strip())
        await sync_all_caches()
    return RedirectResponse(url="/admin/menus", status_code=302)


@router.post("/menus/makes/{make_id}/delete")
async def delete_make_action(
    make_id: int,
    admin_user: str = Depends(require_admin)
):
    """Delete a car make and all associated models."""
    await delete_car_make(make_id)
    await sync_all_caches()
    return RedirectResponse(url="/admin/menus", status_code=302)


@router.post("/menus/models/add")
async def add_model_action(
    make_id: int = Form(...),
    name: str = Form(...),
    admin_user: str = Depends(require_admin)
):
    """Add a model to a car make dynamically."""
    if name.strip() and make_id > 0:
        await add_car_model(make_id, name.strip())
        await sync_all_caches()
    return RedirectResponse(url="/admin/menus", status_code=302)


@router.post("/menus/models/{model_id}/delete")
async def delete_model_action(
    model_id: int,
    admin_user: str = Depends(require_admin)
):
    """Delete a car model dynamically."""
    await delete_car_model(model_id)
    await sync_all_caches()
    return RedirectResponse(url="/admin/menus", status_code=302)


@router.post("/menus/buttons/update")
async def update_buttons_action(
    request: Request,
    button_key: str = Form(...),
    label_en: str = Form(...),
    label_pl: str = Form(...),
    label_ru: str = Form(...),
    admin_user: str = Depends(require_admin)
):
    """Update localized button text across languages."""
    await update_bot_menu_button(
        button_key=button_key.strip(),
        label_en=label_en.strip(),
        label_pl=label_pl.strip(),
        label_ru=label_ru.strip()
    )
    await sync_all_caches()
    return RedirectResponse(url="/admin/menus", status_code=302)


# ==============================================================================
# CAR LISTING CARD MESSAGE TEMPLATES
# ==============================================================================

@router.get("/templates", response_class=HTMLResponse)
async def templates_view(request: Request, admin_user: str = Depends(require_admin)):
    """Render car alert message card template editor."""
    tpls = await get_message_templates()
    is_saved = request.query_params.get("saved") == "1"
    is_reset = request.query_params.get("reset") == "1"

    return templates.TemplateResponse(request=request, name="templates.html", context={
        "admin_user": admin_user,
        "active_page": "templates",
        "templates": tpls,
        "is_saved": is_saved,
        "is_reset": is_reset
    })


@router.post("/templates")
async def save_templates_action(
    standard_template: str = Form(...),
    hot_deal_template: str = Form(...),
    admin_user: str = Depends(require_admin)
):
    """Save custom card templates to database."""
    await update_message_templates(
        standard_template=standard_template.strip(),
        hot_deal_template=hot_deal_template.strip()
    )
    await sync_all_caches()
    return RedirectResponse(url="/admin/templates?saved=1", status_code=302)


@router.post("/templates/reset")
async def reset_templates_action(admin_user: str = Depends(require_admin)):
    """Reset message card templates to system default."""
    default_standard_tpl = (
        "{header_badge}\n"
        "<b>Source:</b> {country_badge} ({platform})\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚗 <b>{title}</b>\n"
        "{specs_text}\n\n"
        "💶 <b>Purchase Price:</b> <b>{price_eur} €</b>{local_price_str} (~{price_pln} PLN)\n"
        "🇵🇱 <b>Poland Market Price (Otomoto):</b> <b>~{poland_median_pln} PLN</b> (~{poland_median_eur} €)\n"
        "   <i>(Based on {sample_count} similar listings on Otomoto)</i>\n\n"
        "📊 <b>Import Costs (to Poland):</b>\n"
        " ├─ 🚚 Logistics ({country}): ~{transport_cost_pln} PLN (~{transport_cost_eur} €)\n"
        " ├─ 📑 Excise Tax ({akcyza_percent}): ~{akcyza_cost_pln} PLN (~{akcyza_cost_eur} €)\n"
        " └─ 🛠️ Docs / Inspection: ~{registration_cost_pln} PLN (~{registration_cost_eur} €)\n"
        "🏷️ <b>Total Landed Cost:</b> <b>~{total_landed_cost_pln} PLN</b> (~{total_landed_cost_eur} €)\n\n"
        "{profit_emoji} <b>Estimated Net Profit:</b> <b>{profit_sign}{profit_pln} PLN</b> ({profit_sign}{profit_eur} €)\n"
        "📈 <b>Profit Margin:</b> <b>{profit_sign}{profit_margin}%</b>"
    )
    default_hot_deal_tpl = (
        default_standard_tpl + "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 <i>This deal is ≥15% below Poland market price or estimated net profit is ≥1 500 €!</i>"
    )
    await update_message_templates(default_standard_tpl, default_hot_deal_tpl)
    await sync_all_caches()
    return RedirectResponse(url="/admin/templates?reset=1", status_code=302)


# ==============================================================================
# ==============================================================================
# PROXY POOL & NETWORK MANAGEMENT (100 - 1000+ ROTATING PROXIES)
# ==============================================================================

def mask_proxy_display(url: str) -> str:
    """Mask proxy password for secure UI rendering."""
    if not url:
        return ""
    if "@" in url:
        try:
            proto, rest = url.split("://", 1)
            cred, host = rest.split("@", 1)
            user = cred.split(":")[0] if ":" in cred else cred
            return f"{proto}://{user}:••••@{host}"
        except Exception:
            return url
    return url


@router.get("/proxies", response_class=HTMLResponse)
async def proxies_view(
    request: Request,
    message: Optional[str] = None,
    error: Optional[str] = None,
    admin_user: str = Depends(require_admin)
):
    """Render Proxy Management Dashboard with bulk pool list, real-time stats, and routing matrix."""
    proxy_conf = await get_proxy_settings()
    pool_stats = await get_proxy_pool_stats()
    raw_pool = await get_proxy_pool(limit=1000)

    # Format proxies for UI
    pool = []
    for item in raw_pool:
        p_dict = dict(item)
        p_dict["masked_url"] = mask_proxy_display(p_dict.get("proxy_url", ""))
        pool.append(p_dict)

    platforms = [
        {"id": "mobile_de", "name": "Mobile.de", "country": "🇩🇪 Germany", "level": "High (Akamai Bot Manager)", "is_protected": True},
        {"id": "leboncoin_fr", "name": "Leboncoin.fr", "country": "🇫🇷 France", "level": "High (DataDome)", "is_protected": True},
        {"id": "sauto_cz", "name": "Sauto.cz", "country": "🇨🇿 Czechia", "level": "Medium (Seznam CMP Wall)", "is_protected": True},
        {"id": "kleinanzeigen_de", "name": "Kleinanzeigen.de", "country": "🇩🇪 Germany", "level": "Direct HTML (No Proxy Needed)", "is_protected": False},
        {"id": "autoplius_lt", "name": "Autoplius.lt", "country": "🇱🇹 Lithuania", "level": "Direct HTML (No Proxy Needed)", "is_protected": False},
        {"id": "ss_latvia", "name": "SS.com", "country": "🇱🇻 Latvia", "level": "Direct HTML (No Proxy Needed)", "is_protected": False},
        {"id": "bazos_sk", "name": "Bazos.sk", "country": "🇸🇰 Slovakia", "level": "Direct HTML (No Proxy Needed)", "is_protected": False},
        {"id": "bazos_cz", "name": "Bazos.cz", "country": "🇨🇿 Czechia", "level": "Direct HTML (No Proxy Needed)", "is_protected": False},
        {"id": "subito_it", "name": "Subito.it", "country": "🇮🇹 Italy", "level": "Direct HTML (No Proxy Needed)", "is_protected": False},
    ]

    is_enabled = proxy_conf.get("is_enabled", False)
    apply_mode = proxy_conf.get("apply_mode", "protected_only")
    strategy = proxy_conf.get("rotation_strategy", "round_robin")
    has_proxies = pool_stats["active"] > 0 or bool(proxy_conf.get("proxy_url"))

    for p in platforms:
        if is_enabled and has_proxies:
            strategy_name = "Round-Robin" if strategy == "round_robin" else "Random IP"
            active_info = f"{pool_stats['active']} IP Pool ({strategy_name})" if pool_stats['active'] > 0 else "Single Proxy"
            if apply_mode == "all":
                p["route_status"] = f"Rotating ({active_info})"
                p["route_badge"] = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                p["icon"] = "fa-shield-halved text-emerald-400"
            elif apply_mode == "protected_only" and p["is_protected"]:
                p["route_status"] = f"Protected ({active_info})"
                p["route_badge"] = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                p["icon"] = "fa-shield-halved text-emerald-400"
            else:
                p["route_status"] = "Direct IP (Ultra-Fast)"
                p["route_badge"] = "bg-blue-500/10 text-blue-400 border-blue-500/20"
                p["icon"] = "fa-bolt text-blue-400"
        else:
            p["route_status"] = "Direct IP (Local)"
            p["route_badge"] = "bg-slate-800 text-slate-400 border-slate-700"
            p["icon"] = "fa-globe text-slate-500"

    return templates.TemplateResponse(request=request, name="proxies.html", context={
        "request": request,
        "admin_user": admin_user,
        "active_page": "proxies",
        "proxy": proxy_conf,
        "stats": pool_stats,
        "proxy_pool": pool,
        "platforms": platforms,
        "message": message,
        "error": error
    })


@router.post("/proxies/save")
async def save_proxy_settings_action(
    is_enabled: Optional[str] = Form(None),
    proxy_url: str = Form(""),
    apply_mode: str = Form("protected_only"),
    rotation_strategy: str = Form("round_robin"),
    admin_user: str = Depends(require_admin)
):
    """Save proxy configuration to DB and synchronize active in-memory scraper cache."""
    enabled_bool = is_enabled in ("1", "true", "on", "yes")
    updated = await update_proxy_settings(
        is_enabled=enabled_bool,
        proxy_url=proxy_url.strip(),
        apply_mode=apply_mode.strip(),
        rotation_strategy=rotation_strategy.strip()
    )
    pool_urls = await get_active_proxy_urls()
    set_cached_proxy_settings(updated, pool_urls)
    return RedirectResponse(
        url="/admin/proxies?message=Proxy+t%C9%99nziml%C9%99m%C9%99l%C9%99ri+u%C4%9Furla+yadda+saxlan%C4%B1ld%C4%B1!",
        status_code=302
    )


@router.post("/proxies/bulk-import")
async def bulk_import_proxies_action(
    proxy_list: str = Form(""),
    auto_enable: Optional[str] = Form(None),
    admin_user: str = Depends(require_admin)
):
    """Bulk import 100 to 1000+ proxies into the rotation pool."""
    raw = proxy_list.strip()
    if not raw:
        return RedirectResponse(
            url="/admin/proxies?error=Z%C9%99hm%C9%99t+olmasa+proksil%C9%99ri+daxil+edin!",
            status_code=302
        )

    res = await bulk_insert_proxies(raw)
    added = res["added"]
    dups = res["duplicates"]
    invalid = res["invalid"]

    if auto_enable in ("1", "true", "on", "yes") and added > 0:
        await update_proxy_settings(is_enabled=True)

    pool_urls = await get_active_proxy_urls()
    p_conf = await get_proxy_settings()
    set_cached_proxy_settings(p_conf, pool_urls)

    msg = f"Hovuza+{added}+%C9%99d%C9%99d+proxy+%C9%99lav%C9%99+edildi!+({dups}+t%C9%99krar,+{invalid}+yarars%C4%B1z)"
    return RedirectResponse(url=f"/admin/proxies?message={msg}", status_code=302)


@router.post("/proxies/{proxy_id}/toggle")
async def toggle_proxy_action(
    proxy_id: int,
    admin_user: str = Depends(require_admin)
):
    """Toggle single proxy active status."""
    new_state = await toggle_proxy(proxy_id)
    pool_urls = await get_active_proxy_urls()
    p_conf = await get_proxy_settings()
    set_cached_proxy_settings(p_conf, pool_urls)
    status_str = "aktivl%C9%99%C5%9Fdirildi" if new_state else "deaktiv+edildi"
    return RedirectResponse(url=f"/admin/proxies?message=Proxy+{status_str}!", status_code=302)


@router.post("/proxies/{proxy_id}/delete")
async def delete_proxy_action(
    proxy_id: int,
    admin_user: str = Depends(require_admin)
):
    """Remove single proxy from pool."""
    await delete_proxy(proxy_id)
    pool_urls = await get_active_proxy_urls()
    p_conf = await get_proxy_settings()
    set_cached_proxy_settings(p_conf, pool_urls)
    return RedirectResponse(url="/admin/proxies?message=Proxy+hovuzdan+silindi!", status_code=302)


@router.post("/proxies/clear-all")
async def clear_all_proxies_action(
    admin_user: str = Depends(require_admin)
):
    """Wipe out all proxies from pool."""
    cnt = await clear_all_proxies()
    pool_urls = await get_active_proxy_urls()
    p_conf = await get_proxy_settings()
    set_cached_proxy_settings(p_conf, pool_urls)
    return RedirectResponse(url=f"/admin/proxies?message=B%C3%BCt%C3%BCn+{cnt}+%C9%99d%C9%99d+proxy+silindi!", status_code=302)


@router.post("/proxies/clear-failed")
async def clear_failed_proxies_action(
    max_failures: int = Form(3),
    admin_user: str = Depends(require_admin)
):
    """Remove failed proxies that exceeded failure threshold."""
    cnt = await clear_failed_proxies(max_failures)
    pool_urls = await get_active_proxy_urls()
    p_conf = await get_proxy_settings()
    set_cached_proxy_settings(p_conf, pool_urls)
    return RedirectResponse(url=f"/admin/proxies?message={cnt}+%C9%99d%C9%99d+x%C9%99tal%C4%B1+proxy+t%C9%99mizl%C9%99ndi!", status_code=302)


@router.post("/proxies/test")
async def test_proxy_action(
    proxy_url: Optional[str] = Form(None),
    admin_user: str = Depends(require_admin)
):
    """Live test proxy latency and external IP connectivity via curl_cffi."""
    import time
    from curl_cffi.requests import AsyncSession

    target_proxy = (proxy_url or "").strip()
    if not target_proxy:
        pool_urls = await get_active_proxy_urls()
        if pool_urls:
            target_proxy = pool_urls[0]
        else:
            conf = await get_proxy_settings()
            target_proxy = conf.get("proxy_url", "").strip()

    if not target_proxy:
        return RedirectResponse(
            url="/admin/proxies?error=Yoxlamaq+%C3%BC%C3%A7%C3%BCn+hovuzda+he%C3%A7+bir+proxy+yoxdur!",
            status_code=302
        )

    start_time = time.time()
    try:
        proxies = {"http": target_proxy, "https": target_proxy}
        async with AsyncSession(impersonate="chrome120", timeout=12, proxies=proxies) as s:
            r = await s.get("https://api.ipify.org?format=json")
            latency_ms = int((time.time() - start_time) * 1000)
            if r.status_code == 200:
                data = r.json()
                detected_ip = data.get("ip", "Unknown")
                try:
                    await record_proxy_test_result(
                        test_status="success",
                        last_tested_ip=detected_ip,
                        last_latency_ms=latency_ms
                    )
                    await record_proxy_usage(target_proxy, success=True, latency_ms=latency_ms)
                    conf = await get_proxy_settings()
                    pool_urls = await get_active_proxy_urls()
                    set_cached_proxy_settings(conf, pool_urls)
                except Exception:
                    pass
                return RedirectResponse(
                    url=f"/admin/proxies?message=%E2%9C%85+Proxy+ba%C4%9Flant%C4%B1s%C4%B1+u%C4%9Furludur!+Xarici+IP:+{detected_ip}+(Gecikm%C9%99:+{latency_ms}ms)",
                    status_code=302
                )
            else:
                try:
                    await record_proxy_test_result(
                        test_status="failed",
                        last_tested_ip=f"Status {r.status_code}",
                        last_latency_ms=latency_ms
                    )
                    await record_proxy_usage(target_proxy, success=False, error=f"Status {r.status_code}")
                except Exception:
                    pass
                return RedirectResponse(
                    url=f"/admin/proxies?error=%E2%9D%8C+Proxy+cavab+verm%C9%99di+(Status+{r.status_code})",
                    status_code=302
                )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        err_msg = str(e)[:90].replace("&", "+").replace("=", "+").replace("%", "+")
        try:
            await record_proxy_test_result(
                test_status="failed",
                last_tested_ip="Connection Error",
                last_latency_ms=latency_ms
            )
            await record_proxy_usage(target_proxy, success=False, error=str(e)[:50])
        except Exception:
            pass
        return RedirectResponse(
            url=f"/admin/proxies?error=%E2%9D%8C+Proxy+ba%C4%9Flant%C4%B1+x%C9%99tas%C4%B1:+{err_msg}",
            status_code=302
        )


# ==============================================================================
# CURRENCY EXCHANGE RATES MANAGEMENT (MANUAL & LIVE ECB SYNC)
# ==============================================================================

@router.get("/currency", response_class=HTMLResponse)
async def currency_view(
    request: Request,
    message: Optional[str] = None,
    error: Optional[str] = None,
    admin_user: str = Depends(require_admin)
):
    """Render Currency Exchange Rates Dashboard with manual and live ECB sync."""
    rates = await get_currency_rates()

    eur_to_pln = rates.get("eur_to_pln", 4.30)
    czk_to_eur = rates.get("czk_to_eur", 0.040)
    eur_to_czk = rates.get("eur_to_czk", 25.0)
    eur_to_usd = rates.get("eur_to_usd", 1.08)

    sample_car_eur = 15000
    sample_car_pln = round(sample_car_eur * eur_to_pln, 2)
    sample_czk_car = 350000
    sample_czk_to_eur = round(sample_czk_car * czk_to_eur, 2)

    return templates.TemplateResponse(request=request, name="currency.html", context={
        "request": request,
        "admin_user": admin_user,
        "active_page": "currency",
        "rates": rates,
        "sample_car_eur": sample_car_eur,
        "sample_car_pln": sample_car_pln,
        "sample_czk_car": sample_czk_car,
        "sample_czk_to_eur": sample_czk_to_eur,
        "message": message,
        "error": error
    })


@router.post("/currency/save")
async def save_currency_rates_action(
    eur_to_pln: float = Form(...),
    czk_to_eur: float = Form(...),
    eur_to_czk: Optional[float] = Form(None),
    eur_to_usd: Optional[float] = Form(None),
    auto_sync: Optional[str] = Form(None),
    admin_user: str = Depends(require_admin)
):
    """Manually update currency exchange rates from Admin Panel."""
    auto_bool = auto_sync in ("1", "true", "on", "yes")
    updated = await update_currency_rates(
        eur_to_pln=float(eur_to_pln),
        czk_to_eur=float(czk_to_eur),
        eur_to_czk=float(eur_to_czk) if eur_to_czk else None,
        eur_to_usd=float(eur_to_usd) if eur_to_usd else None,
        auto_sync=auto_bool,
        source="Admin Panel (Əllə)"
    )
    apply_currency_rates_to_runtime(updated)
    return RedirectResponse(
        url="/admin/currency?message=Valyuta+m%C9%99z%C9%99nn%C9%99l%C9%99ri+u%C4%9Furla+yadda+saxlan%C4%B1ld%C4%B1+v%C9%99+skraperl%C9%99r%C9%99+t%C9%99tbiq+edildi!",
        status_code=302
    )


@router.post("/currency/sync-live")
async def sync_live_currency_action(
    admin_user: str = Depends(require_admin)
):
    """Fetch live exchange rates from European Central Bank (ECB) via public API."""
    result = await fetch_live_exchange_rates()
    if result.get("success"):
        rates = result["rates"]
        apply_currency_rates_to_runtime(rates)
        msg = f"%E2%9C%85+Avropa+M%C9%99rk%C9%99zi+Bank%C4%B1+(ECB)+m%C9%99z%C9%99nn%C9%99l%C9%99ri+u%C4%9Furla+%C3%A7%C9%99kildi!+(EUR/PLN:+{rates['eur_to_pln']},+CZK/EUR:+{rates['czk_to_eur']})"
        return RedirectResponse(url=f"/admin/currency?message={msg}", status_code=302)
    else:
        err = result.get("error", "Bilinməyən xəta")
        err_enc = err.replace("&", "+").replace("=", "+").replace("%", "+")
        return RedirectResponse(url=f"/admin/currency?error=%E2%9D%8C+{err_enc}", status_code=302)


