import re
import logging
from typing import List, Optional, Dict, Any
from selectolax.lexbor import LexborHTMLParser as HTMLParser  # type: ignore

from scrapers.base_scraper import BaseScraper, CarListing
from config.settings import settings

logger = logging.getLogger(__name__)


class BazosCzScraper(BaseScraper):
    name = "bazos_cz"
    country = "CZ"
    interval_seconds = settings.BAZOS_CZ_INTERVAL
    protection_level = 1  # Level 1: Simple HTML

    BASE_URL = "https://auto.bazos.cz"
    SEARCH_URL = "https://auto.bazos.cz/"

    async def scrape(self, filters: Optional[List[Dict[str, Any]]] = None) -> List[CarListing]:
        """Scrape latest car listings from Bazos.cz (Czechia) and convert CZK to EUR."""
        html = await self.fetch(self.SEARCH_URL)
        if not html:
            logger.warning("[Bazos.cz] Failed to fetch cars page.")
            return []

        parser = HTMLParser(html)
        listings: List[CarListing] = []

        cards = parser.css("div.inzeraty, div.inzerat")
        for card in cards[:25]:  # Delta-scanning: top 25 listings
            try:
                title_link = card.css_first("h2.nadpis a, span.nadpis a, div.inzeratynadpis a, h2 a")
                if not title_link or not title_link.text(strip=True):
                    for a_cand in card.css("a"):
                        cand_href = a_cand.attributes.get("href") or ""
                        if a_cand.text(strip=True) and "/inzerat/" in cand_href:
                            title_link = a_cand
                            break
                if not title_link:
                    continue

                href = title_link.attributes.get("href", "")
                if not href or "/inzerat/" not in href:
                    continue

                full_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
                id_match = re.search(r"/inzerat/(\d+)/", full_url)
                external_id = f"bazos_cz_{id_match.group(1)}" if id_match else f"bazos_cz_{hash(full_url)}"

                title = self.clean_text(title_link.text())
                if not title:
                    title = "Bazos Auto"
                desc_el = card.css_first("div.popis")
                desc = self.clean_text(desc_el.text()) if desc_el else ""

                # Image
                img_el = card.css_first("img")
                image_url = img_el.attributes.get("src") if img_el else None

                # Price (CZK)
                price_el = card.css_first("div.inzeratycena b, div.inzeratycena")
                price_text = self.clean_text(price_el.text()) if price_el else ""
                price_czk = None
                if price_text:
                    clean_digits = re.sub(r"[^\d]", "", price_text)
                    if clean_digits:
                        price_czk = float(clean_digits)

                if not price_czk or price_czk < 2000:
                    continue

                # Convert CZK to EUR
                price_eur = round(price_czk * settings.CZK_TO_EUR_RATE, 2)

                # Parse specs
                full_text = f"{title} {desc}"
                year = self._extract_year(full_text)
                mileage_km = self._extract_mileage(full_text)
                fuel_type = self._detect_fuel(full_text)
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
                    description=desc[:200] if desc else None,
                    image_url=image_url
                )
                listings.append(listing)
            except Exception as card_err:
                logger.debug(f"[Bazos.cz] Error parsing card: {card_err}")

        logger.info(f"[Bazos.cz] Scraped {len(listings)} listings.")
        return listings

    def _extract_year(self, text: str) -> Optional[int]:
        match = re.search(r"\b(r\.?\s*v\.?|rok|rv)?\s*:?\s*(199\d|20[0-2]\d)\b", text, re.IGNORECASE)
        if match:
            return int(match.group(2))
        years = re.findall(r"\b(199\d|20[0-2]\d)\b", text)
        return int(years[0]) if years else None

    def _extract_mileage(self, text: str) -> Optional[int]:
        match = re.search(r"\b(\d{1,3}(?:[ \.]\d{3})*|\d+)\s*km\b", text, re.IGNORECASE)
        if match:
            clean = re.sub(r"[^\d]", "", match.group(1))
            return int(clean) if clean else None
        return None

    def _parse_make_model(self, title: str) -> tuple[str, str]:
        parts = title.split()
        if not parts:
            return "Unknown", ""
        make = parts[0].title()
        model = parts[1].title() if len(parts) > 1 else ""
        return make, model

    def _detect_fuel(self, text: str) -> str:
        t = text.lower()
        if "hybrid" in t or "phev" in t:
            return "Hybrid"
        if "diesel" in t or "tdi" in t or "dci" in t or "cdti" in t or "nafta" in t:
            return "Diesel"
        if "electric" in t or "elektro" in t or "ev" in t:
            return "Electric"
        return "Petrol"
