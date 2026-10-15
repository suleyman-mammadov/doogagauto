import re
import logging
from typing import List, Optional, Dict, Any
from selectolax.lexbor import LexborHTMLParser as HTMLParser  # type: ignore

from scrapers.base_scraper import BaseScraper, CarListing
from config.settings import settings

logger = logging.getLogger(__name__)


class SautoCzScraper(BaseScraper):
    name = "sauto_cz"
    country = "CZ"
    interval_seconds = settings.SAUTO_CZ_INTERVAL
    protection_level = 2  # Level 2: Medium / Cookie / Seznam ecosystem

    BASE_URL = "https://www.sauto.cz"
    SEARCH_URL = "https://www.sauto.cz/inzerce/osobni?razeni=nejnovejsi"

    async def scrape(self, filters: Optional[List[Dict[str, Any]]] = None) -> List[CarListing]:
        """Scrape latest car listings from Sauto.cz (Seznam, Czechia)."""
        html = await self.fetch(self.SEARCH_URL)
        if not html:
            logger.warning("[Sauto.cz] Failed to fetch cars page.")
            return []

        parser = HTMLParser(html)
        listings: List[CarListing] = []

        cards = parser.css("article, a.c-item, div[data-testid='search-item']")
        if not cards:
            cards = parser.css(".c-item-list__item, .c-item")

        for card in cards[:25]:
            try:
                link_el = card if card.tag == "a" else card.css_first("a[href*='/detail/'], a")
                if not link_el:
                    continue

                href = link_el.attributes.get("href", "")
                if not href or ("/detail/" not in href and "/osobni/" not in href):
                    continue

                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                id_match = re.search(r"/(\d+)(?:\?|$)", full_url)
                external_id = f"sauto_cz_{id_match.group(1)}" if id_match else f"sauto_cz_{hash(full_url)}"

                # Title
                title_el = card.css_first("h2, h3, .c-item__title")
                title = self.clean_text(title_el.text()) if title_el else ""
                if not title:
                    title = "Sauto.cz Listing"

                # Image
                img_el = card.css_first("img")
                image_url = None
                if img_el:
                    image_url = img_el.attributes.get("src") or img_el.attributes.get("data-src")

                # Price (CZK)
                price_el = card.css_first(".c-item__price, [data-testid='price'], .price, b")
                price_text = self.clean_text(price_el.text()) if price_el else ""
                price_czk = None
                if price_text:
                    clean_digits = re.sub(r"[^\d]", "", price_text)
                    if clean_digits:
                        price_czk = float(clean_digits)

                if not price_czk or price_czk < 2000:
                    continue

                price_eur = round(price_czk * settings.CZK_TO_EUR_RATE, 2)

                # Year and mileage
                card_text = self.clean_text(card.text())
                year = None
                year_match = re.search(r"\b(199\d|20[0-2]\d)\b", card_text)
                if year_match:
                    year = int(year_match.group(1))

                mileage_km = None
                km_match = re.search(r"(\d{1,3}(?:[ \.]\d{3})*|\d+)\s*km", card_text, re.IGNORECASE)
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
                    price_local=price_czk,
                    currency_local="CZK",
                    mileage_km=mileage_km,
                    fuel_type=fuel_type,
                    image_url=image_url
                )
                listings.append(listing)
            except Exception as e:
                logger.debug(f"[Sauto.cz] Parse error: {e}")

        logger.info(f"[Sauto.cz] Scraped {len(listings)} listings.")
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
        if "nafta" in t or "diesel" in t or "tdi" in t:
            return "Diesel"
        if "elektro" in t or "electric" in t:
            return "Electric"
        return "Petrol"
