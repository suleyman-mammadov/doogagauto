import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
import asyncio
from database.db import get_db
from curl_cffi.requests import AsyncSession

async def test_all_platforms():
    db_file = str(ROOT_DIR / "data" / "car_arbitrage.db")
    async with get_db(db_file) as db:
        cur = await db.execute("SELECT proxy_url FROM proxy_pool WHERE is_active = 1 LIMIT 1;")
        row = await cur.fetchone()
        if not row:
            # Fallback if no active proxy, try any proxy in pool
            cur = await db.execute("SELECT proxy_url FROM proxy_pool LIMIT 1;")
            row = await cur.fetchone()

    if not row or not row["proxy_url"]:
        print("❌ Error: No proxies found in 'proxy_pool' database table.")
        print("Please insert at least one proxy into proxy_pool before running this test.")
        return

    p_url = row["proxy_url"]
    print(f"Using proxy: {p_url.split('@')[-1] if '@' in p_url else p_url}")

    kw = {"http": p_url, "https": p_url}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    test_urls = [
        ("SS.com (Latvia)", "https://www.ss.com/lv/transport/cars/"),
        ("Autoplius.lt (Lithuania)", "https://autoplius.lt/skelbimai/naudoti-automobiliai"),
        ("Bazos.sk (Slovakia)", "https://auto.bazos.sk/"),
        ("Bazos.cz (Czechia)", "https://auto.bazos.cz/"),
        ("Subito.it (Italy)", "https://www.subito.it/annunci-italia/vendita/auto/"),
        ("Kleinanzeigen.de (Germany)", "https://www.kleinanzeigen.de/s-autos/c216"),
        ("Sauto.cz (Czechia)", "https://www.sauto.cz/inzerce/osobni"),
        ("Leboncoin.fr (France)", "https://www.leboncoin.fr/recherche?category=71"),
        ("Mobile.de (Germany)", "https://suchen.mobile.de/fahrzeuge/search.html?dam=0&isSearchRequest=true&s=Car&vc=Car")
    ]

    print("Testing 1 of the user's proxies on all 9 platforms:")
    async with AsyncSession(impersonate="chrome120", timeout=12, proxies=kw, headers=headers) as s:
        for name, url in test_urls:
            try:
                r = await s.get(url)
                print(f"[{name}] -> Status: {r.status_code}")
            except Exception as e:
                print(f"[{name}] -> Error: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(test_all_platforms())
