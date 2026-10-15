import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import random
from curl_cffi.requests import AsyncSession  # type: ignore

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CarListing:
    external_id: str
    platform: str
    country: str
    title: str
    make: str
    model: str
    year: Optional[int]
    price_eur: float
    url: str
    price_local: Optional[float] = None
    currency_local: str = "EUR"
    mileage_km: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    engine_size: Optional[str] = None
    location: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    created_in_source: Optional[str] = None


# Module-level cache for dynamic proxy configuration
_CACHED_PROXY_SETTINGS: Dict[str, Any] = {
    "is_enabled": False,
    "proxy_url": "",
    "apply_mode": "protected_only",
    "rotation_strategy": "round_robin",
    "pool_urls": []
}


class ProxyPoolManager:
    """Manages active pool of 100 - 1000+ proxies with round-robin and random rotation."""
    def __init__(self):
        self.proxies: List[str] = []
        self.index: int = 0
        self.is_enabled: bool = False
        self.apply_mode: str = "protected_only"
        self.rotation_strategy: str = "round_robin"
        self.single_fallback_proxy: str = ""

    def update(
        self,
        pool_urls: List[str],
        is_enabled: bool,
        apply_mode: str = "protected_only",
        rotation_strategy: str = "round_robin",
        single_proxy: str = ""
    ):
        self.proxies = [p.strip() for p in pool_urls if p and p.strip()]
        self.is_enabled = is_enabled
        self.apply_mode = apply_mode
        self.rotation_strategy = rotation_strategy
        self.single_fallback_proxy = single_proxy.strip()
        self.index = 0
        logger.info(
            f"[ProxyPool] Active pool updated: {len(self.proxies)} proxies | "
            f"Mode: {apply_mode} | Strategy: {rotation_strategy} | Enabled: {is_enabled}"
        )

    def get_proxy_for_scraper(self, scraper_name: str) -> Optional[str]:
        if not self.is_enabled:
            return None

        # Check scope: if protected_only, only apply to protected sites
        if self.apply_mode == "protected_only" and scraper_name not in {"mobile_de", "leboncoin_fr", "sauto_cz"}:
            return None

        # Rotate through the pool of 100-1000 proxies
        if self.proxies:
            if self.rotation_strategy == "random":
                return random.choice(self.proxies)
            else:  # round_robin
                p = self.proxies[self.index % len(self.proxies)]
                self.index = (self.index + 1) % len(self.proxies)
                return p

        # Fallback to single proxy if pool has no items
        if self.single_fallback_proxy:
            return self.single_fallback_proxy

        return None


proxy_pool_manager = ProxyPoolManager()


def set_cached_proxy_settings(p_dict: Dict[str, Any], pool_urls: Optional[List[str]] = None):
    """Update active proxy settings in memory cache and sync ProxyPoolManager."""
    global _CACHED_PROXY_SETTINGS
    _CACHED_PROXY_SETTINGS = dict(p_dict)

    urls = pool_urls if pool_urls is not None else _CACHED_PROXY_SETTINGS.get("pool_urls", [])
    _CACHED_PROXY_SETTINGS["pool_urls"] = urls

    proxy_pool_manager.update(
        pool_urls=urls,
        is_enabled=bool(p_dict.get("is_enabled", False)),
        apply_mode=p_dict.get("apply_mode", "protected_only"),
        rotation_strategy=p_dict.get("rotation_strategy", "round_robin"),
        single_proxy=p_dict.get("proxy_url", "")
    )


def get_cached_proxy_settings() -> Dict[str, Any]:
    """Retrieve active proxy settings from memory cache."""
    return _CACHED_PROXY_SETTINGS


class BaseScraper:
    name: str = "BaseScraper"
    country: str = "EU"
    interval_seconds: int = 90
    protection_level: int = 1  # 1: Basic HTML, 2: Medium/Cookie, 3: Aggressive

    def __init__(self):
        self._session: Optional[AsyncSession] = None

    async def get_session(self) -> AsyncSession:
        if self._session is None:
            default_headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,de;q=0.8,pl;q=0.7,fr;q=0.6,it;q=0.5,cs;q=0.4,lt;q=0.3",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }

            self._session = AsyncSession(
                impersonate="chrome120",
                timeout=25,
                headers=default_headers
            )
        return self._session

    async def close(self):
        if self._session:
            try:
                await self._session.close()
            except Exception:
                pass
            self._session = None

    async def fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """Fetch URL content with browser impersonation, proxy pool rotation, and retries."""
        session = await self.get_session()
        for attempt in range(1, 4):
            proxy_url = proxy_pool_manager.get_proxy_for_scraper(self.name)
            proxies_kw = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            try:
                response = await session.get(url, params=params, headers=headers, proxies=proxies_kw)
                if response.status_code == 200:
                    return response.text
                elif response.status_code in (404, 410):
                    logger.debug(f"[{self.name}] Page {url} returned {response.status_code}")
                    return None
                elif response.status_code == 403:
                    logger.warning(
                        f"[{self.name}] 403 Forbidden on {url} (Attempt {attempt}, Proxy: {proxy_url or 'Direct'})"
                    )
                    if attempt == 3:
                        return None
                else:
                    logger.warning(f"[{self.name}] Attempt {attempt} returned status {response.status_code} for {url}")
            except Exception as e:
                logger.warning(f"[{self.name}] Attempt {attempt} failed for {url} (Proxy: {proxy_url or 'Direct'}): {e}")
        return None

    async def fetch_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Any]:
        """Fetch JSON endpoint response with rotating proxy pool support."""
        session = await self.get_session()
        for attempt in range(1, 3):
            proxy_url = proxy_pool_manager.get_proxy_for_scraper(self.name)
            proxies_kw = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            try:
                req_headers = {
                    "Accept": "application/json"
                }
                if headers:
                    req_headers.update(headers)
                response = await session.get(url, params=params, headers=req_headers, proxies=proxies_kw)
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"[{self.name}] JSON fetch attempt {attempt} failed for {url}: {e}")
        return None

    @staticmethod
    def extract_number(text: Optional[str]) -> Optional[int]:
        """Extract first integer digits sequence from text."""
        if not text:
            return None
        cleaned = re.sub(r"[^\d]", "", text)
        return int(cleaned) if cleaned else None

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """Strip and normalize whitespaces in string."""
        if not text:
            return ""
        return " ".join(text.split())

    async def scrape(self, filters: Optional[List[Dict[str, Any]]] = None) -> List[CarListing]:
        """Abstract scraping interface to be implemented by child classes."""
        raise NotImplementedError
