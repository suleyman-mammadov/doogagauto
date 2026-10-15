from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING
from urllib.parse import quote

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton  # type: ignore

if TYPE_CHECKING:
    from engine.arbitrage import ArbitrageResult
from scrapers.base_scraper import CarListing

FLAG_MAP = {
    "DE": "🇩🇪 Germany",
    "FR": "🇫🇷 France",
    "IT": "🇮🇹 Italy",
    "LT": "🇱🇹 Lithuania",
    "LV": "🇱🇻 Latvia",
    "EE": "🇪🇪 Estonia",
    "SK": "🇸🇰 Slovakia",
    "CZ": "🇨🇿 Czechia",
    "NL": "🇳🇱 Netherlands",
    "BE": "🇧🇪 Belgium",
    "AT": "🇦🇹 Austria",
    "ES": "🇪🇸 Spain",
    "SE": "🇸🇪 Sweden",
    "HU": "🇭🇺 Hungary",
    "SI": "🇸🇮 Slovenia",
    "HR": "🇭🇷 Croatia",
    "PL": "🇵🇱 Poland"
}

# Module-level cache for ad settings to allow sync formatting in scheduler
_CACHED_AD_SETTINGS: Dict[str, Any] = {
    "is_redirect_enabled": 0,
    "redirect_base_url": "",
    "sponsor_text": "",
    "sponsor_button_name": "",
    "sponsor_button_url": ""
}

# Module-level cache for custom message card templates
_CACHED_TEMPLATES: Dict[str, str] = {
    "standard_template": "",
    "hot_deal_template": ""
}


def set_cached_ad_settings(ad_dict: Dict[str, Any]):
    """Update active ad settings in memory cache."""
    global _CACHED_AD_SETTINGS
    _CACHED_AD_SETTINGS = dict(ad_dict)


def get_cached_ad_settings() -> Dict[str, Any]:
    """Retrieve active ad settings from memory cache."""
    return _CACHED_AD_SETTINGS


def set_cached_templates(tpl_dict: Dict[str, str]):
    """Update active message templates in memory cache."""
    global _CACHED_TEMPLATES
    _CACHED_TEMPLATES = dict(tpl_dict)


def get_cached_templates() -> Dict[str, str]:
    """Retrieve active message templates from memory cache."""
    return _CACHED_TEMPLATES


def safe_format_template(template: str, context: Dict[str, Any]) -> str:
    """Safely format template using context dictionary without crashing on missing keys."""
    import re
    def replace_var(match):
        key = match.group(1)
        return str(context.get(key, f"{{{key}}}"))
    return re.sub(r"\{([a-zA-Z0-9_]+)\}", replace_var, template)


def format_listing_card_html(
    result: ArbitrageResult,
    is_hot_deal_feed: bool = False,
    ad_settings: Optional[Dict[str, Any]] = None,
    custom_template: Optional[str] = None
) -> str:
    """Format rich HTML message for car listing card with monetization and template support."""
    ads = ad_settings or _CACHED_AD_SETTINGS
    listing: CarListing = result.listing
    country_badge = FLAG_MAP.get(listing.country.upper(), f"🇪🇺 {listing.country}")
    
    header_badge = "🔥 <b>HOT DEAL | HIGH ARBITRAGE</b>" if (result.is_hot_deal or is_hot_deal_feed) else "⚡ <b>NEW ARBITRAGE OPPORTUNITY</b>"
    
    specs = []
    if listing.year:
        specs.append(f"📅 {listing.year}")
    if listing.mileage_km:
        specs.append(f"🛣️ {listing.mileage_km:,} km".replace(",", " "))
    if listing.fuel_type:
        specs.append(f"⛽ {listing.fuel_type}")
    if listing.transmission:
        specs.append(f"🕹️ {listing.transmission}")
    if listing.engine_size:
        specs.append(f"⚙️ {listing.engine_size}")
    if listing.location:
        specs.append(f"📍 {listing.location}")
    
    specs_text = " | ".join(specs) if specs else "📍 Info not specified"

    local_price_str = ""
    if listing.currency_local != "EUR" and listing.price_local:
        local_price_str = f" ({listing.price_local:,.0f} {listing.currency_local})".replace(",", " ")

    akcyza_percent_str = f"{result.akcyza_rate * 100:.1f}%"

    profit_sign = "+" if result.profit_pln > 0 else ""
    profit_emoji = "🟢" if result.profit_pln > 0 else "🔴"
    sponsor_text = (ads.get("sponsor_text") or "").strip()

    context = {
        "header_badge": header_badge,
        "country_badge": country_badge,
        "platform": listing.platform.upper(),
        "country": listing.country,
        "title": listing.title,
        "specs_text": specs_text,
        "year": str(listing.year or ""),
        "mileage": f"{listing.mileage_km:,} km".replace(",", " ") if listing.mileage_km else "",
        "fuel_type": listing.fuel_type or "",
        "transmission": listing.transmission or "",
        "engine_size": listing.engine_size or "",
        "location": listing.location or "",
        "price_eur": f"{listing.price_eur:,.0f}".replace(",", " "),
        "local_price_str": local_price_str,
        "price_pln": f"{result.listing_price_pln:,.0f}".replace(",", " "),
        "poland_median_pln": f"{result.poland_median_pln:,.0f}".replace(",", " "),
        "poland_median_eur": f"{result.poland_median_eur:,.0f}".replace(",", " "),
        "sample_count": str(result.sample_count),
        "transport_cost_pln": f"{result.transport_cost_pln:,.0f}".replace(",", " "),
        "transport_cost_eur": f"{result.transport_cost_eur:,.0f}".replace(",", " "),
        "akcyza_percent": akcyza_percent_str,
        "akcyza_cost_pln": f"{result.akcyza_cost_pln:,.0f}".replace(",", " "),
        "akcyza_cost_eur": f"{result.akcyza_cost_eur:,.0f}".replace(",", " "),
        "registration_cost_pln": f"{result.registration_cost_pln:,.0f}".replace(",", " "),
        "registration_cost_eur": f"{result.registration_cost_eur:,.0f}".replace(",", " "),
        "total_landed_cost_pln": f"{result.total_landed_cost_pln:,.0f}".replace(",", " "),
        "total_landed_cost_eur": f"{result.total_landed_cost_eur:,.0f}".replace(",", " "),
        "profit_emoji": profit_emoji,
        "profit_sign": profit_sign,
        "profit_pln": f"{result.profit_pln:,.0f}".replace(",", " "),
        "profit_eur": f"{result.profit_eur:,.0f}".replace(",", " "),
        "profit_margin": f"{result.profit_percent:.1f}",
        "sponsor_text": sponsor_text,
        "url": listing.url
    }

    # Check custom template
    chosen_tpl = custom_template
    if not chosen_tpl:
        is_hd = (result.is_hot_deal or is_hot_deal_feed)
        chosen_tpl = _CACHED_TEMPLATES.get("hot_deal_template") if is_hd else _CACHED_TEMPLATES.get("standard_template")

    if chosen_tpl and chosen_tpl.strip():
        formatted_html = safe_format_template(chosen_tpl, context)
        # If template didn't explicitly include {sponsor_text} and sponsor_text exists, append it
        if sponsor_text and "{sponsor_text}" not in chosen_tpl and sponsor_text not in formatted_html:
            formatted_html += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 {sponsor_text}"
        return formatted_html

    # Default fallback format
    html = (
        f"{header_badge}\n"
        f"<b>Source:</b> {country_badge} ({listing.platform.upper()})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚗 <b>{listing.title}</b>\n"
        f"{specs_text}\n\n"
        f"💶 <b>Purchase Price:</b> <b>{listing.price_eur:,.0f} €</b>{local_price_str} (~{result.listing_price_pln:,.0f} PLN)\n"
        f"🇵🇱 <b>Poland Market Price (Otomoto):</b> <b>~{result.poland_median_pln:,.0f} PLN</b> (~{result.poland_median_eur:,.0f} €)\n"
        f"   <i>(Based on {result.sample_count} similar listings on Otomoto)</i>\n\n"
        f"📊 <b>Import Costs (to Poland):</b>\n"
        f" ├─ 🚚 Logistics ({listing.country}): ~{result.transport_cost_pln:,.0f} PLN (~{result.transport_cost_eur:,.0f} €)\n"
        f" ├─ 📑 Excise Tax ({akcyza_percent_str}): ~{result.akcyza_cost_pln:,.0f} PLN (~{result.akcyza_cost_eur:,.0f} €)\n"
        f" └─ 🛠️ Docs / Inspection: ~{result.registration_cost_pln:,.0f} PLN (~{result.registration_cost_eur:,.0f} €)\n"
        f"🏷️ <b>Total Landed Cost:</b> <b>~{result.total_landed_cost_pln:,.0f} PLN</b> (~{result.total_landed_cost_eur:,.0f} €)\n\n"
        f"{profit_emoji} <b>Estimated Net Profit:</b> <b>{profit_sign}{result.profit_pln:,.0f} PLN</b> ({profit_sign}{result.profit_eur:,.0f} €)\n"
        f"📈 <b>Profit Margin:</b> <b>{profit_sign}{result.profit_percent:.1f}%</b>"
    ).replace(",", " ")

    if result.is_hot_deal:
        html += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n🔥 <i>This deal is ≥15% below Poland market price or estimated net profit is ≥1 500 €!</i>"

    if sponsor_text:
        html += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 {sponsor_text}"

    return html


def create_listing_card_keyboard(
    result: ArbitrageResult,
    ad_settings: Optional[Dict[str, Any]] = None
) -> InlineKeyboardMarkup:
    """Build action buttons with optional monetization redirection and sponsor button."""
    ads = ad_settings or _CACHED_AD_SETTINGS
    original_url = result.listing.url

    # Check redirect URL masking
    if ads.get("is_redirect_enabled") and ads.get("redirect_base_url"):
        base = ads["redirect_base_url"].strip()
        if base.startswith("/"):
            from config.settings import settings
            domain = settings.WEB_BASE_URL.rstrip("/")
            base = f"{domain}{base}"

        if base.endswith("/r/") or base.endswith("/r"):
            base = f"{base.rstrip('/')}/{result.listing.external_id}"

        sep = "&" if "?" in base else "?"
        candidate_url = f"{base}{sep}target={quote(original_url, safe='')}&ref=tg_bot"

        # Telegram Bot API rejects localhost and 127.0.0.1 in inline keyboard buttons
        if "localhost" in candidate_url.lower() or "127.0.0.1" in candidate_url:
            final_url = original_url
        else:
            final_url = candidate_url
    else:
        final_url = original_url

    buttons = [
        [
            InlineKeyboardButton(text="🔗 View Listing ↗️", url=final_url)
        ]
    ]

    otomoto_link = result.otomoto_url
    if not otomoto_link:
        make_part = result.listing.make.lower()
        model_part = result.listing.model.lower() if result.listing.model else ""
        year_part = f"?search%5Bfilter_float_year%3Afrom%5D={result.listing.year}&search%5Bfilter_float_year%3Ato%5D={result.listing.year}" if result.listing.year else ""
        otomoto_link = f"https://www.otomoto.pl/osobowe/{make_part}/{model_part}{year_part}".replace("//", "/")

    buttons.append([
        InlineKeyboardButton(text="🇵🇱 Compare on Otomoto", url=otomoto_link)
    ])

    # Sponsor button integration
    s_btn_name = (ads.get("sponsor_button_name") or "").strip()
    s_btn_url = (ads.get("sponsor_button_url") or "").strip()
    if s_btn_name and s_btn_url and s_btn_url.startswith("http"):
        # Ensure sponsor button does not fail Telegram URL validation
        if not ("localhost" in s_btn_url.lower() or "127.0.0.1" in s_btn_url):
            buttons.append([
                InlineKeyboardButton(text=f"🌟 {s_btn_name}", url=s_btn_url)
            ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Aliases for backward compatibility
format_car_card_html = format_listing_card_html
create_car_card_keyboard = create_listing_card_keyboard
