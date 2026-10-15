import sys
from pathlib import Path
import hashlib
import logging
import time
import datetime
from typing import List, Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from database.db import get_db, hash_password
except ImportError:
    from .db import get_db, hash_password

from config.settings import settings

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. USER SETTINGS & i18n
# ==============================================================================

async def get_user_language(user_id: int) -> Optional[str]:
    """Retrieve user language preference ('en', 'pl', 'ru')."""
    async with get_db() as db:
        async with db.execute("SELECT language FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row["language"] if row else None


async def set_user_language(user_id: int, language: str) -> None:
    """Upsert user language preference."""
    lang = (language or "en").lower().strip()
    async with get_db() as db:
        await db.execute("""
            INSERT INTO user_settings (user_id, language, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                language = excluded.language,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, lang))
        await db.commit()


async def get_user_notification_settings(user_id: int) -> Dict[str, Any]:
    """Retrieve notification destination preferences for a user."""
    async with get_db() as db:
        async with db.execute("""
            SELECT notification_target, connected_group_id, connected_group_title, connected_group_invite_link
            FROM user_settings WHERE user_id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "notification_target": row["notification_target"] or "dm",
                    "connected_group_id": row["connected_group_id"],
                    "connected_group_title": row["connected_group_title"],
                    "connected_group_invite_link": row["connected_group_invite_link"]
                }
            return {
                "notification_target": "dm",
                "connected_group_id": None,
                "connected_group_title": None,
                "connected_group_invite_link": None
            }


async def set_user_notification_target(user_id: int, target: str) -> None:
    """Switch notification target between 'dm' and 'group'."""
    normalized = "group" if target == "group" else "dm"
    async with get_db() as db:
        await db.execute("""
            INSERT INTO user_settings (user_id, notification_target, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                notification_target = excluded.notification_target,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, normalized))
        await db.commit()


async def link_user_group(user_id: int, group_id: int, group_title: str, invite_link: Optional[str] = None) -> None:
    """Link user to their connected personal supergroup/forum and switch destination to 'group'."""
    async with get_db() as db:
        await db.execute("""
            INSERT INTO user_settings (
                user_id, notification_target, connected_group_id, connected_group_title, connected_group_invite_link, updated_at
            ) VALUES (?, 'group', ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                notification_target = 'group',
                connected_group_id = excluded.connected_group_id,
                connected_group_title = excluded.connected_group_title,
                connected_group_invite_link = excluded.connected_group_invite_link,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, group_id, group_title, invite_link))
        await db.commit()


async def unlink_user_group(user_id: int) -> None:
    """Disconnect user's group and revert notification destination to 'dm'."""
    async with get_db() as db:
        await db.execute("""
            UPDATE user_settings
            SET notification_target = 'dm',
                connected_group_id = NULL,
                connected_group_title = NULL,
                connected_group_invite_link = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()


async def get_user_hot_deals_status(user_id: int) -> bool:
    """Check if user has enabled Hot Deals notifications (default: True)."""
    async with get_db() as db:
        async with db.execute("SELECT hot_deals_enabled FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row is not None and row["hot_deals_enabled"] is not None:
                return bool(row["hot_deals_enabled"])
            return True


async def toggle_user_hot_deals(user_id: int) -> bool:
    """Toggle user's Hot Deals status and return the new state."""
    current_status = await get_user_hot_deals_status(user_id)
    new_status = not current_status
    async with get_db() as db:
        await db.execute("""
            INSERT INTO user_settings (user_id, hot_deals_enabled, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                hot_deals_enabled = excluded.hot_deals_enabled,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, 1 if new_status else 0))
        await db.commit()
    return new_status


async def get_user_hot_deals_settings(user_id: int) -> Dict[str, Any]:
    """Retrieve full Hot Deals preferences for a user."""
    async with get_db() as db:
        async with db.execute("""
            SELECT hot_deals_enabled, hot_deals_min_profit_eur, hot_deals_min_year,
                   hot_deals_max_price_eur, hot_deals_interval_hours, hot_deals_last_sent_at,
                   hot_deals_min_profit_percent, hot_deals_deal_type, hot_deals_max_mileage
            FROM user_settings WHERE user_id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "enabled": bool(row["hot_deals_enabled"]) if row["hot_deals_enabled"] is not None else True,
                    "min_profit_eur": float(row["hot_deals_min_profit_eur"] if row["hot_deals_min_profit_eur"] is not None else 1500.0),
                    "min_year": int(row["hot_deals_min_year"] if row["hot_deals_min_year"] is not None else 2012),
                    "max_price_eur": float(row["hot_deals_max_price_eur"] if row["hot_deals_max_price_eur"] is not None else 0.0),
                    "interval_hours": int(row["hot_deals_interval_hours"] if row["hot_deals_interval_hours"] is not None else 0),
                    "last_sent_at": row["hot_deals_last_sent_at"],
                    "min_profit_percent": float(row["hot_deals_min_profit_percent"] if "hot_deals_min_profit_percent" in row.keys() and row["hot_deals_min_profit_percent"] is not None else 15.0),
                    "deal_type": str(row["hot_deals_deal_type"] if "hot_deals_deal_type" in row.keys() and row["hot_deals_deal_type"] else "all"),
                    "max_mileage": int(row["hot_deals_max_mileage"] if "hot_deals_max_mileage" in row.keys() and row["hot_deals_max_mileage"] is not None else 0)
                }
            return {
                "enabled": True,
                "min_profit_eur": 1500.0,
                "min_year": 2012,
                "max_price_eur": 0.0,
                "interval_hours": 0,
                "last_sent_at": None,
                "min_profit_percent": 15.0,
                "deal_type": "all",
                "max_mileage": 0
            }


async def update_user_hot_deals_settings(user_id: int, **kwargs) -> Dict[str, Any]:
    """Update user's Hot Deals configuration values."""
    current = await get_user_hot_deals_settings(user_id)
    enabled = kwargs.get("enabled", current["enabled"])
    min_profit = kwargs.get("min_profit_eur", current["min_profit_eur"])
    min_year = kwargs.get("min_year", current["min_year"])
    max_price = kwargs.get("max_price_eur", current["max_price_eur"])
    interval = kwargs.get("interval_hours", current["interval_hours"])
    min_profit_pct = kwargs.get("min_profit_percent", current.get("min_profit_percent", 15.0))
    deal_type = kwargs.get("deal_type", current.get("deal_type", "all"))
    max_mileage = kwargs.get("max_mileage", current.get("max_mileage", 0))

    async with get_db() as db:
        await db.execute("""
            INSERT INTO user_settings (
                user_id, hot_deals_enabled, hot_deals_min_profit_eur,
                hot_deals_min_year, hot_deals_max_price_eur, hot_deals_interval_hours,
                hot_deals_min_profit_percent, hot_deals_deal_type, hot_deals_max_mileage,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                hot_deals_enabled = excluded.hot_deals_enabled,
                hot_deals_min_profit_eur = excluded.hot_deals_min_profit_eur,
                hot_deals_min_year = excluded.hot_deals_min_year,
                hot_deals_max_price_eur = excluded.hot_deals_max_price_eur,
                hot_deals_interval_hours = excluded.hot_deals_interval_hours,
                hot_deals_min_profit_percent = excluded.hot_deals_min_profit_percent,
                hot_deals_deal_type = excluded.hot_deals_deal_type,
                hot_deals_max_mileage = excluded.hot_deals_max_mileage,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, 1 if enabled else 0, min_profit, min_year, max_price, interval, min_profit_pct, deal_type, max_mileage))
        await db.commit()

    return await get_user_hot_deals_settings(user_id)


async def update_user_hot_deals_sent_timestamp(user_id: int) -> None:
    """Record that a Hot Deal was sent to this user now."""
    async with get_db() as db:
        await db.execute("""
            UPDATE user_settings 
            SET hot_deals_last_sent_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()


async def get_eligible_hot_deals_users(
    profit_eur: float,
    year: Optional[int],
    price_eur: float,
    profit_percent: float = 0.0,
    mileage_km: Optional[int] = None
) -> List[int]:
    """Find all users eligible to receive this Hot Deal based on their custom criteria and intervals."""
    car_year = year or 0
    car_mileage = mileage_km or 0
    async with get_db() as db:
        async with db.execute("""
            SELECT user_id, hot_deals_interval_hours, hot_deals_last_sent_at,
                   hot_deals_min_profit_percent, hot_deals_deal_type, hot_deals_max_mileage
            FROM user_settings
            WHERE (hot_deals_enabled IS NULL OR hot_deals_enabled = 1)
              AND (hot_deals_min_profit_eur IS NULL OR ? >= hot_deals_min_profit_eur)
              AND (hot_deals_min_year IS NULL OR hot_deals_min_year = 0 OR ? >= hot_deals_min_year OR ? = 0)
              AND (hot_deals_max_price_eur IS NULL OR hot_deals_max_price_eur = 0 OR ? <= hot_deals_max_price_eur)
              AND (hot_deals_min_profit_percent IS NULL OR ? >= hot_deals_min_profit_percent)
              AND (hot_deals_max_mileage IS NULL OR hot_deals_max_mileage = 0 OR ? <= hot_deals_max_mileage OR ? = 0)
        """, (profit_eur, car_year, car_year, price_eur, profit_percent, car_mileage, car_mileage)) as cursor:
            rows = await cursor.fetchall()
            eligible = []
            now_ts = time.time()
            for r in rows:
                deal_type = r["hot_deals_deal_type"] or "all"
                if deal_type == "top_profit" and profit_percent < 25.0 and profit_eur < 2500:
                    continue
                elif deal_type == "new_cars" and car_year > 0 and car_year < 2018:
                    continue
                elif deal_type == "low_mileage" and car_mileage > 100000:
                    continue
                elif deal_type == "low_mileage_cheap" and (car_mileage > 120000 or price_eur > 15000):
                    continue

                interval_h = r["hot_deals_interval_hours"] or 0
                last_sent = r["hot_deals_last_sent_at"]
                if interval_h > 0 and last_sent:
                    try:
                        last_dt = datetime.datetime.strptime(str(last_sent).split(".")[0], "%Y-%m-%d %H:%M:%S")
                        elapsed_seconds = now_ts - last_dt.replace(tzinfo=datetime.timezone.utc).timestamp()
                        if elapsed_seconds < interval_h * 3600:
                            continue
                    except Exception:
                        pass
                eligible.append(int(r["user_id"]))
            return eligible


async def get_all_user_ids() -> List[int]:
    """Get all unique Telegram user IDs from database."""
    async with get_db() as db:
        async with db.execute("""
            SELECT user_id FROM user_settings
            UNION
            SELECT user_id FROM user_filters
        """) as cursor:
            rows = await cursor.fetchall()
            return [int(row["user_id"]) for row in rows if row["user_id"]]


async def get_total_users_count() -> int:
    """Get count of registered users."""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(DISTINCT user_id) as cnt FROM user_settings") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


# ==============================================================================
# 2. USER FILTERS & FORUM TOPICS
# ==============================================================================

async def create_user_filter(
    user_id: int,
    make: str,
    model: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    mileage_min: Optional[int] = None,
    mileage_max: Optional[int] = None,
    price_min_eur: Optional[float] = None,
    price_max_eur: Optional[float] = None,
    fuel_type: str = "all",
    condition: str = "all",
    transmission: str = "all",
    body_type: str = "all",
    target_country: str = "ALL",
    topic_id: int = 0,
    pinned_message_id: Optional[int] = None,
    is_active: int = 1,
    admin_notes: Optional[str] = None,
    # Backward compatibility args
    mileage_max_km: Optional[int] = None,
    target_countries: Optional[str] = None,
    topic_name: Optional[str] = None,
    target_platforms: str = "ALL",
    target_chat_id: Optional[int] = None
) -> int:
    """Insert a new user search filter."""
    actual_mileage_max = mileage_max if mileage_max is not None else mileage_max_km
    actual_country = target_country if target_country != "ALL" else (target_countries or "ALL")

    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO user_filters (
                user_id, make, model, year_min, year_max, mileage_min, mileage_max,
                price_min_eur, price_max_eur, fuel_type, condition, transmission,
                body_type, target_country, target_chat_id, topic_id, pinned_message_id, is_active, is_archived, admin_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (
            user_id,
            make.strip().title(),
            model.strip().title() if model else None,
            year_min,
            year_max,
            mileage_min,
            actual_mileage_max,
            price_min_eur,
            price_max_eur,
            (fuel_type or "all").lower(),
            (condition or "all").lower(),
            (transmission or "all").lower(),
            (body_type or "all").lower(),
            actual_country.strip().upper(),
            target_chat_id,
            topic_id,
            pinned_message_id,
            is_active,
            admin_notes
        ))
        await db.commit()
        return int(cursor.lastrowid or 0)


async def update_filter_pinned_message(filter_id: int, pinned_message_id: int) -> bool:
    """Update pinned_message_id for a filter."""
    async with get_db() as db:
        await db.execute(
            "UPDATE user_filters SET pinned_message_id = ? WHERE id = ?",
            (pinned_message_id, filter_id)
        )
        await db.commit()
        return True


async def update_filter_topic(filter_id: int, topic_id: int, pinned_message_id: Optional[int] = None) -> bool:
    """Update topic id and optionally pinned message id."""
    async with get_db() as db:
        if pinned_message_id is not None:
            await db.execute(
                "UPDATE user_filters SET topic_id = ?, pinned_message_id = ? WHERE id = ?",
                (topic_id, pinned_message_id, filter_id)
            )
        else:
            await db.execute(
                "UPDATE user_filters SET topic_id = ? WHERE id = ?",
                (topic_id, filter_id)
            )
        await db.commit()
        return True


async def get_active_filters() -> List[Dict[str, Any]]:
    """Retrieve all active, non-archived filters for the scraper."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM user_filters WHERE is_active = 1 AND is_archived = 0") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_user_filters(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all filters created by a specific user (excluding archived)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM user_filters WHERE user_id = ? AND is_archived = 0 ORDER BY id DESC",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_filter_by_id(filter_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single filter by its primary ID."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM user_filters WHERE id = ?",
            (filter_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def toggle_filter_status(filter_id: int) -> Optional[int]:
    """Toggle a filter between active (1) and paused (0). Returns new status."""
    async with get_db() as db:
        async with db.execute("SELECT is_active FROM user_filters WHERE id = ?", (filter_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            new_status = 0 if row["is_active"] == 1 else 1

        await db.execute(
            "UPDATE user_filters SET is_active = ? WHERE id = ?",
            (new_status, filter_id)
        )
        await db.commit()
        return new_status


async def delete_filter(filter_id: int) -> bool:
    """Delete a user filter by ID."""
    async with get_db() as db:
        await db.execute("DELETE FROM user_filters WHERE id = ?", (filter_id,))
        await db.commit()
        return True


async def archive_filter(filter_id: int, admin_notes: Optional[str] = None) -> bool:
    """Archive a filter, pause it, and record admin notes."""
    async with get_db() as db:
        if admin_notes is not None:
            await db.execute(
                "UPDATE user_filters SET is_archived = 1, is_active = 0, admin_notes = ? WHERE id = ?",
                (admin_notes, filter_id)
            )
        else:
            await db.execute(
                "UPDATE user_filters SET is_archived = 1, is_active = 0 WHERE id = ?",
                (filter_id,)
            )
        await db.commit()
        return True


async def unarchive_filter(filter_id: int) -> bool:
    """Restore an archived filter back to paused state."""
    async with get_db() as db:
        await db.execute(
            "UPDATE user_filters SET is_archived = 0 WHERE id = ?",
            (filter_id,)
        )
        await db.commit()
        return True


async def update_filter_admin(
    filter_id: int,
    price_max_eur: Optional[float] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    admin_notes: Optional[str] = None
) -> bool:
    """Update filter parameters from Web Admin Panel."""
    async with get_db() as db:
        await db.execute("""
            UPDATE user_filters SET
                price_max_eur = COALESCE(?, price_max_eur),
                year_min = COALESCE(?, year_min),
                year_max = COALESCE(?, year_max),
                admin_notes = COALESCE(?, admin_notes)
            WHERE id = ?
        """, (price_max_eur, year_min, year_max, admin_notes, filter_id))
        await db.commit()
        return True


async def update_user_filter(filter_id: int, **kwargs) -> bool:
    """Dynamically update user filter attributes (make, model, year, price, mileage, limit, age, etc.)."""
    allowed_fields = {
        "make", "model", "year_min", "year_max", "mileage_min", "mileage_max",
        "price_min_eur", "price_max_eur", "fuel_type", "condition", "transmission",
        "body_type", "target_country", "daily_alert_limit", "listing_age_hours",
        "mute_notifications", "min_profit_eur", "is_active", "topic_id"
    }
    updates = []
    values = []
    for k, v in kwargs.items():
        if k in allowed_fields:
            updates.append(f"{k} = ?")
            values.append(v)
    if not updates:
        return False
    values.append(filter_id)
    async with get_db() as db:
        await db.execute(f"UPDATE user_filters SET {', '.join(updates)} WHERE id = ?", tuple(values))
        await db.commit()
    return True


async def increment_filter_alert_count(filter_id: int) -> None:
    """Track alerts delivered today for a specific filter, resetting daily."""
    today_str = time.strftime("%Y-%m-%d")
    async with get_db() as db:
        async with db.execute("SELECT last_alert_date, alerts_sent_today FROM user_filters WHERE id = ?", (filter_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            last_date = row["last_alert_date"] or ""
            current_count = row["alerts_sent_today"] or 0
            if last_date == today_str:
                new_count = current_count + 1
            else:
                new_count = 1
        await db.execute("""
            UPDATE user_filters 
            SET alerts_sent_today = ?, last_alert_date = ?
            WHERE id = ?
        """, (new_count, today_str, filter_id))
        await db.commit()


async def search_seen_listings_for_filter(flt: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Search existing seen_listings in database matching user filter criteria."""
    query = ["SELECT * FROM seen_listings WHERE 1=1"]
    params: List[Any] = []
    
    # Make check
    make = (flt.get("make") or "").strip().lower()
    if make and make not in ("all", "bütün"):
        query.append("AND (LOWER(title) LIKE ? OR (make IS NOT NULL AND LOWER(make) LIKE ?))")
        params.extend([f"%{make}%", f"%{make}%"])
        
    # Model check
    model = (flt.get("model") or "").strip().lower()
    if model and model not in ("-", "all", "none"):
        query.append("AND (LOWER(title) LIKE ? OR (model IS NOT NULL AND LOWER(model) LIKE ?))")
        params.extend([f"%{model}%", f"%{model}%"])
        
    # Year check
    if flt.get("year_min"):
        query.append("AND (year IS NULL OR year >= ?)")
        params.append(flt["year_min"])
    if flt.get("year_max"):
        query.append("AND (year IS NULL OR year <= ?)")
        params.append(flt["year_max"])
        
    # Price check
    if flt.get("price_min_eur"):
        query.append("AND price_eur >= ?")
        params.append(flt["price_min_eur"])
    if flt.get("price_max_eur"):
        query.append("AND price_eur <= ?")
        params.append(flt["price_max_eur"])
        
    # Mileage check
    mileage_max = flt.get("mileage_max")
    if mileage_max:
        query.append("AND (mileage_km IS NULL OR mileage_km <= ?)")
        params.append(mileage_max)
        
    # Country check
    target_country = flt.get("target_country") or flt.get("target_countries") or "ALL"
    if target_country and target_country.upper() != "ALL":
        countries = [c.strip().upper() for c in target_country.split(",")]
        placeholders = ",".join("?" for _ in countries)
        query.append(f"AND UPPER(country_code) IN ({placeholders})")
        params.extend(countries)

    # Time / Age check (listing_age_hours)
    age_hours = flt.get("listing_age_hours", 0) or 0
    if age_hours > 0:
        query.append("AND (first_scraped_at >= datetime('now', ?))")
        params.append(f"-{age_hours} hours")
        
    query.append("ORDER BY first_scraped_at DESC, id DESC LIMIT ?")
    params.append(limit)
    
    sql = " ".join(query)
    async with get_db() as db:
        async with db.execute(sql, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_top_arbitrage_deals(
    limit: int = 10,
    deal_type: str = "all",
    min_profit_eur: float = 1000.0,
    min_profit_pct: float = 15.0,
    min_year: int = 0,
    max_price: float = 0.0,
    max_mileage: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve top hot deals calculated against Poland market benchmarks from database."""
    sql = """
        SELECT s.*, b.median_price_eur as benchmark_eur, b.total_listings_analyzed as sample_cnt
        FROM seen_listings s
        JOIN market_benchmarks b ON (
            LOWER(s.title) LIKE '%' || LOWER(b.make) || '%' 
            AND LOWER(s.title) LIKE '%' || LOWER(b.model) || '%'
            AND s.year = b.year
        )
        WHERE s.price_eur > 0 AND b.median_price_eur > s.price_eur
    """
    params: List[Any] = []
    if min_year > 0:
        sql += " AND s.year >= ?"
        params.append(min_year)
    if max_price > 0:
        sql += " AND s.price_eur <= ?"
        params.append(max_price)
    if max_mileage > 0:
        sql += " AND s.mileage_km <= ?"
        params.append(max_mileage)

    sql += " ORDER BY (b.median_price_eur - s.price_eur) DESC LIMIT ?"
    params.append(limit * 3)

    async with get_db() as db:
        async with db.execute(sql, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            deals = []
            for r in rows:
                p_eur = r["price_eur"]
                b_eur = r["benchmark_eur"]
                gross_diff = b_eur - p_eur
                pct = round((gross_diff / b_eur) * 100, 1) if b_eur else 0
                if gross_diff < min_profit_eur and pct < min_profit_pct:
                    continue
                if deal_type == "top_profit" and pct < 25.0 and gross_diff < 2500:
                    continue
                elif deal_type == "new_cars" and r["year"] and r["year"] < 2018:
                    continue
                elif deal_type == "low_mileage" and r["mileage_km"] and r["mileage_km"] > 100000:
                    continue
                elif deal_type == "low_mileage_cheap" and ((r["mileage_km"] and r["mileage_km"] > 120000) or p_eur > 15000):
                    continue

                d = dict(r)
                d["est_profit_eur"] = round(gross_diff, 0)
                d["est_profit_pct"] = pct
                deals.append(d)
                if len(deals) >= limit:
                    break
            return deals


async def get_all_filters_admin(
    search: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve all filters with filtering for Web Admin table."""
    async with get_db() as db:
        query = "SELECT * FROM user_filters WHERE 1=1"
        params: List[Any] = []

        if status == "active":
            query += " AND is_active = 1 AND is_archived = 0"
        elif status == "paused":
            query += " AND is_active = 0 AND is_archived = 0"
        elif status == "archived":
            query += " AND is_archived = 1"

        if search:
            query += " AND (LOWER(make) LIKE ? OR LOWER(model) LIKE ? OR CAST(user_id AS TEXT) LIKE ?)"
            s_param = f"%{search.lower().strip()}%"
            params.extend([s_param, s_param, s_param])

        query += " ORDER BY id DESC"

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_active_topics() -> List[int]:
    """Retrieve all distinct active topic IDs."""
    async with get_db() as db:
        async with db.execute("""
            SELECT DISTINCT topic_id FROM user_filters 
            WHERE is_active = 1 AND is_archived = 0 AND topic_id > 0
        """) as cursor:
            rows = await cursor.fetchall()
            return [int(row["topic_id"]) for row in rows if row["topic_id"]]


async def get_all_topics() -> List[int]:
    """Retrieve all distinct forum topic IDs."""
    async with get_db() as db:
        async with db.execute("""
            SELECT DISTINCT topic_id FROM user_filters 
            WHERE topic_id > 0 AND is_archived = 0
        """) as cursor:
            rows = await cursor.fetchall()
            return [int(row["topic_id"]) for row in rows if row["topic_id"]]


async def get_total_topics_count() -> int:
    """Get count of all opened non-archived topics."""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(DISTINCT topic_id) as cnt FROM user_filters WHERE topic_id > 0 AND is_archived = 0") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


async def get_active_filters_count() -> int:
    """Get count of active filters."""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) as cnt FROM user_filters WHERE is_active = 1 AND is_archived = 0") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


# ==============================================================================
# 3. MONETIZATION & AD SETTINGS
# ==============================================================================

async def get_ad_settings() -> Dict[str, Any]:
    """Retrieve global ad & sponsorship settings."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM ad_settings WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            
            # Fallback creation
            await db.execute("""
                INSERT OR IGNORE INTO ad_settings (
                    id, is_redirect_enabled, redirect_base_url, custom_affiliate_url, sponsor_text, sponsor_button_name, sponsor_button_url
                ) VALUES (1, 0, '/r/', '', '', '', '')
            """)
            await db.commit()
            return {
                "id": 1,
                "is_redirect_enabled": 0,
                "redirect_base_url": "/r/",
                "custom_affiliate_url": "",
                "sponsor_text": "",
                "sponsor_button_name": "",
                "sponsor_button_url": ""
            }


async def update_ad_settings(
    is_redirect_enabled: Optional[bool] = None,
    redirect_base_url: Optional[str] = None,
    custom_affiliate_url: Optional[str] = None,
    sponsor_text: Optional[str] = None,
    sponsor_button_name: Optional[str] = None,
    sponsor_button_url: Optional[str] = None
) -> Dict[str, Any]:
    """Update global ad and sponsorship settings."""
    current = await get_ad_settings()
    new_redirect = int(is_redirect_enabled) if is_redirect_enabled is not None else current["is_redirect_enabled"]
    new_url = redirect_base_url.strip() if redirect_base_url is not None else current.get("redirect_base_url", "/r/")
    new_affiliate = custom_affiliate_url.strip() if custom_affiliate_url is not None else current.get("custom_affiliate_url", "")
    new_text = sponsor_text.strip() if sponsor_text is not None else current["sponsor_text"]
    new_btn_name = sponsor_button_name.strip() if sponsor_button_name is not None else current["sponsor_button_name"]
    new_btn_url = sponsor_button_url.strip() if sponsor_button_url is not None else current["sponsor_button_url"]

    async with get_db() as db:
        await db.execute("""
            UPDATE ad_settings SET
                is_redirect_enabled = ?,
                redirect_base_url = ?,
                custom_affiliate_url = ?,
                sponsor_text = ?,
                sponsor_button_name = ?,
                sponsor_button_url = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (new_redirect, new_url, new_affiliate, new_text, new_btn_name, new_btn_url))
        await db.commit()

    return await get_ad_settings()


# ==============================================================================
# 4. WEB ADMIN AUTHENTICATION
# ==============================================================================

async def get_admin_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieve admin user by username."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM admin_users WHERE username = ?", (username,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def verify_admin_credentials(username: str, password: str) -> bool:
    """Verify admin login credentials with salted hash."""
    user = await get_admin_user_by_username(username)
    if not user:
        return False
    expected_hash = user["password_hash"]
    given_hash = hash_password(password)
    return expected_hash == given_hash


async def change_admin_password(username: str, new_password: str) -> bool:
    """Update admin password hash."""
    new_hash = hash_password(new_password)
    async with get_db() as db:
        await db.execute("UPDATE admin_users SET password_hash = ? WHERE username = ?", (new_hash, username))
        await db.commit()
        return True


# ==============================================================================
# 5. CLICK ANALYTICS
# ==============================================================================

async def record_click(
    listing_id: Optional[str],
    source_topic_id: Optional[int],
    target_url: str,
    ip_hash: str,
    user_agent: str
) -> int:
    """Record an ad/listing click into analytics."""
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO click_analytics (
                listing_id, source_topic_id, target_url, ip_hash, user_agent, clicked_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (listing_id, source_topic_id, target_url, ip_hash, user_agent))
        await db.commit()
        return int(cursor.lastrowid or 0)


async def get_total_clicks_count() -> int:
    """Get total count of recorded clicks."""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) as cnt FROM click_analytics") as cur:
            row = await cur.fetchone()
            return row["cnt"] if row else 0


async def get_recent_clicks(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent click records for the analytics dashboard."""
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM click_analytics ORDER BY id DESC LIMIT ?
        """, (limit,)) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_clicks_per_day(days: int = 7) -> List[Dict[str, Any]]:
    """Get click aggregation per day for Chart.js line charts."""
    async with get_db() as db:
        async with db.execute("""
            SELECT DATE(clicked_at) as click_date, COUNT(*) as click_count
            FROM click_analytics
            WHERE clicked_at >= DATE('now', '-' || ? || ' days')
            GROUP BY DATE(clicked_at)
            ORDER BY click_date ASC
        """, (days,)) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_country_distribution() -> Dict[str, int]:
    """Get count of active filters grouped by target_country for Chart.js doughnut chart."""
    async with get_db() as db:
        async with db.execute("""
            SELECT target_country, COUNT(*) as cnt
            FROM user_filters
            WHERE is_archived = 0
            GROUP BY target_country
            ORDER BY cnt DESC
        """) as cur:
            rows = await cur.fetchall()
            return {row["target_country"]: row["cnt"] for row in rows}


# ==============================================================================
# 6. BROADCAST CAMPAIGNS (WEB & TELEGRAM)
# ==============================================================================

async def create_broadcast_campaign(
    title: str,
    message_text: str,
    target_type: str,
    total_targets: int,
    image_url: Optional[str] = None,
    button_name: Optional[str] = None,
    button_url: Optional[str] = None
) -> int:
    """Create a new broadcast campaign record."""
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO broadcast_campaigns (
                title, message_text, image_url, button_name, button_url, target_type,
                total_targets, sent_count, failed_count, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 'running', CURRENT_TIMESTAMP)
        """, (title, message_text, image_url, button_name, button_url, target_type, total_targets))
        await db.commit()
        return int(cursor.lastrowid or 0)


async def update_campaign_progress(
    campaign_id: int,
    sent_count: int,
    failed_count: int,
    status: str = "running",
    completed: bool = False
) -> None:
    """Update progress and status of a broadcast campaign."""
    async with get_db() as db:
        if completed:
            await db.execute("""
                UPDATE broadcast_campaigns SET
                    sent_count = ?,
                    failed_count = ?,
                    status = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (sent_count, failed_count, status, campaign_id))
        else:
            await db.execute("""
                UPDATE broadcast_campaigns SET
                    sent_count = ?,
                    failed_count = ?,
                    status = ?
                WHERE id = ?
            """, (sent_count, failed_count, status, campaign_id))
        await db.commit()


async def get_broadcast_campaigns(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve history of broadcast campaigns."""
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM broadcast_campaigns ORDER BY id DESC LIMIT ?
        """, (limit,)) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_broadcast_campaign_by_id(campaign_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a broadcast campaign by ID."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM broadcast_campaigns WHERE id = ?", (campaign_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# Backward-compatible wrapper for Telegram admin handler
async def create_broadcast_history(
    admin_id: int,
    message_text: str,
    target_type: str,
    total_targets: int
) -> int:
    """Create a new broadcast campaign history entry."""
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO broadcast_history (
                admin_id, message_text, target_type, total_targets, sent_count, failed_count, status
            ) VALUES (?, ?, ?, ?, 0, 0, 'running')
        """, (admin_id, message_text, target_type, total_targets))
        await db.commit()
        return int(cursor.lastrowid or 0)


async def update_broadcast_progress(
    broadcast_id: int,
    sent_count: int,
    failed_count: int,
    status: str = "running"
) -> None:
    """Update progress and status of a broadcast campaign."""
    async with get_db() as db:
        await db.execute("""
            UPDATE broadcast_history SET
                sent_count = ?,
                failed_count = ?,
                status = ?
            WHERE id = ?
        """, (sent_count, failed_count, status, broadcast_id))
        await db.commit()


# ==============================================================================
# 7. SCRAPER SEEN LISTINGS & MARKET BENCHMARKS
# ==============================================================================

async def is_listing_seen(platform: str, external_id: str) -> bool:
    """Check if listing has already been processed by (platform, external_id)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT 1 FROM seen_listings WHERE platform = ? AND external_id = ? LIMIT 1",
            (platform, external_id)
        ) as cursor:
            return (await cursor.fetchone()) is not None


async def save_seen_listing(
    platform: str,
    external_id: str,
    country_code: str,
    title: str,
    url: str,
    price_eur: float,
    year: Optional[int] = None,
    mileage_km: Optional[int] = None,
    fuel_type: Optional[str] = None,
    photo_url: Optional[str] = None,
    created_in_source: Optional[str] = None,
    make: Optional[str] = None,
    model: Optional[str] = None
) -> bool:
    """Save newly seen listing into database."""
    async with get_db() as db:
        try:
            await db.execute("""
                INSERT INTO seen_listings (
                    platform, external_id, country_code, title, url, price_eur,
                    year, mileage_km, fuel_type, photo_url, created_in_source, make, model, first_scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(platform, external_id) DO NOTHING
            """, (
                platform, external_id, country_code.upper(), title, url, price_eur,
                year, mileage_km, fuel_type, photo_url, created_in_source,
                make.strip().title() if make else None,
                model.strip().title() if model else None
            ))
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"Failed to save seen listing {platform}/{external_id}: {e}")
            return False


async def get_market_benchmark(
    make: str,
    model: str,
    year: int,
    fuel_type: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve Polish market benchmark price from market_benchmarks."""
    fuel = (fuel_type or "ALL").upper()
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM market_benchmarks 
            WHERE LOWER(make) = LOWER(?) AND LOWER(model) = LOWER(?) AND year = ? AND fuel_type = ?
        """, (make, model, year, fuel)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        async with db.execute("""
            SELECT * FROM market_benchmarks 
            WHERE LOWER(make) = LOWER(?) AND LOWER(model) = LOWER(?) AND year = ?
            ORDER BY total_listings_analyzed DESC LIMIT 1
        """, (make, model, year)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def save_market_benchmark(
    make: str,
    model: str,
    year: int,
    median_price_eur: float,
    total_listings_analyzed: int = 1,
    fuel_type: Optional[str] = None
):
    """Upsert Polish market benchmark median price."""
    fuel = (fuel_type or "ALL").upper()
    async with get_db() as db:
        await db.execute("""
            INSERT INTO market_benchmarks (
                make, model, year, fuel_type, median_price_eur, total_listings_analyzed, last_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(make, model, year, fuel_type) DO UPDATE SET
                median_price_eur = excluded.median_price_eur,
                total_listings_analyzed = excluded.total_listings_analyzed,
                last_updated_at = CURRENT_TIMESTAMP
        """, (
            make.strip().title(), model.strip().title(), year, fuel,
            median_price_eur, total_listings_analyzed
        ))
        await db.commit()


async def get_database_stats() -> Dict[str, Any]:
    """Retrieve overall system and database statistics."""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) as cnt FROM seen_listings") as cur:
            row = await cur.fetchone()
            seen_cnt = row["cnt"] if row else 0

        async with db.execute("SELECT COUNT(*) as cnt FROM user_filters WHERE is_active = 1 AND is_archived = 0") as cur:
            row = await cur.fetchone()
            active_filters = row["cnt"] if row else 0

        async with db.execute("SELECT COUNT(*) as cnt FROM user_filters WHERE is_archived = 0") as cur:
            row = await cur.fetchone()
            total_filters = row["cnt"] if row else 0

        async with db.execute("SELECT COUNT(*) as cnt FROM user_filters WHERE is_archived = 1") as cur:
            row = await cur.fetchone()
            archived_filters = row["cnt"] if row else 0

        async with db.execute("SELECT COUNT(DISTINCT topic_id) as cnt FROM user_filters WHERE topic_id > 0 AND is_archived = 0") as cur:
            row = await cur.fetchone()
            total_topics = row["cnt"] if row else 0

        async with db.execute("SELECT COUNT(DISTINCT user_id) as cnt FROM user_settings") as cur:
            row = await cur.fetchone()
            total_users = row["cnt"] if row else 0

        async with db.execute("SELECT COUNT(*) as cnt FROM click_analytics") as cur:
            row = await cur.fetchone()
            total_clicks = row["cnt"] if row else 0

        async with db.execute("SELECT COUNT(*) as cnt FROM market_benchmarks") as cur:
            row = await cur.fetchone()
            benchmarks_cnt = row["cnt"] if row else 0

        return {
            "total_users": total_users,
            "seen_listings": seen_cnt,
            "active_filters": active_filters,
            "total_filters": total_filters,
            "archived_filters": archived_filters,
            "total_topics": total_topics,
            "total_clicks": total_clicks,
            "cached_benchmarks": benchmarks_cnt
        }


# Aliases for backward compatibility
async def get_poland_benchmark(make: str, model: str, year: int) -> Optional[Dict[str, Any]]:
    return await get_market_benchmark(make=make, model=model, year=year)


async def save_poland_benchmark(
    make: str,
    model: str,
    year: int,
    median_price_pln: float,
    median_price_eur: float,
    sample_count: int = 1
):
    await save_market_benchmark(
        make=make,
        model=model,
        year=year,
        median_price_eur=median_price_eur,
        total_listings_analyzed=sample_count
    )


# ==============================================================================
# SYSTEM CONFIGURATION & TOPIC PERSISTENCE (SYSTEM_KV)
# ==============================================================================

async def get_system_kv(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve string value from system_kv table."""
    async with get_db() as db:
        async with db.execute("SELECT value FROM system_kv WHERE key = ?;", (key,)) as cur:
            row = await cur.fetchone()
            return row["value"] if row else default


async def set_system_kv(key: str, value: str):
    """Store or update key-value pair in system_kv table."""
    async with get_db() as db:
        await db.execute("""
            INSERT INTO system_kv (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP;
        """, (key, value))
        await db.commit()


async def get_hot_deals_topic_id() -> Optional[int]:
    """Retrieve persistent Hot Deals topic thread ID from database."""
    val = await get_system_kv("hot_deals_topic_id")
    if val and val.isdigit():
        return int(val)
    return None


async def set_hot_deals_topic_id(topic_id: int):
    """Save persistent Hot Deals topic thread ID to database."""
    await set_system_kv("hot_deals_topic_id", str(topic_id))


# ==============================================================================
# 8. CAR MAKES & MODELS (DYNAMIC BOT MENUS)
# ==============================================================================

async def get_all_car_makes() -> List[Dict[str, Any]]:
    """Retrieve all car makes ordered by name."""
    async with get_db() as db:
        async with db.execute("""
            SELECT m.id, m.name, COUNT(md.id) as model_count 
            FROM car_makes m
            LEFT JOIN car_models md ON m.id = md.make_id
            GROUP BY m.id, m.name
            ORDER BY m.name ASC;
        """) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def add_car_make(name: str) -> Optional[int]:
    """Add a new car make to database."""
    clean_name = name.strip()
    if not clean_name:
        return None
    async with get_db() as db:
        try:
            cursor = await db.execute("INSERT INTO car_makes (name) VALUES (?);", (clean_name,))
            await db.commit()
            return int(cursor.lastrowid or 0)
        except Exception:
            return None


async def delete_car_make(make_id: int) -> bool:
    """Delete a car make and all associated models."""
    async with get_db() as db:
        await db.execute("DELETE FROM car_models WHERE make_id = ?;", (make_id,))
        await db.execute("DELETE FROM car_makes WHERE id = ?;", (make_id,))
        await db.commit()
        return True


async def get_car_models_by_make_id(make_id: int) -> List[Dict[str, Any]]:
    """Retrieve all models for a specific make ID."""
    async with get_db() as db:
        async with db.execute("SELECT id, make_id, name FROM car_models WHERE make_id = ? ORDER BY name ASC;", (make_id,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_car_models_by_make_name(make_name: str) -> List[str]:
    """Retrieve model names for a given make name."""
    clean_name = make_name.strip()
    async with get_db() as db:
        async with db.execute("""
            SELECT md.name 
            FROM car_models md
            JOIN car_makes m ON md.make_id = m.id
            WHERE LOWER(m.name) = LOWER(?)
            ORDER BY md.name ASC;
        """, (clean_name,)) as cur:
            rows = await cur.fetchall()
            return [row["name"] for row in rows]


async def add_car_model(make_id: int, name: str) -> Optional[int]:
    """Add a model under a make."""
    clean_name = name.strip()
    if not clean_name:
        return None
    async with get_db() as db:
        try:
            cursor = await db.execute("INSERT INTO car_models (make_id, name) VALUES (?, ?);", (make_id, clean_name))
            await db.commit()
            return int(cursor.lastrowid or 0)
        except Exception:
            return None


async def delete_car_model(model_id: int) -> bool:
    """Delete a specific car model."""
    async with get_db() as db:
        await db.execute("DELETE FROM car_models WHERE id = ?;", (model_id,))
        await db.commit()
        return True


# ==============================================================================
# 9. BOT MENU BUTTONS & LABELS
# ==============================================================================

async def get_bot_menu_buttons() -> List[Dict[str, Any]]:
    """Retrieve all configurable bot menu buttons."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM bot_menu_buttons ORDER BY order_index ASC;") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def update_bot_menu_button(button_key: str, label_en: str, label_pl: str, label_ru: str, is_active: bool = True) -> bool:
    """Update localized labels for a menu button."""
    async with get_db() as db:
        await db.execute("""
            UPDATE bot_menu_buttons SET
                label_en = ?,
                label_pl = ?,
                label_ru = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE button_key = ?;
        """, (label_en.strip(), label_pl.strip(), label_ru.strip(), 1 if is_active else 0, button_key))
        await db.commit()
        return True


# ==============================================================================
# 10. MESSAGE TEMPLATES (CARD LAYOUTS)
# ==============================================================================

async def get_message_templates() -> Dict[str, str]:
    """Retrieve car card message templates."""
    async with get_db() as db:
        async with db.execute("SELECT standard_template, hot_deal_template FROM message_templates WHERE id = 1;") as cur:
            row = await cur.fetchone()
            if row:
                return {
                    "standard_template": row["standard_template"],
                    "hot_deal_template": row["hot_deal_template"]
                }
    return {
        "standard_template": "",
        "hot_deal_template": ""
    }


async def update_message_templates(standard_template: str, hot_deal_template: str) -> bool:
    """Update message templates in database."""
    async with get_db() as db:
        await db.execute("""
            UPDATE message_templates SET
                standard_template = ?,
                hot_deal_template = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1;
        """, (standard_template.strip(), hot_deal_template.strip()))
        await db.commit()
        return True


# ==============================================================================
# 11. BROADCAST MESSAGE TRACKING & TELEGRAM DELETION
# ==============================================================================

async def save_broadcast_message(campaign_id: int, chat_id: int, message_id: int, message_thread_id: int = 0) -> None:
    """Save sent broadcast message ID to allow future deletion."""
    async with get_db() as db:
        await db.execute("""
            INSERT INTO broadcast_messages (campaign_id, chat_id, message_id, message_thread_id)
            VALUES (?, ?, ?, ?);
        """, (campaign_id, chat_id, message_id, message_thread_id))
        await db.commit()


async def get_broadcast_messages(campaign_id: int) -> List[Dict[str, Any]]:
    """Retrieve all sent messages for a campaign."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM broadcast_messages WHERE campaign_id = ?;", (campaign_id,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_broadcast_campaign_record(campaign_id: int) -> bool:
    """Delete a broadcast campaign record and associated message log."""
    async with get_db() as db:
        await db.execute("DELETE FROM broadcast_messages WHERE campaign_id = ?;", (campaign_id,))
        await db.execute("DELETE FROM broadcast_campaigns WHERE id = ?;", (campaign_id,))
        await db.commit()
        return True


# ==============================================================================
# 12. PROXY SETTINGS & ROTATING POOL MANAGEMENT
# ==============================================================================

def parse_proxy_line(line: str) -> Optional[str]:
    """Parse various proxy formats (ip:port:user:pass, user:pass@ip:port, http/socks5) into standard URL format."""
    clean = line.strip()
    if not clean or clean.startswith("#"):
        return None

    # Already has protocol
    if clean.startswith("http://") or clean.startswith("https://") or clean.startswith("socks5://") or clean.startswith("socks5h://"):
        return clean

    # Format: host:port:username:password
    parts = clean.split(":")
    if len(parts) == 4:
        host, port, user, password = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        return f"http://{user}:{password}@{host}:{port}"

    # Format: host:port@username:password or username:password@host:port
    if "@" in clean:
        left, right = clean.split("@", 1)
        if ":" in left and ":" in right:
            first_elem = left.split(":")[0]
            # If first element has letters, likely user:pass@host:port
            if any(c.isalpha() for c in first_elem):
                return f"http://{clean}"
            else:
                # host:port@user:pass -> user:pass@host:port
                return f"http://{right.strip()}@{left.strip()}"

    # Format: host:port (unauthenticated)
    if len(parts) == 2 and parts[1].strip().isdigit():
        return f"http://{parts[0].strip()}:{parts[1].strip()}"

    return f"http://{clean}"


async def get_proxy_settings() -> Dict[str, Any]:
    """Retrieve active proxy configuration."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM proxy_settings WHERE id = 1;") as cur:
            row = await cur.fetchone()
            if row:
                cols = row.keys()
                return {
                    "is_enabled": bool(row["is_enabled"]),
                    "proxy_url": row["proxy_url"] or "",
                    "apply_mode": row["apply_mode"] or "protected_only",
                    "rotation_strategy": row["rotation_strategy"] if "rotation_strategy" in cols else "round_robin",
                    "test_status": row["test_status"] or "untested",
                    "last_tested_ip": row["last_tested_ip"] or "",
                    "last_latency_ms": int(row["last_latency_ms"] or 0),
                    "last_tested_at": row["last_tested_at"],
                    "updated_at": row["updated_at"]
                }
            return {
                "is_enabled": False,
                "proxy_url": "",
                "apply_mode": "protected_only",
                "rotation_strategy": "round_robin",
                "test_status": "untested",
                "last_tested_ip": "",
                "last_latency_ms": 0,
                "last_tested_at": None,
                "updated_at": None
            }


async def update_proxy_settings(
    is_enabled: Optional[bool] = None,
    proxy_url: Optional[str] = None,
    apply_mode: Optional[str] = None,
    rotation_strategy: Optional[str] = None
) -> Dict[str, Any]:
    """Upsert or patch proxy configuration and return updated state."""
    current = await get_proxy_settings()
    new_enabled = is_enabled if is_enabled is not None else current.get("is_enabled", False)
    new_url = proxy_url.strip() if proxy_url is not None else current.get("proxy_url", "")
    new_mode = apply_mode.strip() if apply_mode is not None else current.get("apply_mode", "protected_only")
    new_strat = rotation_strategy.strip() if rotation_strategy is not None else current.get("rotation_strategy", "round_robin")

    async with get_db() as db:
        await db.execute("""
            INSERT INTO proxy_settings (id, is_enabled, proxy_url, apply_mode, rotation_strategy, updated_at)
            VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                is_enabled = excluded.is_enabled,
                proxy_url = excluded.proxy_url,
                apply_mode = excluded.apply_mode,
                rotation_strategy = excluded.rotation_strategy,
                updated_at = CURRENT_TIMESTAMP;
        """, (1 if new_enabled else 0, new_url, new_mode, new_strat))
        await db.commit()
    return await get_proxy_settings()


async def record_proxy_test_result(test_status: str, last_tested_ip: str = "", last_latency_ms: int = 0) -> None:
    """Record proxy connectivity test result."""
    async with get_db() as db:
        await db.execute("""
            UPDATE proxy_settings
            SET test_status = ?,
                last_tested_ip = ?,
                last_latency_ms = ?,
                last_tested_at = CURRENT_TIMESTAMP
            WHERE id = 1;
        """, (test_status, last_tested_ip, last_latency_ms))
        await db.commit()


# ==============================================================================
# PROXY POOL (100 - 1000+ ROTATING PROXIES)
# ==============================================================================

async def get_proxy_pool(limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieve list of proxies from the pool."""
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM proxy_pool 
            ORDER BY is_active DESC, success_count DESC, id DESC 
            LIMIT ? OFFSET ?;
        """, (limit, offset)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_active_proxy_urls() -> List[str]:
    """Retrieve all enabled proxy URLs for the active in-memory scraper rotation."""
    async with get_db() as db:
        async with db.execute("SELECT proxy_url FROM proxy_pool WHERE is_active = 1;") as cur:
            rows = await cur.fetchall()
            return [r["proxy_url"] for r in rows if r["proxy_url"]]


async def bulk_insert_proxies(raw_text: str) -> Dict[str, int]:
    """Parse raw proxy text lines and bulk insert into proxy_pool with deduplication."""
    lines = raw_text.strip().splitlines()
    added_count = 0
    duplicate_count = 0
    invalid_count = 0

    async with get_db() as db:
        for line in lines:
            parsed = parse_proxy_line(line)
            if not parsed:
                invalid_count += 1
                continue
            protocol = "socks5" if parsed.startswith("socks") else "http"
            try:
                await db.execute("""
                    INSERT INTO proxy_pool (proxy_url, protocol, is_active)
                    VALUES (?, ?, 1);
                """, (parsed, protocol))
                added_count += 1
            except Exception:
                duplicate_count += 1
        await db.commit()

    return {
        "added": added_count,
        "duplicates": duplicate_count,
        "invalid": invalid_count,
        "total_submitted": len(lines)
    }


async def delete_proxy(proxy_id: int) -> bool:
    """Delete a single proxy by ID."""
    async with get_db() as db:
        await db.execute("DELETE FROM proxy_pool WHERE id = ?;", (proxy_id,))
        await db.commit()
        return True


async def toggle_proxy(proxy_id: int) -> bool:
    """Toggle is_active flag for a proxy."""
    async with get_db() as db:
        async with db.execute("SELECT is_active FROM proxy_pool WHERE id = ?;", (proxy_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False
            new_val = 0 if row["is_active"] else 1

        await db.execute("UPDATE proxy_pool SET is_active = ? WHERE id = ?;", (new_val, proxy_id))
        await db.commit()
        return bool(new_val)


async def clear_all_proxies() -> int:
    """Delete all proxies from the pool."""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM proxy_pool;")
        await db.commit()
        return cursor.rowcount


async def clear_failed_proxies(max_failures: int = 3) -> int:
    """Delete proxies that have accumulated high fail count."""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM proxy_pool WHERE fail_count >= ?;", (max_failures,))
        await db.commit()
        return cursor.rowcount


async def record_proxy_usage(proxy_url: str, success: bool, latency_ms: int = 0, error: str = "") -> None:
    """Update success/fail stats for a proxy after a scrape attempt."""
    async with get_db() as db:
        if success:
            await db.execute("""
                UPDATE proxy_pool 
                SET success_count = success_count + 1,
                    last_latency_ms = ?,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE proxy_url = ?;
            """, (latency_ms, proxy_url))
        else:
            await db.execute("""
                UPDATE proxy_pool 
                SET fail_count = fail_count + 1,
                    last_error = ?,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE proxy_url = ?;
            """, (error[:100], proxy_url))
        await db.commit()


async def get_proxy_pool_stats() -> Dict[str, Any]:
    """Retrieve statistical counters for the proxy pool."""
    async with get_db() as db:
        async with db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN fail_count >= 3 THEN 1 ELSE 0 END) as failed,
                SUM(success_count) as total_success,
                SUM(fail_count) as total_failures,
                AVG(CASE WHEN last_latency_ms > 0 THEN last_latency_ms ELSE NULL END) as avg_latency
            FROM proxy_pool;
        """) as cur:
            row = await cur.fetchone()
            if row:
                return {
                    "total": row["total"] or 0,
                    "active": row["active"] or 0,
                    "failed": row["failed"] or 0,
                    "total_success": row["total_success"] or 0,
                    "total_failures": row["total_failures"] or 0,
                    "avg_latency": int(row["avg_latency"]) if row["avg_latency"] else 0
                }
            return {"total": 0, "active": 0, "failed": 0, "total_success": 0, "total_failures": 0, "avg_latency": 0}


# ==============================================================================
# 11. CURRENCY EXCHANGE RATES (MANUAL & LIVE ECB SYNC)
# ==============================================================================

async def get_currency_rates() -> Dict[str, Any]:
    """Retrieve current currency exchange rates and auto-sync status."""
    async with get_db() as db:
        async with db.execute("SELECT * FROM currency_rates WHERE id = 1;") as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
            return {
                "id": 1,
                "eur_to_pln": 4.30,
                "czk_to_eur": 0.040,
                "eur_to_czk": 25.0,
                "eur_to_usd": 1.08,
                "auto_sync": 1,
                "last_source": "system_default",
                "last_updated_at": "İlkin təyinat"
            }


def apply_currency_rates_to_runtime(rates: Dict[str, Any]) -> None:
    """Synchronize rates dynamically into global settings so all scrapers use them."""
    try:
        if "eur_to_pln" in rates and rates["eur_to_pln"]:
            settings.EUR_TO_PLN_RATE = float(rates["eur_to_pln"])
        if "czk_to_eur" in rates and rates["czk_to_eur"]:
            settings.CZK_TO_EUR_RATE = float(rates["czk_to_eur"])
    except Exception as e:
        logger.warning(f"Could not apply currency rates to runtime settings: {e}")


async def update_currency_rates(
    eur_to_pln: float,
    czk_to_eur: float,
    eur_to_czk: Optional[float] = None,
    eur_to_usd: Optional[float] = None,
    auto_sync: bool = True,
    source: str = "manual"
) -> Dict[str, Any]:
    """Manually update currency exchange rates in database and runtime cache."""
    if not eur_to_czk and czk_to_eur > 0:
        eur_to_czk = round(1.0 / czk_to_eur, 3)
    if not czk_to_eur and eur_to_czk and eur_to_czk > 0:
        czk_to_eur = round(1.0 / eur_to_czk, 5)

    eur_usd = eur_to_usd if eur_to_usd is not None else 1.08

    async with get_db() as db:
        await db.execute("""
            INSERT INTO currency_rates (
                id, eur_to_pln, czk_to_eur, eur_to_czk, eur_to_usd, auto_sync, last_source, last_updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                eur_to_pln = excluded.eur_to_pln,
                czk_to_eur = excluded.czk_to_eur,
                eur_to_czk = excluded.eur_to_czk,
                eur_to_usd = excluded.eur_to_usd,
                auto_sync = excluded.auto_sync,
                last_source = excluded.last_source,
                last_updated_at = CURRENT_TIMESTAMP;
        """, (eur_to_pln, czk_to_eur, eur_to_czk, eur_usd, 1 if auto_sync else 0, source))
        await db.commit()

    updated = await get_currency_rates()
    apply_currency_rates_to_runtime(updated)
    return updated


async def fetch_live_exchange_rates() -> Dict[str, Any]:
    """Fetch live European Central Bank (ECB) exchange rates from public API and update DB."""
    import httpx

    urls_to_try = [
        "https://api.frankfurter.app/latest?from=EUR&to=PLN,CZK,USD",
        "https://open.er-api.com/v6/latest/EUR"
    ]

    last_error = ""
    for api_url in urls_to_try:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(api_url)
                if resp.status_code == 200:
                    data = resp.json()
                    rates = data.get("rates", {})
                    pln_rate = rates.get("PLN")
                    czk_rate = rates.get("CZK")
                    usd_rate = rates.get("USD", 1.08)

                    if pln_rate and czk_rate:
                        eur_to_pln = round(float(pln_rate), 4)
                        eur_to_czk = round(float(czk_rate), 3)
                        czk_to_eur = round(1.0 / eur_to_czk, 5)
                        eur_to_usd = round(float(usd_rate), 4)

                        source_name = "Avropa Mərkəzi Bankı (ECB)"
                        res = await update_currency_rates(
                            eur_to_pln=eur_to_pln,
                            czk_to_eur=czk_to_eur,
                            eur_to_czk=eur_to_czk,
                            eur_to_usd=eur_to_usd,
                            auto_sync=True,
                            source=source_name
                        )
                        return {
                            "success": True,
                            "rates": res,
                            "source": source_name,
                            "message": f"Məzənnələr uğurla yeniləndi (EUR/PLN: {eur_to_pln}, CZK/EUR: {czk_to_eur})"
                        }
        except Exception as e:
            last_error = str(e)
            continue

    current = await get_currency_rates()
    return {
        "success": False,
        "rates": current,
        "error": f"Canlı məzənnə serverlərinə qoşulmaq olmadı: {last_error}"
    }


