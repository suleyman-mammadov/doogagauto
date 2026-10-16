# 🚗 Schengen Car Arbitrage & Live Scanner Bot (Pan-European Edition)

**An automated real-time scanning system across the Schengen zone for second-hand vehicles and classified platforms, designed for buyers, dealers, and car flippers in Poland.**

The system compares regional prices against Polish market benchmark values (**Otomoto.pl** median prices), calculates net profit margins (arbitrage) accounting for logistics, customs, and registration costs, and delivers real-time listing cards directly to dedicated forum topics (**Topics**) in a Telegram supergroup.

---

## 📌 1. Schengen Zone Platform Matrix

Platforms are categorized into two primary tiers:
* **Classifieds / Peer-to-Peer (P2P):** Direct from owners, zero dealer markup, where the cheapest emergency and fast-sale listings appear.
* **Professional Auto Portals (B2C / Aggregators):** Clean structured filtering with higher anti-bot security..

| Region | Country | Platforms | Security / Tier |
| :--- | :--- | :--- | :--- |
| **Western Europe** | 🇩🇪 Germany | **Mobile.de**, **Kleinanzeigen.de**, AutoScout24.de | Tier 3 (curl_cffi Chrome Impersonation) |
| **Western Europe** | 🇫🇷 France | **Leboncoin.fr**, LaCentrale.fr, ParuVendu.fr | Tier 3 (curl_cffi Chrome Impersonation) |
| **Western Europe** | 🇮🇹 Italy | **Subito.it**, AutoScout24.it, Automobile.it | Tier 3 (curl_cffi Chrome Impersonation) |
| **Baltics** | 🇱🇹 Lithuania | **Autoplius.lt**, Autogidas.lt, Skelbiu.lt | Tier 2 (Medium / HTTP/2) |
| **Baltics** | 🇱🇻 Latvia | **SS.com** (formerly ss.lv), Dalder.lv | Tier 1 (Simple HTML Lexbor) |
| **Central Europe** | 🇨🇿 Czechia | **Bazos.cz**, **Sauto.cz**, TipCars.com | Tier 1 / 2 (CZK -> EUR conversion) |
| **Central Europe** | 🇸🇰 Slovakia | **Bazos.sk**, Autobazar.eu, Autobazar.sk | Tier 1 (Simple HTML Lexbor) |
| **Nordic & Other** | 🇳🇱 Netherlands, 🇧🇪 Belgium, 🇦🇹 Austria | Marktplaats.nl, 2dehands.be, Willhaben.at | Tier 2 / 3 |
| **Poland (Benchmark)** | 🇵🇱 Poland | **Otomoto.pl** | Benchmark Median Price Generator |

---

## 🛡️ 2. Scraping Architecture & Anti-Bot Strategy

* **Tier 1 (Simple HTML):** Minimal bot protection, static pages (`SS.com`, `Bazos.sk`, `Bazos.cz`) — `curl_cffi` + `selectolax.lexbor` parser (60–90 seconds).
* **Tier 2 (Moderate Protection):** Lightweight JS / Cookie / User-Agent filtering (`Autoplius.lt`, `Sauto.cz`) — `curl_cffi` (Chrome Impersonation) + HTTP/2 (90–120 seconds).
* **Tier 3 (Aggressive Protection):** Cloudflare / DataDome / Akamai (`Mobile.de`, `Otomoto.pl`, `Leboncoin.fr`, `Subito.it`) — `curl_cffi` browser impersonation and mobile API structures (120–180 seconds).
* **Delta-Scanning:** Rather than full site scraping, only the first 10–25 listings on page 1 sorted by `sort=created_desc` are fetched.
* **Deduplication:** Every incoming listing is checked against unique `(platform, external_id)` keys in SQLite `seen_listings`.

---

## 💰 3. Arbitrage & Margin Calculation Engine

For each foreign listing, the algorithm fetches the median market price in Poland (**Otomoto.pl**) and calculates net profit using this formula:

$$\text{Net Profit} = \text{Poland Median Selling Price (EUR)} - (\text{Purchase Price} + \text{Logistics} + \text{Excise Tax} + \text{Registration})$$

### Logistics Costs (Dynamic Regional Rates):
* **Baltics (Lithuania / Latvia / Estonia):** $\approx 400\text{ EUR}$
* **Slovakia / Czechia:** $\approx 300\text{ EUR}$
* **Germany:** $\approx 500\text{ EUR}$
* **France / Italy / Netherlands / Spain:** $\approx 850\text{ EUR}$
* **Other:** $\approx 500\text{ EUR}$

### Polish Excise Duty (Akcyza):
* Engine capacity $\le 2.0\text{L}$: **$3.1\%$**
* Engine capacity $> 2.0\text{L}$: **$18.6\%$**
* Hybrid ($\le 2.0\text{L}$): **$1.55\%$**
* Hybrid ($> 2.0\text{L}$): **$9.3\%$**
* Full Electric (EV): **$0\%$**
* Polish registration and initial technical inspection: **~300 PLN (~70 EUR)**

> 🔥 **Hot Deals:** If $\text{Net Profit} \ge 1,500\text{ EUR}$ or price is $\ge 15\%$ below market value, the listing is automatically forwarded to the **`#HotDeals`** topic!

---

## 🏛️ 4. Telegram Forum & Dynamic Topic Architecture

Telegram Group: `@doogagauto` (Supergroup with Topics enabled)

### Static Topics:
* ⚙️ **`#Settings`** (ID: Topic 2): User bot controls, new filter configuration, and status monitoring.
* 🔥 **`#HotDeals`** (ID: Topic 4): High-arbitrage anomaly deals across Schengen with $\ge 15\%$ discount or net profit $\ge 1,500\text{ EUR}$.
* 📊 **`#MarketPrices`** (ID: Topic 6): Polish median price benchmark reference cards.
* 💬 **`#Community`** (ID: Topic 12): Open discussion for buyers and flippers.

### Dynamic Topics (Filter-Based):
When a user sets up a search filter, the bot calls Telegram's `createForumTopic`:
* **Format:** `🚗 [{Country Code}] {Make} {Model} (<{Budget} €)`
* **Example:** `🚗 [LV] Toyota Prius (<10k €)` or `🚙 [DE] BMW 520 (<15k €)`
* Listings matching the filter are delivered exclusively to that Topic ID (`message_thread_id`). When the user deletes the filter, the bot executes `closeForumTopic` and archives the filter in the database.

---

## 📂 5. Project Directory Structure

```
doogagauto/
├── config/
│   ├── __init__.py
│   └── settings.py              # Environment variables, country and logistics rates
├── database/
│   ├── __init__.py
│   ├── db.py                    # aiosqlite async connection and auto-migration
│   └── queries.py               # Filter, listing, and benchmark queries
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py          # Abstract Base Scraper class
│   ├── baltic/
│   │   ├── __init__.py
│   │   ├── ss_latvia.py         # SS.com
│   │   └── autoplius_lt.py      # Autoplius.lt
│   ├── central/
│   │   ├── __init__.py
│   │   ├── bazos_sk.py          # Bazos.sk
│   │   ├── bazos_cz.py          # Bazos.cz
│   │   └── sauto_cz.py          # Sauto.cz
│   ├── western/
│   │   ├── __init__.py
│   │   ├── mobile_de.py         # Mobile.de
│   │   ├── kleinanzeigen_de.py  # Kleinanzeigen.de
│   │   ├── leboncoin_fr.py      # Leboncoin.fr
│   │   └── subito_it.py         # Subito.it
│   └── poland_benchmarks/
│       ├── __init__.py
│       └── otomoto_pl.py        # Otomoto.pl median benchmark generator
├── bot/
│   ├── __init__.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── filter_fsm.py        # Aiogram 3 FSM (filter creation dashboard)
│   │   ├── management.py        # Settings, Hot Deals, topics management
│   │   └── admin.py             # Administrative controls & broadcast wizard
│   ├── locales/
│   │   ├── __init__.py
│   │   └── texts.py             # Multilingual localization dictionaries (EN, PL, RU)
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── i18n.py              # User language middleware
│   └── views/
│       ├── __init__.py
│       └── listing_card.py      # Telegram HTML rich listing cards & monetization
├── web/
│   ├── __init__.py
│   ├── app.py                  # FastAPI application factory
│   ├── auth.py                 # Admin session token authentication
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin.py             # Admin panel views & actions
│   │   ├── gateway.py           # Click redirect tracking & partner affiliate gateway
│   │   └── api.py               # JSON API endpoints
│   └── templates/               # Modern Glassmorphic UI templates
├── engine/
│   ├── __init__.py
│   ├── arbitrage.py             # Net margin, customs, and excise calculation
│   ├── broadcaster.py           # Background mass broadcast engine with jitter
│   └── scheduler.py             # Async cyclical scraping & notification scheduler
├── .env
├── requirements.txt
├── test_telegram_upgrade.py    # Specification test suite
├── test_web_admin.py           # Web admin & gateway test suite
├── test_system.py              # Full end-to-end scraper & arithmetic test
└── main.py                     # Entry point launching bot and web admin
```

---

## 🚀 6. Getting Started

```bash
# 1. Run test suite:
python test_system.py

# 2. Run Telegram upgrade tests:
python test_telegram_upgrade.py

# 3. Run Web Admin tests:
python test_web_admin.py

# 4. Launch bot & web server:
python main.py
```
