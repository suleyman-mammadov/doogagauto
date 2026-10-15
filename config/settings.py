from typing import Optional, Union, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
from pydantic import Field, field_validator  # type: ignore


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Bot Settings
    BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token")
    GROUP_CHAT_ID: Union[int, str] = Field(
        default="@doogagauto", 
        description="Target Telegram Supergroup (@username or -100xxx ID)"
    )

    # Static Forum Topics (Default thread IDs in Supergroup)
    SETTINGS_TOPIC_ID: Optional[int] = Field(default=2, description="Thread ID for ⚙️ #Settings forum topic")
    HOT_DEALS_TOPIC_ID: Optional[int] = Field(default=None, description="Thread ID for 🔥 #HotDeals forum topic")
    MARKET_PRICES_TOPIC_ID: Optional[int] = Field(default=6, description="Thread ID for 📊 #MarketPrices forum topic")
    COMMUNITY_TOPIC_ID: Optional[int] = Field(default=12, description="Thread ID for 💬 #Community forum topic")

    @field_validator(
        "SETTINGS_TOPIC_ID", 
        "HOT_DEALS_TOPIC_ID", 
        "MARKET_PRICES_TOPIC_ID", 
        "COMMUNITY_TOPIC_ID", 
        mode="before"
    )
    @classmethod
    def parse_topic_id(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            v_clean = v.strip()
            if "/" in v_clean:
                v_clean = v_clean.split("/")[-1]
            if v_clean.isdigit():
                return int(v_clean)
        try:
            return int(v)
        except Exception:
            return None

    # Admin Telegram IDs
    ADMIN_USER_IDS: list[int] = Field(
        default_factory=list,
        description="List of admin Telegram user IDs authorized for /admin"
    )

    @field_validator("ADMIN_USER_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if not v:
            return []
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, str):
            clean = v.strip().strip("[]")
            if not clean:
                return []
            ids = []
            for item in clean.split(","):
                item_s = item.strip().strip("\"'")
                if item_s.isdigit():
                    ids.append(int(item_s))
            return ids
        if isinstance(v, (list, tuple, set)):
            return [int(x) for x in v if str(x).isdigit()]
        return []

    # Web Admin Dashboard Settings
    WEB_HOST: str = Field(default="0.0.0.0", description="Web admin server bind host")
    WEB_PORT: int = Field(default=8000, description="Web admin server port")
    WEB_ADMIN_USERNAME: str = Field(default="admin", description="Web admin username")
    WEB_ADMIN_PASSWORD: str = Field(default="admin123", description="Web admin password")
    SECRET_KEY: str = Field(default="doogag-secret-key-change-in-production-9988", description="Session encryption secret")
    WEB_BASE_URL: str = Field(default="http://localhost:8000", description="Base public URL of the web server for redirects")

    # Database Settings
    DATABASE_PATH: str = Field(default="data/car_arbitrage.db", description="SQLite database file path")

    # Financial & Currency Settings
    EUR_TO_PLN_RATE: float = Field(default=4.30, description="Exchange rate: 1 EUR in PLN")
    CZK_TO_EUR_RATE: float = Field(default=0.040, description="Exchange rate: 1 CZK in EUR (~25 CZK/EUR)")

    # Arbitrage & Hot Deal Thresholds
    HOT_DEAL_THRESHOLD_PERCENT: float = Field(
        default=15.0, 
        description="Minimum profit percent to flag as Hot Deal (>=15%)"
    )
    HOT_DEAL_MIN_PROFIT_EUR: float = Field(
        default=1500.0,
        description="Minimum absolute profit in EUR to flag as Hot Deal (>=1500 EUR)"
    )
    HOT_DEAL_DAILY_LIMIT: int = Field(
        default=10,
        description="Maximum Hot Deals alerts to post per day (0 = unlimited)"
    )

    # Polish Import Costs & Akcyza (Excise Tax)
    ESTIMATED_REGISTRATION_PLN: float = Field(
        default=300.0, 
        description="Technical inspection and doc registration fee in Poland (PLN)"
    )
    AKCYZA_STANDARD_RATE: float = Field(
        default=0.031, 
        description="Polish Excise tax for petrol/diesel engines <= 2.0L (3.1%)"
    )
    AKCYZA_HIGH_CAPACITY_RATE: float = Field(
        default=0.186, 
        description="Polish Excise tax for petrol/diesel engines > 2.0L (18.6%)"
    )
    AKCYZA_HYBRID_STANDARD_RATE: float = Field(
        default=0.0155,
        description="Polish Excise tax for hybrid engines <= 2.0L (1.55%)"
    )
    AKCYZA_HYBRID_HIGH_RATE: float = Field(
        default=0.093,
        description="Polish Excise tax for hybrid engines > 2.0L (9.3%)"
    )
    AKCYZA_EV_RATE: float = Field(
        default=0.0,
        description="Polish Excise tax for full electric vehicles (0.0%)"
    )

    # Country-specific Logistics Costs to Poland (EUR)
    # Baltic: 350-500€, Slovakia/Czechia: 250-400€, Germany: 400-600€, France/Italy/Netherlands: 700-1000€
    LOGISTICS_RATES_EUR: Dict[str, float] = Field(
        default={
            "LV": 400.0,  # Latvia
            "LT": 400.0,  # Lithuania
            "EE": 450.0,  # Estonia
            "SK": 300.0,  # Slovakia
            "CZ": 300.0,  # Czechia
            "DE": 500.0,  # Germany
            "FR": 850.0,  # France
            "IT": 850.0,  # Italy
            "NL": 800.0,  # Netherlands
            "BE": 800.0,  # Belgium
            "AT": 550.0,  # Austria
            "ES": 950.0,  # Spain
            "SE": 750.0,  # Sweden
            "HU": 450.0,  # Hungary
            "SI": 550.0,  # Slovenia
            "HR": 600.0,  # Croatia
            "PL": 0.0,    # Domestic (Poland)
            "DEFAULT": 500.0
        },
        description="Estimated vehicle transport costs to Poland by country code"
    )

    # Scraper Intervals (seconds)
    SS_LATVIA_INTERVAL: int = Field(default=75, description="SS.com scrape interval (sec)")
    BAZOS_SK_INTERVAL: int = Field(default=75, description="Bazos.sk scrape interval (sec)")
    BAZOS_CZ_INTERVAL: int = Field(default=75, description="Bazos.cz scrape interval (sec)")
    SAUTO_CZ_INTERVAL: int = Field(default=90, description="Sauto.cz scrape interval (sec)")
    AUTOPLIUS_LT_INTERVAL: int = Field(default=100, description="Autoplius.lt scrape interval (sec)")
    MOBILE_DE_INTERVAL: int = Field(default=120, description="Mobile.de scrape interval (sec)")
    KLEINANZEIGEN_DE_INTERVAL: int = Field(default=120, description="Kleinanzeigen.de scrape interval (sec)")
    LEBONCOIN_FR_INTERVAL: int = Field(default=150, description="Leboncoin.fr scrape interval (sec)")
    SUBITO_IT_INTERVAL: int = Field(default=150, description="Subito.it scrape interval (sec)")
    OTOMOTO_CACHE_HOURS: int = Field(default=24, description="Otomoto benchmark cache expiration (hours)")

    # Proxy Settings
    PROXY_URL: Optional[str] = Field(default=None, description="Optional rotating residential proxy URL (e.g. http://user:pass@proxy.example.com:8080)")

    # System
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")


settings = Settings()
