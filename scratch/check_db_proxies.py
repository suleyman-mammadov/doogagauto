import sys
sys.path.insert(0, ".")
import asyncio
from database.db import get_db

async def main():
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM proxy_settings WHERE id = 1;")
        row = await cur.fetchone()
        print("=== PROXY SETTINGS ===")
        print(dict(row) if row else "None")

        cur2 = await db.execute("SELECT id, is_active, success_count, fail_count, last_latency_ms, last_error, proxy_url FROM proxy_pool;")
        rows = await cur2.fetchall()
        print(f"\n=== PROXY POOL ({len(rows)} proxies) ===")
        for r in rows:
            d = dict(r)
            # mask user/pass
            url = d["proxy_url"]
            print(f"ID: {d['id']} | Active: {d['is_active']} | Success: {d['success_count']} | Fail: {d['fail_count']} | Latency: {d['last_latency_ms']}ms | Last Error: '{d['last_error']}'")

if __name__ == "__main__":
    asyncio.run(main())
