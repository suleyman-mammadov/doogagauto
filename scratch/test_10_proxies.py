import sys
sys.path.insert(0, ".")
import asyncio
from database.db import get_db
from curl_cffi.requests import AsyncSession

async def test_proxies_live():
    async with get_db() as db:
        cur = await db.execute("SELECT id, proxy_url FROM proxy_pool WHERE is_active = 1;")
        proxies = list(await cur.fetchall())

    print(f"Testing {len(proxies)} proxies against Mobile.de and IP detector...")

    for p in proxies:
        pid = p["id"]
        p_url = p["proxy_url"]
        kw = {"http": p_url, "https": p_url}
        print(f"\n--- Testing Proxy ID {pid} ---")

        # 1. IP check
        try:
            async with AsyncSession(impersonate="chrome120", timeout=10, proxies=kw) as s:
                r = await s.get("https://api.ipify.org?format=json")
                if r.status_code == 200:
                    ext_ip = r.json().get("ip")
                    print(f"  [IP Check] OK! External IP: {ext_ip}")
                else:
                    print(f"  [IP Check] Failed status: {r.status_code}")
        except Exception as e:
            print(f"  [IP Check] Exception: {e}")

        # 2. Mobile.de test
        try:
            mobile_url = "https://suchen.mobile.de/fahrzeuge/search.html?dam=0&isSearchRequest=true&s=Car&vc=Car"
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1"
            }
            async with AsyncSession(impersonate="chrome120", timeout=12, proxies=kw, headers=headers) as s:
                r_mob = await s.get(mobile_url)
                print(f"  [Mobile.de] Status: {r_mob.status_code} (HTML length: {len(r_mob.text)})")
                if r_mob.status_code == 403:
                    print("  [Mobile.de] Got 403 Forbidden!")
                elif r_mob.status_code == 200:
                    print("  [Mobile.de] SUCCESS 200 OK!")
        except Exception as e:
            print(f"  [Mobile.de] Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxies_live())
