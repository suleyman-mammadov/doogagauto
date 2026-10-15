import sys
from pathlib import Path
import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.base_scraper import CarListing
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageResult:
    listing: CarListing
    poland_median_pln: float
    poland_median_eur: float
    sample_count: int
    listing_price_pln: float
    transport_cost_eur: float
    transport_cost_pln: float
    akcyza_rate: float
    akcyza_cost_pln: float
    akcyza_cost_eur: float
    registration_cost_pln: float
    registration_cost_eur: float
    total_landed_cost_pln: float
    total_landed_cost_eur: float
    profit_pln: float
    profit_eur: float
    profit_percent: float
    is_hot_deal: bool
    otomoto_url: Optional[str] = None


class ArbitrageEngine:
    def __init__(self, eur_to_pln: Optional[float] = None):
        self._eur_to_pln = eur_to_pln

    @property
    def eur_to_pln(self) -> float:
        return self._eur_to_pln if self._eur_to_pln is not None else settings.EUR_TO_PLN_RATE

    @eur_to_pln.setter
    def eur_to_pln(self, value: float):
        self._eur_to_pln = value

    def get_logistics_cost_eur(self, country_code: str) -> float:
        """Determine estimated transport cost to Poland by country code."""
        code = (country_code or "DEFAULT").upper()
        rates = settings.LOGISTICS_RATES_EUR
        if code in rates:
            return rates[code]
        return rates.get("DEFAULT", 500.0)

    def determine_akcyza_rate(self, listing: CarListing) -> float:
        """Determine Polish excise tax (Akcyza) percentage based on engine & fuel."""
        engine_str = (listing.engine_size or "").lower()
        title_str = (listing.title or "").lower()
        full_text = f"{engine_str} {title_str} {listing.description or ''}".lower()

        # 1. Full Electric Vehicles: 0%
        if listing.fuel_type == "Electric" or "ev" in full_text or "elektro" in full_text or "electric" in full_text:
            return settings.AKCYZA_EV_RATE

        is_hybrid = listing.fuel_type == "Hybrid" or "hybrid" in full_text or "hsd" in full_text or "phev" in full_text

        # 2. Check engine capacity in liters (e.g., 2.2L, 3.0L)
        is_high_capacity = False
        liters_match = re.search(r"\b([1-9]\.[0-9])\s*l?\b", full_text)
        if liters_match:
            try:
                liters = float(liters_match.group(1))
                if liters > 2.0:
                    is_high_capacity = True
            except ValueError:
                pass

        # 3. Check engine capacity in cm3 (e.g., 2148 cm3, 2993 cm3)
        if not is_high_capacity:
            cc_match = re.search(r"\b([2-9]\d{3})\s*cm3?\b", full_text)
            if cc_match:
                try:
                    cc = int(cc_match.group(1))
                    if cc > 2000:
                        is_high_capacity = True
                except ValueError:
                    pass

        # 4. Return applicable rates
        if is_hybrid:
            return settings.AKCYZA_HYBRID_HIGH_RATE if is_high_capacity else settings.AKCYZA_HYBRID_STANDARD_RATE

        return settings.AKCYZA_HIGH_CAPACITY_RATE if is_high_capacity else settings.AKCYZA_STANDARD_RATE

    def calculate_arbitrage(
        self,
        listing: CarListing,
        market_benchmark: Dict[str, Any]
    ) -> ArbitrageResult:
        """
        Calculate complete Pan-European financial arbitrage model:
        Net Profit = Poland Median Price (EUR) - (Purchase Price + Logistics + Excise + Registration)
        """
        # Benchmark median in PLN and EUR
        if "median_price_eur" in market_benchmark and market_benchmark["median_price_eur"]:
            poland_median_eur = float(market_benchmark["median_price_eur"])
            poland_median_pln = round(poland_median_eur * self.eur_to_pln, 2)
        else:
            poland_median_pln = float(market_benchmark.get("median_price_pln", 0.0))
            poland_median_eur = round(poland_median_pln / self.eur_to_pln, 2)

        sample_count = int(market_benchmark.get("total_listings_analyzed") or market_benchmark.get("sample_count", 1))

        # 1. Listing price
        listing_price_eur = float(listing.price_eur)
        listing_price_pln = round(listing_price_eur * self.eur_to_pln, 2)

        # 2. Country-specific Logistics
        transport_cost_eur = self.get_logistics_cost_eur(listing.country)
        transport_cost_pln = round(transport_cost_eur * self.eur_to_pln, 2)

        # 3. Akcyza (Excise Tax)
        akcyza_rate = self.determine_akcyza_rate(listing)
        akcyza_cost_pln = round(listing_price_pln * akcyza_rate, 2)
        akcyza_cost_eur = round(akcyza_cost_pln / self.eur_to_pln, 2)

        # 4. Registration & Technical Inspection in Poland
        registration_cost_pln = float(settings.ESTIMATED_REGISTRATION_PLN)
        registration_cost_eur = round(registration_cost_pln / self.eur_to_pln, 2)

        # 5. Total Landed Cost
        total_landed_cost_pln = round(
            listing_price_pln + transport_cost_pln + akcyza_cost_pln + registration_cost_pln,
            2
        )
        total_landed_cost_eur = round(total_landed_cost_pln / self.eur_to_pln, 2)

        # 6. Gross Arbitrage Profit (Net Profit)
        profit_pln = round(poland_median_pln - total_landed_cost_pln, 2)
        profit_eur = round(profit_pln / self.eur_to_pln, 2)

        # 7. Profit Margin (%)
        if total_landed_cost_pln > 0:
            profit_percent = round((profit_pln / total_landed_cost_pln) * 100, 1)
        else:
            profit_percent = 0.0

        # 8. Hot Deal Condition: Net Profit >= 1,500 EUR OR >= 15% discount
        is_hot_deal = (
            profit_eur >= settings.HOT_DEAL_MIN_PROFIT_EUR or
            profit_percent >= settings.HOT_DEAL_THRESHOLD_PERCENT
        )

        return ArbitrageResult(
            listing=listing,
            poland_median_pln=poland_median_pln,
            poland_median_eur=poland_median_eur,
            sample_count=sample_count,
            listing_price_pln=listing_price_pln,
            transport_cost_eur=transport_cost_eur,
            transport_cost_pln=transport_cost_pln,
            akcyza_rate=akcyza_rate,
            akcyza_cost_pln=akcyza_cost_pln,
            akcyza_cost_eur=akcyza_cost_eur,
            registration_cost_pln=registration_cost_pln,
            registration_cost_eur=registration_cost_eur,
            total_landed_cost_pln=total_landed_cost_pln,
            total_landed_cost_eur=total_landed_cost_eur,
            profit_pln=profit_pln,
            profit_eur=profit_eur,
            profit_percent=profit_percent,
            is_hot_deal=is_hot_deal,
            otomoto_url=market_benchmark.get("url")
        )

    @staticmethod
    def matches_filter(listing: CarListing, user_filter: Dict[str, Any]) -> bool:
        """Evaluate if car listing satisfies all criteria of a user filter."""
        # 1. Target countries check
        raw_countries = user_filter.get("target_countries") or user_filter.get("target_country", "ALL")
        if raw_countries and raw_countries != "ALL":
            allowed_countries = [c.strip().upper() for c in raw_countries.split(",")]
            if listing.country.upper() not in allowed_countries:
                return False

        # 2. Target platforms check
        raw_platforms = user_filter.get("target_platforms", "ALL")
        if raw_platforms and raw_platforms != "ALL":
            allowed_platforms = [p.strip().lower() for p in raw_platforms.split(",")]
            if listing.platform.lower() not in allowed_platforms:
                return False

        # 3. Make check (Mandatory)
        filter_make = (user_filter.get("make") or "").strip().lower()
        listing_make = (listing.make or "").strip().lower()
        listing_title = (listing.title or "").strip().lower()
        if filter_make and filter_make not in ("all", "any", "bütün"):
            if filter_make not in listing_make and filter_make not in listing_title:
                return False

        # 4. Model check (Optional)
        filter_model = (user_filter.get("model") or "").strip().lower()
        if filter_model and filter_model not in ("all", "any", "none", "-", "bütün"):
            listing_model = (listing.model or "").strip().lower()
            if filter_model not in listing_model and filter_model not in listing_title:
                return False

        # 5. Year min and max check
        year_min = user_filter.get("year_min")
        if year_min and listing.year:
            if listing.year < year_min:
                return False

        year_max = user_filter.get("year_max")
        if year_max and listing.year:
            if listing.year > year_max:
                return False

        # 6. Price min and max check
        price_min_eur = user_filter.get("price_min_eur")
        if price_min_eur and listing.price_eur:
            if listing.price_eur < price_min_eur:
                return False

        price_max_eur = user_filter.get("price_max_eur")
        if price_max_eur and listing.price_eur:
            if listing.price_eur > price_max_eur:
                return False

        # 7. Mileage min and max check
        mileage_min = user_filter.get("mileage_min")
        if mileage_min and listing.mileage_km:
            if listing.mileage_km < mileage_min:
                return False

        mileage_max = user_filter.get("mileage_max") if user_filter.get("mileage_max") is not None else user_filter.get("mileage_max_km")
        if mileage_max and listing.mileage_km:
            if listing.mileage_km > mileage_max:
                return False

        # 8. Fuel type check
        filter_fuel = (user_filter.get("fuel_type") or "").strip().lower()
        if filter_fuel and filter_fuel not in ("all", "any", "any fuel", "all fuels", "none"):
            if listing.fuel_type and filter_fuel not in listing.fuel_type.lower():
                return False

        # 9. Transmission check
        filter_trans = (user_filter.get("transmission") or "").strip().lower()
        if filter_trans and filter_trans not in ("all", "any", "any transmission", "all transmissions", "none"):
            if listing.transmission and filter_trans not in listing.transmission.lower():
                return False

        return True
