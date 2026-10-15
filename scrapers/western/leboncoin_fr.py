import re
import logging
from typing import List, Optional, Dict, Any
from selectolax.lexbor import LexborHTMLParser as HTMLParser  # type: ignore

from scrapers.base_scraper import BaseScraper, CarListing
from config.settings import settings

logger = logging.getLogger(__name__)


class LeboncoinFrScraper(BaseScraper):
    name = "leboncoin_fr"
    country = "FR"
    interval_seconds = settings.LEBONCOIN_FR_INTERVAL
    protection_level = 3  # Level 3: Aggressive DataDome (curl_cffi Chrome Impersonation)

    BASE_URL = "https://www.leboncoin.fr"
    SEARCH_URL = "https://www.leboncoin.fr/recherche?category=2&sort=time&order=desc"

    async def scrape(self, filters: Optional[List[Dict[str, Any]]] = None) -> List[CarListing]:
        """Scrape latest car listings from Leboncoin.fr (France P2P)."""
        html = await self.fetch(self.SEARCH_URL)
        if not html:
            html = await self.fetch("https://www.leboncoin.fr/c/voitures")
        if not html:
            logger.warning("[Leboncoin.fr] Failed to fetch cars page.")
            return []

        parser = HTMLParser(html)
        listings: List[CarListing] = []

        cards = parser.css("a[data-test-id='ad'], a[href*='/ad/voitures/'], article")
        if not cards:
            cards = parser.css("div[data-qa-id='aditem_container'] a, [data-test-id='listing-card'] a")

        for card in cards[:25]:
            try:
                link_el = card if card.tag == "a" else card.css_first("a")
                if not link_el:
                    continue

                href = link_el.attributes.get("href", "")
                if not href or ("/ad/" not in href and "/voitures/" not in href):
                    continue

                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                id_match = re.search(r"/(\d+)(?:\?|$)", full_url)
                external_id = f"lbc_{id_match.group(1)}" if id_match else f"lbc_{hash(full_url)}"

                # Title
                title_el = card.css_first("p[data-qa-id='aditem_title'], h2, h3, [class*='title']")
                title = self.clean_text(title_el.text()) if title_el else ""
                if not title:
                    title = "Leboncoin Auto"

                # Image
                img_el = card.css_first("img")
                image_url = None
                if img_el:
                    image_url = img_el.attributes.get("src") or img_el.attributes.get("data-src")

                # Price (EUR)
                price_el = card.css_first("[data-qa-id='aditem_price'], [class*='price']")
                price_text = self.clean_text(price_el.text()) if price_el else ""
                price_eur = None
                if price_text:
                    clean_digits = re.sub(r"[^\d]", "", price_text)
                    if clean_digits:
                        price_eur = float(clean_digits)

                if not price_eur or price_eur < 100:
                    continue

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
                    price_local=price_eur,
                    currency_local="EUR",
                    mileage_km=mileage_km,
                    fuel_type=fuel_type,
                    image_url=image_url
                )
                listings.append(listing)
            except Exception as e:
                logger.debug(f"[Leboncoin.fr] Parse error: {e}")

        logger.info(f"[Leboncoin.fr] Scraped {len(listings)} listings.")
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
        if "hybride" in t or "hybrid" in t:
            return "Hybrid"
        if "diesel" in t or "dci" in t or "hdi" in t:
            return "Diesel"
        if "electrique" in t or "électrique" in t or "ev" in t:
            return "Electric"
        return "Petrol"
