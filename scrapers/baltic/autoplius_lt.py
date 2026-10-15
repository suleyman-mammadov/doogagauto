import re
import logging
from typing import List, Optional, Dict, Any
from selectolax.lexbor import LexborHTMLParser as HTMLParser  # type: ignore

from scrapers.base_scraper import BaseScraper, CarListing
from config.settings import settings

logger = logging.getLogger(__name__)


class AutopliusLtScraper(BaseScraper):
    name = "autoplius_lt"
    country = "LT"
    interval_seconds = settings.AUTOPLIUS_LT_INTERVAL
    protection_level = 2  # Level 2: Medium/Cookie, Chrome TLS Impersonation

    BASE_URL = "https://en.autoplius.lt"
    SEARCH_URL = "https://en.autoplius.lt/ads/used-cars?order_by=created_date&order_direction=desc"

    async def scrape(self, filters: Optional[List[Dict[str, Any]]] = None) -> List[CarListing]:
        """Scrape latest used car ads from Autoplius.lt (Lithuania)."""
        html = await self.fetch(self.SEARCH_URL)
        if not html:
            html = await self.fetch("https://en.autoplius.lt/ads/used-cars")
        if not html:
            logger.warning("[Autoplius.lt] Failed to fetch cars page.")
            return []

        parser = HTMLParser(html)
        listings: List[CarListing] = []

        cards = parser.css("a.announcement-item, div.announcement-item")
        if not cards:
            cards = parser.css(".auto-lists .item-wrapper, div.list-item")

        for card in cards[:30]:  # Delta-scanning: top newest listings
            try:
                # Link
                link_el = card if card.tag == "a" else card.css_first("a[href*='/ads/'], a")
                if not link_el:
                    continue

                href = link_el.attributes.get("href", "")
                if not href or "/ads/" not in href:
                    continue

                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                id_match = re.search(r"-(\d+)\.html", full_url)
                external_id = f"autoplius_{id_match.group(1)}" if id_match else f"autoplius_{hash(full_url)}"

                # Title
                title_el = card.css_first(".announcement-body-heading, .item-title, .announcement-title, h2, h3")
                title = self.clean_text(title_el.text()) if title_el else ""
                if not title:
                    title = "Auto Listing"

                # Image
                img_el = card.css_first("img")
                image_url = None
                if img_el:
                    image_url = img_el.attributes.get("src") or img_el.attributes.get("data-src")

                # Price (EUR)
                price_el = card.css_first(".pricing-container strong, .announcement-pricing-info strong, .description-price, .announcement-pricing, .price")
                price_text = self.clean_text(price_el.text()) if price_el else ""
                price_eur = None
                if price_text:
                    clean_digits = re.sub(r"[^\d]", "", price_text)
                    if clean_digits:
                        price_eur = float(clean_digits)

                if not price_eur:
                    # Fallback to scanning text for currency
                    card_txt = card.text()
                    m_price = re.search(r"(\d{1,3}(?:[ \.]\d{3})*|\d+)\s*€", card_txt)
                    if m_price:
                        clean_p = re.sub(r"[^\d]", "", m_price.group(1))
                        if clean_p and int(clean_p) >= 100:
                            price_eur = float(clean_p)

                if not price_eur or price_eur < 100:
                    continue

                # Parameters
                card_text = self.clean_text(card.text())
                year = None
                year_el = card.css_first(".announcement-title-parameters, .announcement-parameters")
                year_candidate = self.clean_text(year_el.text()) if year_el else card_text
                year_match = re.search(r"\b(199\d|20[0-2]\d)\b", year_candidate)
                if year_match:
                    year = int(year_match.group(1))

                mileage_km = None
                km_match = re.search(r"(\d{1,3}(?:[ \.]\d{3})*|\d+)\s*km", card_text, re.IGNORECASE)
                if km_match:
                    clean_km = re.sub(r"[^\d]", "", km_match.group(1))
                    if clean_km:
                        mileage_km = int(clean_km)

                fuel_type = None
                engine_size = None

                param_items = card.css(".param-list span, .announcement-parameters span, .announcement-parameters div, .item-parameters span")
                for item in param_items:
                    stext = self.clean_text(item.text())
                    if not stext:
                        continue

                    # Fuel
                    s_lower = stext.lower()
                    if "diesel" in s_lower or "dyzelis" in s_lower:
                        fuel_type = "Diesel"
                    elif "petrol" in s_lower or "benzinas" in s_lower:
                        fuel_type = "Petrol"
                    elif "hybrid" in s_lower or "hibridas" in s_lower:
                        fuel_type = "Hybrid"
                    elif "electric" in s_lower or "elektra" in s_lower:
                        fuel_type = "Electric"

                    # Engine capacity (e.g. 2.0 l)
                    if "l" in s_lower and re.search(r"[0-9]\.[0-9]", stext):
                        engine_size = stext

                if not fuel_type:
                    fuel_type = self._detect_fuel(card_text)

                make, model = self._parse_make_model(title)

                listing = CarListing(
                    external_id=external_id,
                    platform=self.name,
                    country=self.country,
                    title=title,
                    make=make,
                    model=model,
                    year=year,
                    price_eur=price_eur,
                    url=full_url,
                    price_local=price_eur,
                    currency_local="EUR",
                    mileage_km=mileage_km,
                    fuel_type=fuel_type,
                    engine_size=engine_size,
                    image_url=image_url
                )
                listings.append(listing)
            except Exception as card_err:
                logger.debug(f"[Autoplius.lt] Error parsing card: {card_err}")

        logger.info(f"[Autoplius.lt] Scraped {len(listings)} listings.")
        return listings

    def _parse_make_model(self, title: str) -> tuple[str, str]:
        parts = title.split()
        if not parts:
            return "Unknown", ""
        make = parts[0].title()
        model = parts[1].title() if len(parts) > 1 else ""
        return make, model

    def _detect_fuel(self, title: str) -> str:
        t = title.lower()
        if "hybrid" in t or "hsd" in t:
            return "Hybrid"
        if "diesel" in t or "dyzel" in t:
            return "Diesel"
        if "electric" in t or "ev" in t or "elektro" in t:
            return "Electric"
        return "Petrol"
