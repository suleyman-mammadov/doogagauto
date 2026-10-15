import os
import sys
import hashlib
from pathlib import Path
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiosqlite  # type: ignore
from config.settings import settings

logger = logging.getLogger(__name__)


def hash_password(password: str, salt: str = "doogag_salt_9988") -> str:
    """Generate secure SHA-256 password hash with salt."""
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


@asynccontextmanager
async def get_db(db_path: Optional[str] = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that yields an aiosqlite connection with row_factory set to Row and WAL enabled."""
    path = db_path or settings.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=30000;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        yield db


async def init_db(db_path: Optional[str] = None):
    """Initialize database tables, pragmas, columns, and indexes with auto-migration."""
    path = db_path or settings.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    logger.info(f"Initializing database at: {path}")
    async with get_db(path) as db:
        # 1. user_settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id BIGINT PRIMARY KEY,
                language TEXT DEFAULT 'en',
                notification_target TEXT DEFAULT 'dm',
                connected_group_id BIGINT,
                connected_group_title TEXT,
                connected_group_invite_link TEXT,
                hot_deals_enabled BOOLEAN DEFAULT 1,
                hot_deals_min_profit_eur REAL DEFAULT 1500.0,
                hot_deals_min_year INTEGER DEFAULT 2012,
                hot_deals_max_price_eur REAL DEFAULT 0.0,
                hot_deals_interval_hours INTEGER DEFAULT 0,
                hot_deals_last_sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. user_filters table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT NOT NULL,
                make TEXT NOT NULL,
                model TEXT,
                year_min INTEGER,
                year_max INTEGER,
                mileage_min INTEGER,
                mileage_max INTEGER,
                price_min_eur REAL,
                price_max_eur REAL,
                fuel_type TEXT DEFAULT 'all',
                condition TEXT DEFAULT 'all',
                transmission TEXT DEFAULT 'all',
                body_type TEXT DEFAULT 'all',
                target_country TEXT DEFAULT 'ALL',
                target_chat_id BIGINT,
                topic_id INTEGER NOT NULL DEFAULT 0,
                pinned_message_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                is_archived BOOLEAN DEFAULT 0,
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. ad_settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ad_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                is_redirect_enabled BOOLEAN DEFAULT 0,
                redirect_base_url TEXT DEFAULT '/r/',
                custom_affiliate_url TEXT DEFAULT '',
                sponsor_text TEXT DEFAULT '',
                sponsor_button_name TEXT DEFAULT '',
                sponsor_button_url TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Auto-migration check for ad_settings if existing table lacked custom_affiliate_url
        cursor = await db.execute("PRAGMA table_info(ad_settings)")
        ad_columns = [row["name"] for row in await cursor.fetchall()]
        if "custom_affiliate_url" not in ad_columns:
            await db.execute("ALTER TABLE ad_settings ADD COLUMN custom_affiliate_url TEXT DEFAULT '';")

        # Ensure singleton row exists for ad_settings
        await db.execute("""
            INSERT OR IGNORE INTO ad_settings (
                id, is_redirect_enabled, redirect_base_url, custom_affiliate_url, sponsor_text, sponsor_button_name, sponsor_button_url
            ) VALUES (1, 0, '/r/', '', '', '', '');
        """)

        # 4. broadcast_history table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id BIGINT NOT NULL,
                message_text TEXT NOT NULL,
                target_type TEXT NOT NULL,
                total_targets INTEGER NOT NULL,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 5. admin_users table (Web Admin Panel)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 6. click_analytics table (Redirect Gateway & Analytics)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS click_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT,
                source_topic_id INTEGER,
                target_url TEXT NOT NULL,
                ip_hash TEXT,
                user_agent TEXT,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 7. broadcast_campaigns table (Web Dashboard Campaigns)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message_text TEXT NOT NULL,
                image_url TEXT,
                button_name TEXT,
                button_url TEXT,
                target_type TEXT NOT NULL,
                total_targets INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
        """)

        # 8. seen_listings table (scraper deduplication)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                external_id TEXT NOT NULL,
                country_code TEXT NOT NULL DEFAULT 'EU',
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                price_eur REAL NOT NULL,
                year INTEGER,
                mileage_km INTEGER,
                fuel_type TEXT,
                photo_url TEXT,
                created_in_source TIMESTAMP,
                first_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, external_id)
            );
        """)

        # 9. market_benchmarks table (Poland Otomoto Market Benchmarks)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS market_benchmarks (
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER NOT NULL,
                fuel_type TEXT NOT NULL,
                median_price_eur REAL NOT NULL,
                total_listings_analyzed INTEGER DEFAULT 0,
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(make, model, year, fuel_type)
            );
        """)

        # Ensure unique index exists on seen_listings(platform, external_id)
        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_seen_platform_ext 
            ON seen_listings(platform, external_id);
        """)

        # 10. system_kv table for persistent bot configuration & topic mapping
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_kv (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # car_makes table for dynamic makes
        await db.execute("""
        CREATE TABLE IF NOT EXISTS car_makes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # car_models table linked to makes
        await db.execute("""
        CREATE TABLE IF NOT EXISTS car_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            make_id INTEGER NOT NULL REFERENCES car_makes(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(make_id, name)
        );
        """)

        # menu_items table for customizable bot menus
        await db.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # broadcast_messages table for tracking sent messages to allow recall/deletion
        await db.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            chat_id BIGINT NOT NULL,
            message_id INTEGER NOT NULL,
            message_thread_id INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # message_templates table for custom car listing card formats
        await db.execute("""
        CREATE TABLE IF NOT EXISTS message_templates (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            standard_template TEXT NOT NULL,
            hot_deal_template TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # bot_menu_buttons table for custom button texts across languages
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_menu_buttons (
            button_key TEXT PRIMARY KEY,
            category TEXT NOT NULL DEFAULT 'fsm',
            label_en TEXT NOT NULL,
            label_pl TEXT NOT NULL,
            label_ru TEXT NOT NULL,
            action_type TEXT DEFAULT 'callback',
            url TEXT DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            order_index INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # proxy_settings table for dynamic proxy configuration from web admin
        await db.execute("""
        CREATE TABLE IF NOT EXISTS proxy_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            is_enabled BOOLEAN DEFAULT 0,
            proxy_url TEXT DEFAULT '',
            apply_mode TEXT DEFAULT 'protected_only',
            rotation_strategy TEXT DEFAULT 'round_robin',
            test_status TEXT DEFAULT 'untested',
            last_tested_ip TEXT DEFAULT '',
            last_latency_ms INTEGER DEFAULT 0,
            last_tested_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Migration check for rotation_strategy column
        cursor = await db.execute("PRAGMA table_info(proxy_settings)")
        ps_cols = [row["name"] for row in await cursor.fetchall()]
        if "rotation_strategy" not in ps_cols:
            await db.execute("ALTER TABLE proxy_settings ADD COLUMN rotation_strategy TEXT DEFAULT 'round_robin';")

        await db.execute("""
            INSERT OR IGNORE INTO proxy_settings (
                id, is_enabled, proxy_url, apply_mode, rotation_strategy, test_status, last_tested_ip, last_latency_ms
            ) VALUES (1, 0, '', 'protected_only', 'round_robin', 'untested', '', 0);
        """)

        # proxy_pool table for 100 - 1000+ rotating proxies
        await db.execute("""
        CREATE TABLE IF NOT EXISTS proxy_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proxy_url TEXT UNIQUE NOT NULL,
            protocol TEXT DEFAULT 'http',
            is_active BOOLEAN DEFAULT 1,
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            last_latency_ms INTEGER DEFAULT 0,
            last_tested_ip TEXT DEFAULT '',
            last_error TEXT DEFAULT '',
            last_used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_proxy_pool_active ON proxy_pool(is_active);")

        # currency_rates table for manual & live dynamic exchange rates
        await db.execute("""
        CREATE TABLE IF NOT EXISTS currency_rates (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            eur_to_pln REAL DEFAULT 4.30,
            czk_to_eur REAL DEFAULT 0.040,
            eur_to_czk REAL DEFAULT 25.0,
            eur_to_usd REAL DEFAULT 1.08,
            auto_sync BOOLEAN DEFAULT 1,
            last_source TEXT DEFAULT 'system_default',
            last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.execute("""
            INSERT OR IGNORE INTO currency_rates (
                id, eur_to_pln, czk_to_eur, eur_to_czk, eur_to_usd, auto_sync, last_source
            ) VALUES (1, 4.30, 0.040, 25.0, 1.08, 1, 'system_default');
        """)

        # Seed default message template if not exists
        default_standard_tpl = (
            "{header_badge}\n"
            "<b>Source:</b> {country_badge} ({platform})\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🚗 <b>{title}</b>\n"
            "{specs_text}\n\n"
            "💶 <b>Purchase Price:</b> <b>{price_eur} €</b>{local_price_str} (~{price_pln} PLN)\n"
            "🇵🇱 <b>Poland Market Price (Otomoto):</b> <b>~{poland_median_pln} PLN</b> (~{poland_median_eur} €)\n"
            "   <i>(Based on {sample_count} similar listings on Otomoto)</i>\n\n"
            "📊 <b>Import Costs (to Poland):</b>\n"
            " ├─ 🚚 Logistics ({country}): ~{transport_cost_pln} PLN (~{transport_cost_eur} €)\n"
            " ├─ 📑 Excise Tax ({akcyza_percent}): ~{akcyza_cost_pln} PLN (~{akcyza_cost_eur} €)\n"
            " └─ 🛠️ Docs / Inspection: ~{registration_cost_pln} PLN (~{registration_cost_eur} €)\n"
            "🏷️ <b>Total Landed Cost:</b> <b>~{total_landed_cost_pln} PLN</b> (~{total_landed_cost_eur} €)\n\n"
            "{profit_emoji} <b>Estimated Net Profit:</b> <b>{profit_sign}{profit_pln} PLN</b> ({profit_sign}{profit_eur} €)\n"
            "📈 <b>Profit Margin:</b> <b>{profit_sign}{profit_margin}%</b>"
        )
        default_hot_deal_tpl = (
            default_standard_tpl + "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 <i>This deal is ≥15% below Poland market price or estimated net profit is ≥1 500 €!</i>"
        )
        await db.execute("""
            INSERT OR IGNORE INTO message_templates (id, standard_template, hot_deal_template)
            VALUES (1, ?, ?)
        """, (default_standard_tpl, default_hot_deal_tpl))

        # Seed car_makes and car_models from defaults if empty
        async with db.execute("SELECT COUNT(*) as cnt FROM car_makes") as c:
            row = await c.fetchone()
            makes_cnt = row["cnt"] if row else 0
            if makes_cnt == 0:
                default_makes_and_models = {
                    "BMW": ["3 Series", "5 Series", "1 Series", "X5", "X3", "X1", "7 Series", "4 Series", "X6", "2 Series", "X4", "6 Series"],
                    "Mercedes-Benz": ["C-Class", "E-Class", "A-Class", "S-Class", "GLC", "GLE", "CLA", "B-Class", "GLA", "CLS", "GLS", "Vito"],
                    "Audi": ["A4", "A6", "A3", "Q5", "Q7", "A5", "Q3", "A1", "Q8", "A7", "A8", "TT"],
                    "Volkswagen": ["Golf", "Passat", "Tiguan", "Polo", "Touran", "Arteon", "Touareg", "T-Roc", "Caddy", "T-Cross", "Sharan", "Scirocco"],
                    "Toyota": ["Corolla", "RAV4", "Yaris", "Camry", "C-HR", "Auris", "Avensis", "Land Cruiser", "Prius", "Aygo", "Hilux", "Supra"],
                    "Skoda": ["Octavia", "Superb", "Fabia", "Kodiaq", "Karoq", "Kamiq", "Scala", "Rapid", "Yeti", "Citigo", "Roomster", "Enyaq"],
                    "Ford": ["Focus", "Mondeo", "Fiesta", "Kuga", "Puma", "C-Max", "S-Max", "Mustang", "Transit", "Galaxy", "EcoSport", "Ranger"],
                    "Volvo": ["XC60", "XC90", "V60", "V90", "XC40", "V40", "S60", "S90", "V70", "S80", "XC70", "C30"],
                    "Renault": ["Megane", "Clio", "Scenic", "Kadjar", "Captur", "Talisman", "Espace", "Koleos"],
                    "Peugeot": ["308", "508", "3008", "208", "5008", "2008", "407", "207"],
                    "Hyundai": ["Tucson", "i30", "Santa Fe", "i20", "Kona", "i40", "ix35", "Ioniq"],
                    "Kia": ["Sportage", "Ceed", "Optima", "Sorento", "Rio", "Stonic", "Niro", "Proceed"],
                    "Opel": ["Astra", "Insignia", "Corsa", "Mokka", "Zafira", "Grandland", "Crossland"],
                    "Seat": ["Leon", "Ibiza", "Ateca", "Arona", "Alhambra", "Tarraco", "Toledo"],
                    "Porsche": ["Cayenne", "Panamera", "Macan", "911", "Taycan", "Boxster", "Cayman"],
                    "Mazda": ["6", "3", "CX-5", "CX-3", "CX-30", "MX-5", "2", "CX-60"],
                    "Nissan": ["Qashqai", "X-Trail", "Juke", "Micra", "Leaf", "Navara", "Note", "370Z"],
                    "Honda": ["Civic", "CR-V", "Accord", "HR-V", "Jazz", "Insight", "FR-V", "Civic Type R"]
                }
                for mk_name, models in default_makes_and_models.items():
                    cursor = await db.execute("INSERT OR IGNORE INTO car_makes (name) VALUES (?)", (mk_name,))
                    make_id = cursor.lastrowid
                    if not make_id:
                        async with db.execute("SELECT id FROM car_makes WHERE name = ?", (mk_name,)) as cur:
                            row = await cur.fetchone()
                            make_id = row["id"] if row else None
                    if make_id:
                        for mdl_name in models:
                            await db.execute("INSERT OR IGNORE INTO car_models (make_id, name) VALUES (?, ?)", (make_id, mdl_name))

        # Seed default button labels if empty
        default_buttons = [
            ("btn_model", "fsm", "🚘 Model", "🚘 Model", "🚘 Модель", 1),
            ("btn_year", "fsm", "📅 Year Range", "📅 Rocznik", "📅 Диапазон Лет", 2),
            ("btn_mileage", "fsm", "🧭 Mileage (km)", "🧭 Przebieg (km)", "🧭 Пробег (км)", 3),
            ("btn_price", "fsm", "💰 Price (€)", "💰 Cena (€)", "💰 Цена (€)", 4),
            ("btn_fuel", "fsm", "⛽ Fuel", "⛽ Paliwo", "⛽ Топливо", 5),
            ("btn_condition", "fsm", "🛠 Condition", "🛠 Stan", "🛠 Состояние", 6),
            ("btn_transmission", "fsm", "⚙️ Gearbox", "⚙️ Skrzynia", "⚙️ Коробка", 7),
            ("btn_body_type", "fsm", "🏎 Body Type", "🏎 Typ Nadwozia", "🏎 Тип Кузова", 8),
            ("btn_country", "fsm", "🌍 Target Country", "🌍 Kraj", "🌍 Страна", 9),
            ("btn_submit_topic", "fsm", "🚀 Launch Search & Open Topic", "🚀 Rozpocznij i Otwórz Temat", "🚀 Запустить Поиск и Создать Тему", 10),
            ("btn_cancel", "fsm", "❌ Cancel", "❌ Anuluj", "❌ Отмена", 11),
            ("btn_new_search", "main", "➕ New Search", "➕ Nowe Wyszukiwanie", "➕ Новый Поиск", 12),
            ("btn_my_topics", "main", "📋 My Search Topics", "📋 Moje Tematy", "📋 Мои Темы", 13),
            ("btn_stats", "main", "📊 Statistics", "📊 Statystyki", "📊 Статистика", 14),
            ("btn_help", "main", "ℹ️ Help & Guide", "ℹ️ Pomoc i Zasady", "ℹ️ Помощь и Инфо", 15),
            ("btn_settings", "main", "⚙️ Settings", "⚙️ Ustawienia", "⚙️ Настройки", 16)
        ]
        for b_key, b_cat, l_en, l_pl, l_ru, o_idx in default_buttons:
            await db.execute("""
                INSERT OR IGNORE INTO bot_menu_buttons (button_key, category, label_en, label_pl, label_ru, order_index)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (b_key, b_cat, l_en, l_pl, l_ru, o_idx))


        # Auto-migration helpers for user_filters
        cursor = await db.execute("PRAGMA table_info(user_filters)")
        columns = [row["name"] for row in await cursor.fetchall()]
        if "mileage_min" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN mileage_min INTEGER;")
        if "mileage_max" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN mileage_max INTEGER;")
        if "price_min_eur" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN price_min_eur REAL;")
        if "condition" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN condition TEXT DEFAULT 'all';")
        if "body_type" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN body_type TEXT DEFAULT 'all';")
        if "target_country" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN target_country TEXT DEFAULT 'ALL';")
        if "pinned_message_id" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN pinned_message_id INTEGER;")
        if "year_max" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN year_max INTEGER;")
        if "transmission" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN transmission TEXT DEFAULT 'all';")
        if "fuel_type" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN fuel_type TEXT DEFAULT 'all';")
        if "is_archived" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN is_archived BOOLEAN DEFAULT 0;")
        if "admin_notes" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN admin_notes TEXT;")
        if "daily_alert_limit" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN daily_alert_limit INTEGER DEFAULT 0;")
        if "alerts_sent_today" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN alerts_sent_today INTEGER DEFAULT 0;")
        if "last_alert_date" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN last_alert_date TEXT DEFAULT '';")
        if "listing_age_hours" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN listing_age_hours INTEGER DEFAULT 0;")
        if "mute_notifications" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN mute_notifications BOOLEAN DEFAULT 0;")
        if "min_profit_eur" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN min_profit_eur REAL DEFAULT 0.0;")
        if "target_chat_id" not in columns:
            await db.execute("ALTER TABLE user_filters ADD COLUMN target_chat_id BIGINT;")

        # Auto-migration helpers for user_settings
        cursor = await db.execute("PRAGMA table_info(user_settings)")
        us_cols = [row["name"] for row in await cursor.fetchall()]
        if "notification_target" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN notification_target TEXT DEFAULT 'dm';")
        if "connected_group_id" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN connected_group_id BIGINT;")
        if "connected_group_title" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN connected_group_title TEXT;")
        if "connected_group_invite_link" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN connected_group_invite_link TEXT;")
        if "hot_deals_enabled" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_enabled BOOLEAN DEFAULT 1;")
        if "hot_deals_min_profit_eur" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_min_profit_eur REAL DEFAULT 1500.0;")
        if "hot_deals_min_year" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_min_year INTEGER DEFAULT 2012;")
        if "hot_deals_max_price_eur" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_max_price_eur REAL DEFAULT 0.0;")
        if "hot_deals_interval_hours" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_interval_hours INTEGER DEFAULT 0;")
        if "hot_deals_last_sent_at" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_last_sent_at TIMESTAMP;")
        if "hot_deals_min_profit_percent" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_min_profit_percent REAL DEFAULT 15.0;")
        if "hot_deals_deal_type" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_deal_type TEXT DEFAULT 'all';")
        if "hot_deals_max_mileage" not in us_cols:
            await db.execute("ALTER TABLE user_settings ADD COLUMN hot_deals_max_mileage INTEGER DEFAULT 0;")

        # Auto-migration helpers for seen_listings
        cursor = await db.execute("PRAGMA table_info(seen_listings)")
        sl_cols = [row["name"] for row in await cursor.fetchall()]
        if "make" not in sl_cols:
            await db.execute("ALTER TABLE seen_listings ADD COLUMN make TEXT;")
        if "model" not in sl_cols:
            await db.execute("ALTER TABLE seen_listings ADD COLUMN model TEXT;")

        # Initialize default web admin account if empty
        async with db.execute("SELECT COUNT(*) as cnt FROM admin_users") as c:
            row = await c.fetchone()
            admin_cnt = row["cnt"] if row else 0
            if admin_cnt == 0:
                def_user = settings.WEB_ADMIN_USERNAME
                def_pass_hash = hash_password(settings.WEB_ADMIN_PASSWORD)
                await db.execute("""
                    INSERT INTO admin_users (username, password_hash)
                    VALUES (?, ?)
                """, (def_user, def_pass_hash))
                logger.info(f"Initialized default Web Admin account: '{def_user}'")

        # Indexes for fast query lookup
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_settings_lang ON user_settings(language);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_filters_active ON user_filters(is_active);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_filters_archived ON user_filters(is_archived);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_filters_user ON user_filters(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_filters_topic ON user_filters(topic_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_click_analytics_date ON click_analytics(clicked_at);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_status ON broadcast_campaigns(status);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_seen_lookup ON seen_listings(platform, external_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_benchmarks_lookup ON market_benchmarks(make, model, year, fuel_type);")

        await db.commit()
    logger.info("Database initialized successfully with WAL optimization and complete Web Admin schema.")
