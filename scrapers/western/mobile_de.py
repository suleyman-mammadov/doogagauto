import re
import logging
from typing import List, Optional, Dict, Any
from selectolax.lexbor import LexborHTMLParser as HTMLParser  # type: ignore

from scrapers.base_scraper import BaseScraper, CarListing
from config.settings import settings

logger = logging.getLogger(__name__)


class MobileDeScraper(BaseScraper):
    name = "mobile_de"
    country = "DE"
    interval_seconds = settings.MOBILE_DE_INTERVAL
    protection_level = 3  # Level 3: Aggressive (curl_cffi Chrome Impersonation + HTTP/2)

    BASE_URL = "https://suchen.mobile.de"
    SEARCH_URL = "https://suchen.mobile.de/fahrzeuge/search.html?dam=0&isSearchRequest=true&s=Car&sortOption.sortBy=creationTime.desc&vc=Car"

    async def scrape(self, filters: Optional[List[Dict[str, Any]]] = None) -> List[CarListing]:
        """Scrape latest car listings from Mobile.de (Germany)."""
        html = await self.fetch(self.SEARCH_URL)
        if not html:
            logger.warning("[Mobile.de] Failed to fetch search page.")
            return []

        parser = HTMLParser(html)
        listings: List[CarListing] = []

        cards = parser.css("article[data-testid^='result-listing-'], div.cBox-body--resultitem, a.link--muted")
        if not cards:
            cards = parser.css("article, div[class*='result-item']")

        for card in cards[:25]:  # Delta-scanning: top 25 listings
            try:
                link_el = card if card.tag == "a" else card.css_first("a[href*='/fahrzeuge/details.html'], a")
                if not link_el:
                    continue

                href = link_el.attributes.get("href", "")
                if not href or "/fahrzeuge/details.html" not in href:
                    continue

                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                id_match = re.search(r"id=(\d+)", full_url)
                external_id = f"mobile_de_{id_match.group(1)}" if id_match else f"mobile_de_{hash(full_url)}"

                # Title
                title_el = card.css_first("h2, h3, [data-testid='listing-title'], .headline--bold")
                title = self.clean_text(title_el.text()) if title_el else ""
                if not title:
                    title = "Mobile.de Vehicle"

                # Image
                img_el = card.css_first("img")
                image_url = None
                if img_el:
                    image_url = img_el.attributes.get("src") or img_el.attributes.get("data-src")

                # Price (EUR)
                price_el = card.css_first("[data-testid='price-label'], .price-block, .u-text-bold, [class*='price']")
                price_text = self.clean_text(price_el.text()) if price_el else ""
                price_eur = None
                if "€" in price_text or price_text:
                    clean_digits = re.sub(r"[^\d]", "", price_text)
                    if clean_digits:
                        price_eur = float(clean_digits)

                if not price_eur or price_eur < 100:
                    continue

                card_text = self.clean_text(card.text())
                year = None
                year_match = re.search(r"\b(0[1-9]|1[0-2])?/?(199\d|20[0-2]\d)\b", card_text)
                if year_match:
                    year = int(year_match.group(2))

                mileage_km = None
                km_match = re.search(r"(\d{1,3}(?:[\.,]\d{3})*|\d+)\s*km", card_text, re.IGNORECASE)
                if km_match:
                    clean_km = re.sub(r"[^\d]", "", km_match.group(1))
                    if clean_km:
                        mileage_km = int(clean_km)

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
                    image_url=image_url
                )
                listings.append(listing)
            except Exception as e:
                logger.debug(f"[Mobile.de] Parse error: {e}")

        logger.info(f"[Mobile.de] Scraped {len(listings)} listings.")
        return listings

    def _parse_make_model(self, title: str) -> tuple[str, str]:
        parts = title.split()
        if not parts:
            return "Unknown", ""
        make = parts[0].title()
        model = parts[1].title() if len(parts) > 1 else ""
        return make, model

    def _detect_fuel(self, text: str) -> str:
        t = text.lower()
        if "hybrid" in t:
            return "Hybrid"
        if "diesel" in t:
            return "Diesel"
        if "elektro" in t or "electric" in t:
            return "Electric"
        return "Petrol"
