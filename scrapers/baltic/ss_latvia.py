import re
import logging
from typing import List, Optional, Dict, Any
from selectolax.lexbor import LexborHTMLParser as HTMLParser  # type: ignore

from scrapers.base_scraper import BaseScraper, CarListing
from config.settings import settings

logger = logging.getLogger(__name__)


class SSLatviaScraper(BaseScraper):
    name = "ss_latvia"
    country = "LV"
    interval_seconds = settings.SS_LATVIA_INTERVAL
    protection_level = 1  # Level 1: Simple HTML

    BASE_URL = "https://www.ss.com"
    SEARCH_URL = "https://www.ss.com/lv/transport/cars/today-5/sell/"

    async def scrape(self, filters: Optional[List[Dict[str, Any]]] = None) -> List[CarListing]:
        """Scrape latest car listings from SS.com (Latvia)."""
        html = await self.fetch(self.SEARCH_URL)
        if not html:
            html = await self.fetch(f"{self.BASE_URL}/lv/transport/cars/sell/")
        if not html:
            logger.warning("[SS.com] Failed to fetch cars page.")
            return []

        parser = HTMLParser(html)
        listings: List[CarListing] = []

        # Find rows in the ad table
        rows = parser.css("tr[id^='tr_']")
        if not rows:
            rows = parser.css("table#page_main tr")

        for row in rows[:30]:  # Delta-scanning: top newest listings
            try:
                msg_link = row.css_first("a[id^='dm_'], a.am")
                if not msg_link:
                    continue

                href = msg_link.attributes.get("href", "")
                if not href or not href.endswith(".html"):
                    continue

                full_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
                msg_id_match = re.search(r"/([a-zA-Z0-9_-]+)\.html", href)
                external_id = f"ss_{msg_id_match.group(1)}" if msg_id_match else f"ss_{hash(full_url)}"

                # Extract title and image
                title = self.clean_text(msg_link.text())
                img_el = row.css_first("img")
                image_url = img_el.attributes.get("src") if img_el else None

                # Extract table columns
                tds = row.css("td")
                year = None
                engine_size = None
                mileage_km = None
                price_eur = None

                for td in tds:
                    td_text = self.clean_text(td.text())
                    if not td_text:
                        continue

                    # Price column (e.g., "4,500 €" or "4 500 €")
                    if "€" in td_text:
                        clean_price = re.sub(r"[^\d]", "", td_text)
                        if clean_price:
                            price_eur = float(clean_price)
                        continue

                    # Year column (e.g., "2015", "2008")
                    if re.match(r"^(199\d|20[0-2]\d)$", td_text):
                        year = int(td_text)
                        continue

                    # Mileage (e.g., "185 tūkst." or "185 000")
                    if "tūkst" in td_text or "km" in td_text:
                        num = self.extract_number(td_text)
                        if num:
                            mileage_km = num * 1000 if "tūkst" in td_text and num < 1000 else num
                        continue

                    # Engine (e.g., "2.0D", "1.6", "2.2H")
                    if re.match(r"^[0-9]\.[0-9][a-zA-Z]?$", td_text):
                        engine_size = td_text
                        continue

                if not price_eur or price_eur <= 100:
                    continue

                # Parse Make and Model from title
                make, model = self._parse_make_model(title)
                fuel_type = self._detect_fuel(title, engine_size)

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
            except Exception as row_err:
                logger.debug(f"[SS.com] Error parsing row: {row_err}")

        logger.info(f"[SS.com] Scraped {len(listings)} listings.")
        return listings

    def _parse_make_model(self, title: str) -> tuple[str, str]:
        parts = title.split()
        if not parts:
            return "Unknown", ""
        make = parts[0].title()
        model = parts[1].title() if len(parts) > 1 else ""
        return make, model

    def _detect_fuel(self, title: str, engine: Optional[str]) -> str:
        text = f"{title} {engine or ''}".lower()
        if "hybrid" in text or "hsd" in text:
            return "Hybrid"
        if "d" in (engine or "").lower() or "diesel" in text or "dīzelis" in text:
            return "Diesel"
        if "ev" in text or "electric" in text or "elektro" in text:
            return "Electric"
        return "Petrol"
