import sys
from pathlib import Path
import re
import json
import logging
import statistics
from typing import Optional, Dict, Any, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from selectolax.lexbor import LexborHTMLParser as HTMLParser  # type: ignore

from scrapers.base_scraper import BaseScraper
from config.settings import settings
from database.queries import get_market_benchmark, save_market_benchmark

logger = logging.getLogger(__name__)


class OtomotoBenchmarkScraper(BaseScraper):
    name = "otomoto_pl"
    country = "PL"
    BASE_URL = "https://www.otomoto.pl"

    SLUG_MAP = {
        "mercedes-benz": "mercedes-benz",
        "mercedes": "mercedes-benz",
        "vw": "volkswagen",
        "bmw": "bmw",
        "audi": "audi",
        "skoda": "skoda",
        "toyota": "toyota",
        "volvo": "volvo",
        "ford": "ford",
        "renault": "renault",
        "opel": "opel",
        "peugeot": "peugeot",
        "hyundai": "hyundai",
        "kia": "kia",
        "nissan": "nissan",
        "honda": "honda",
        "mazda": "mazda",
        "seat": "seat"
    }

    def _clean_slug(self, text: str) -> str:
        s = text.strip().lower()
        s = self.SLUG_MAP.get(s, s)
        s = re.sub(r"[^a-z0-9\-]", "-", s)
        return re.sub(r"-+", "-", s).strip("-")

    async def get_market_price(
        self,
        make: str,
        model: str,
        year: int,
        fuel_type: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch median Polish market price for make, model, year.
        Uses cached benchmark if available, otherwise live scrapes Otomoto.pl.
        """
        if not make or not year:
            return None

        # Check DB cache
        if use_cache:
            cached = await get_market_benchmark(make, model, year, fuel_type)
            if cached:
                median_eur = float(cached["median_price_eur"])
                median_pln = round(median_eur * settings.EUR_TO_PLN_RATE, 2)
                logger.debug(f"[Otomoto] Found cached benchmark for {make} {model} {year}: {median_eur} €")
                return {
                    "make": make,
                    "model": model,
                    "year": year,
                    "median_price_eur": median_eur,
                    "median_price_pln": median_pln,
                    "sample_count": cached.get("total_listings_analyzed", 1),
                    "url": f"{self.BASE_URL}/osobowe/{self._clean_slug(make)}/{self._clean_slug(model)}"
                }

        # Construct Otomoto search URL
        make_slug = self._clean_slug(make)
        model_slug = self._clean_slug(model) if model else ""

        if model_slug:
            url = (
                f"{self.BASE_URL}/osobowe/{make_slug}/{model_slug}"
                f"?search%5Bfilter_float_year%3Afrom%5D={year}"
                f"&search%5Bfilter_float_year%3Ato%5D={year}"
            )
        else:
            url = (
                f"{self.BASE_URL}/osobowe/{make_slug}"
                f"?search%5Bfilter_float_year%3Afrom%5D={year}"
                f"&search%5Bfilter_float_year%3Ato%5D={year}"
            )

        try:
            html_text = await self.fetch(url)
            if not html_text:
                return None

            prices: List[float] = []
            tree = HTMLParser(html_text)
            script = tree.css_first("script#__NEXT_DATA__")

            if script:
                try:
                    data = json.loads(script.text())
                    urql = data.get("props", {}).get("pageProps", {}).get("urqlState", {})
                    for _, v in urql.items():
                        data_str = v.get("data", "")
                        if "advertSearch" in data_str:
                            d = json.loads(data_str)
                            edges = d.get("advertSearch", {}).get("edges", [])
                            for edge in edges:
                                price_obj = edge.get("node", {}).get("price", {})
                                amt = price_obj.get("amount", {}).get("units")
                                if amt and isinstance(amt, (int, float)):
                                    prices.append(float(amt))
                except Exception as json_err:
                    logger.debug(f"[Otomoto] Error parsing __NEXT_DATA__: {json_err}")

            # Fallback to HTML elements
            if not prices:
                price_tags = tree.css("p[data-testid='ad-price'], h3, [class*='price']")
                for pt in price_tags:
                    cleaned_p = re.sub(r"[^\d]", "", pt.text(strip=True))
                    if cleaned_p and len(cleaned_p) >= 4:
                        val = float(cleaned_p)
                        if 1000 <= val <= 2000000:
                            prices.append(val)

            if not prices:
                logger.info(f"[Otomoto] No active listings found on Otomoto for {make} {model} {year}")
                return None

            median_pln = round(float(statistics.median(prices)), 2)
            median_eur = round(median_pln / settings.EUR_TO_PLN_RATE, 2)
            sample_count = len(prices)

            # Save to DB cache
            await save_market_benchmark(
                make=make,
                model=model,
                year=year,
                median_price_eur=median_eur,
                total_listings_analyzed=sample_count,
                fuel_type=fuel_type
            )

            logger.info(
                f"[Otomoto] Benchmark updated: {make} {model} ({year}) -> "
                f"Median: {median_pln} PLN (~{median_eur} €) from {sample_count} samples"
            )

            return {
                "make": make,
                "model": model,
                "year": year,
                "median_price_pln": median_pln,
                "median_price_eur": median_eur,
                "sample_count": sample_count,
                "min_price_pln": min(prices),
                "max_price_pln": max(prices),
                "url": url
            }
        except Exception as e:
            logger.error(f"[Otomoto] Error calculating benchmark for {make} {model} {year}: {e}")
            return None
