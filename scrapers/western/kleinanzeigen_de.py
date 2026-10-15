import re
import json
import logging
from typing import List, Optional, Dict, Any
from selectolax.lexbor import LexborHTMLParser as HTMLParser  # type: ignore

from scrapers.base_scraper import BaseScraper, CarListing
from config.settings import settings

logger = logging.getLogger(__name__)


class KleinanzeigenDeScraper(BaseScraper):
    name = "kleinanzeigen_de"
    country = "DE"
    interval_seconds = settings.KLEINANZEIGEN_DE_INTERVAL
    protection_level = 3  # Level 3: Aggressive / P2P Classifieds

    BASE_URL = "https://www.kleinanzeigen.de"
    SEARCH_URL = "https://www.kleinanzeigen.de/s-autos/sortierung:neueste/c216"

    async def scrape(self, filters: Optional[List[Dict[str, Any]]] = None) -> List[CarListing]:
        """Scrape latest car listings from Kleinanzeigen.de (Germany P2P)."""
        html = await self.fetch(self.SEARCH_URL)
        if not html:
            html = await self.fetch("https://www.kleinanzeigen.de/s-autos/c216")
        if not html:
            logger.warning("[Kleinanzeigen.de] Failed to fetch cars page.")
            return []

        parser = HTMLParser(html)
        listings: List[CarListing] = []

        articles = parser.css("article, li.ad-listitem article")
        for art in articles[:30]:  # Delta-scanning: top newest listings
            try:
                # Support data-href attribute or child link
                href = art.attributes.get("data-href") or ""
                if not href:
                    link_el = art.css_first("a[href*='/s-anzeige/'], a.ellipsis, h2 a, a")
                    if link_el:
                        href = link_el.attributes.get("href", "")

                if not href or "/s-anzeige/" not in href:
                    continue

                full_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
                adid = art.attributes.get("data-adid")
                if adid:
                    external_id = f"klein_{adid}"
                else:
                    id_match = re.search(r"/(\d+)(?:-\d+-\d+)?", href)
                    external_id = f"klein_{id_match.group(1)}" if id_match else f"klein_{hash(full_url)}"

                # Title & Image via application/ld+json or DOM
                title = ""
                image_url = None
                ld = art.css_first("script")
                if ld and "application/ld+json" in (ld.attributes.get("type") or ""):
                    try:
                        data = json.loads(ld.text())
                        title = self.clean_text(data.get("title", ""))
                        image_url = data.get("contentUrl")
                    except Exception:
                        pass

                if not title:
                    title_el = art.css_first("h2, a.ellipsis, a, .aditem-main--middle--subject")
                    title = self.clean_text(title_el.text()) if title_el else ""

                if not title:
                    title = "Kleinanzeigen Auto"

                if not image_url:
                    img_el = art.css_first("img")
                    if img_el:
                        image_url = img_el.attributes.get("src") or img_el.attributes.get("data-src")

                # Price (EUR)
                price_eur = None
                # First check legacy selector
                price_el = art.css_first(".aditem-main--middle--price-shipping--price, p.aditem-main--middle--price")
                if price_el:
                    clean_p = re.sub(r"[^\d]", "", price_el.text())
                    if clean_p and int(clean_p) >= 100:
                        price_eur = float(clean_p)

                # If not found, scan modern price elements
                if not price_eur:
                    for el in art.css("p, span, div"):
                        txt = el.text().strip()
                        if ("EUR" in txt or "VB" in txt or "€" in txt) and re.search(r"\d", txt):
                            m = re.search(r"(\d{1,3}(?:[ \.]\d{3})*|\d+)\s*(?:€|EUR|VB)", txt)
                            if m:
                                clean_digits = re.sub(r"[^\d]", "", m.group(1))
                                if clean_digits and int(clean_digits) >= 100:
                                    price_eur = float(clean_digits)
                                    break

                if not price_eur or price_eur < 100:
                    continue

                # Details text (year, km, fuel)
                art_text = self.clean_text(art.text())
                year = None
                year_match = re.search(r"\b(199\d|20[0-2]\d)\b", art_text)
                if year_match:
                    year = int(year_match.group(1))

                mileage_km = None
                km_match = re.search(r"(\d{1,3}(?:[ \.]\d{3})*|\d+)\s*km", art_text, re.IGNORECASE)
                if km_match:
                    clean_km = re.sub(r"[^\d]", "", km_match.group(1))
                    if clean_km:
                        mileage_km = int(clean_km)

                fuel_type = self._detect_fuel(art_text)
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
                logger.debug(f"[Kleinanzeigen.de] Parse error: {e}")

        logger.info(f"[Kleinanzeigen.de] Scraped {len(listings)} listings.")
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
        if "diesel" in t or "tdi" in t:
            return "Diesel"
        if "elektro" in t or "electric" in t or "ev" in t:
            return "Electric"
        return "Petrol"
