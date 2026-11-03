---

# 🚗 DoogagAuto Bot: Access and Testing Guide

Want to test our real-time Schengen car arbitrage scanner? Follow these simple steps to find and launch the bot on Telegram

1. **Open Telegram:** Launch the Telegram app on your mobile device or desktop.
2. **Search for the Bot:** Type `@doogagauto_bot` into the global search bar (or use the direct link provided by the administrator).
3. **Initialize the Bot:** Open the chat window and click the **Start** button (or type `/start`) to activate the system.
4. **Set Up Your First Filter:** Use the interactive menu or the `/newfilter` command to choose your preferred car make, model, year range, budget, and target Schengen countries.
5. **Get Live Alerts:** Watch as the system matches foreign listings and delivers high-margin deals and *Hot Deals* directly to your chat or group topics! 🚀

---

# 🛠️ DoogagAuto Engine: High-Performance Pan-European Arbitrage & Anti-Bot Architecture

**Enterprise-grade, asynchronous Schengen car arbitrage, web scraper, and real-time notification platform.**

The system continuously monitors automotive portals across 7+ European countries, detects local price anomalies, calculates customs, excise, and logistics expenses, and delivers them to users via Telegram Supergroup Topics / Web Gateway.

---

## 🏗️ 1. System Architecture & Server Infrastructure

* ☁️ **Hosting & Server:** **Microsoft Azure Cloud (Azure Virtual Machine / Ubuntu Server 22.04/24.04 LTS)**.
* ⚡ **Execution Model:** 24/7 continuous asynchronous execution via `systemd` services or Docker containers.
* 🔄 **Event Loop:** Python `asyncio` single-core asynchronous architecture — Telegram Bot (`aiogram 3`), Background Scraper (`APScheduler`), and Web Admin Panel (`FastAPI` + `Uvicorn`) run concurrently in the same event loop without blocking.


-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## 🏗️ Detailed System Architecture & Azure Infrastructure

The following diagram illustrates the complete end-to-end architecture of the Pan-European Car Arbitrage and Live Scanner system running 24/7 on **Microsoft Azure Cloud**.

```mermaid
graph TD
    subgraph Azure ["Microsoft Azure VM (Ubuntu Server)"]
        
        subgraph Web ["Web & Admin Panel"]
            FastAPI["FastAPI Application"]
            Gateway["Click Redirect Gateway"]
        end

        subgraph Bot ["Telegram Bot Layer"]
            Aiogram["Aiogram 3 Bot Core"]
            FSM["FSM Filter Manager"]
            Topics["Forum Topics Automator"]
        end

        subgraph Engine ["Core Engine"]
            Scheduler["APScheduler"]
            Arbitrage["Arbitrage Calculator"]
        end

        subgraph Scrapers ["Pan-European Scrapers & Anti-Bot"]
            ProxyPool["Intelligent Proxy Pool"]
            Tier1["Tier 1: SS.com, Bazos.sk, Bazos.cz"]
            Tier2["Tier 2: Autoplius.lt, Sauto.cz"]
            Tier3["Tier 3: Mobile.de, Kleinanzeigen, Leboncoin, Subito"]
            Otomoto["Otomoto.pl Benchmark"]
        end

        Database[("aiosqlite Database (WAL Mode)")]
    end

    External["External Schengen Classifieds"] --> ProxyPool
    ProxyPool --> Tier1
    ProxyPool --> Tier2
    ProxyPool --> Tier3
    ProxyPool --> Otomoto
    
    Scheduler --> Scrapers
    Tier1 --> Arbitrage
    Tier2 --> Arbitrage
    Tier3 --> Arbitrage
    Otomoto --> Arbitrage
    
    Arbitrage --> Database
    FastAPI --> Database
    Aiogram --> Database
    FSM --> Topics
    
    Arbitrage --> Aiogram
    Aiogram --> TelegramGroup["Telegram Supergroup (Forum Topics)"]
    FastAPI --> AdminPanel["Admin Browser (Dashboard & Proxies)"]
    Gateway --> UserClicks["Affiliate & Sponsor Redirects"]
```

## 
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 🧰 2. Technology Stack & Libraries

| Category | Technology / Library | Purpose |
| :--- | :--- | :--- |
| **Core Language** | Python 3.11 / 3.12+ | Core system engine and asynchronous orchestration |
| **Web & Templates** | HTML5, TailwindCSS, Jinja2, Chart.js | Modern dark-themed Admin Panel and analytics charts |
| **Bot Framework** | `aiogram >= 3.15.0` | Telegram Bot API 7.0+ (Forum Topics, FSM, Middleware support) |
| **HTTP & Anti-Bot** | `curl_cffi >= 0.7.0` | TLS/JA3/HTTP2 Chrome 120 impersonation (Cloudflare/DataDome bypass) |
| **HTML Parser** | `selectolax >= 1.0.0` | Ultra-fast Lexbor HTML parsing engine written in C |
| **Database** | `aiosqlite >= 0.20.0` | Asynchronous SQLite with PRAGMA WAL high-performance read/write |
| **Web Framework** | `fastapi >= 0.110.0`, `uvicorn` | Admin panel, JSON API, click tracking, and affiliate redirect gateway |
| **Scheduler** | `apscheduler >= 3.10.0` | Multi-platform scraper and periodic maintenance jobs |
| **Settings** | `pydantic-settings >= 2.2.0` | Robust type validation and `.env` configuration management |

---

## 🛡️ 3. Anti-Bot Strategy & Scraper Tiers

European automotive platforms have varying security barriers. The system operates on a 3-tier architecture:

* 🟢 **Tier 1 (Minimal Protection):** `SS.com` (Latvia), `Bazos.sk` (Slovakia), `Bazos.cz` (Czechia).
  - Simple HTTP requests and `selectolax.lexbor` processing with a 60–90 second interval.
* 🟡 **Tier 2 (Moderate Protection):** `Autoplius.lt` (Lithuania), `Sauto.cz` (Czechia).
  - Cookie, User-Agent, and HTTP/2 header synchronization.
* 🔴 **Tier 3 (Aggressive Protection):** `Mobile.de`, `Kleinanzeigen.de` (Germany), `Leboncoin.fr` (France), `Subito.it` (Italy), `Otomoto.pl` (Poland).
  - **Protection:** Cloudflare Turnstile, DataDome, Akamai Bot Manager.
  - **Solution:** `curl_cffi` is used instead of standard `requests` or `httpx`. TLS Fingerprints (JA3/JA4) and HTTP/2 frame sequences are simulated to mimic a real Google Chrome 120 browser.
* ⚡ **Delta-Scanning:** Fetches only the top 10–25 newly posted listings (`sort=created_desc`) rather than full site crawling.
* 🧹 **Deduplication:** Every listing is checked against a unique `(platform, external_id)` key in SQLite to prevent duplicate processing.

---

## 🌐 4. Intelligent Proxy Pool Architecture

The system utilizes a dynamic proxy management infrastructure to prevent IP bans:
* **Pool Size:** Supports 100 – 1000+ active HTTP/HTTPS/SOCKS5 proxies.
* **Rotation Strategies:**
  1. `round_robin` — Equal sequential distribution.
  2. `random` — Random selection to obscure tracking patterns.
* **Application Modes:**
  - `protected_only` — Proxies are used exclusively on Tier-3 platforms (Cloudflare/DataDome protected like Mobile.de, Leboncoin, etc.), preserving resources on Tier-1 sites.
  - `all` — All requests are fully anonymized.
* **Healthcheck & Latency Monitor:**
  - The web panel and background workers test latency (ms), success/fail counts for each proxy, automatically dropping faulty ones from circulation.

---

## 💰 5. Pricing & Arbitrage Calculation Algorithm

When a foreign listing is discovered, it is compared against the Polish market median (**Otomoto.pl**):

$$\text{Net Profit} = \text{Otomoto Median Price (EUR)} - \text{Total Landed Cost}$$

Where:
$$\text{Landed Cost} = \text{Purchase Price} + \text{Logistics} + \text{Excise Tax (Akcyza)} + \text{Registration}$$

### 🚚 1. Dynamic Logistics Costs:
- 🇱🇻 🇱🇹 🇪🇪 Baltics: **€400**
- 🇨🇿 🇸🇰 Czechia / Slovakia: **€300**
- 🇩🇪 Germany: **€500**
- 🇫🇷 🇮🇹 🇪🇸 🇳🇱 France, Italy, Spain, Netherlands: **€850**
- 🌐 Other: **€500**

### 📑 2. Polish Excise Tax (Akcyza) Engine:
The engine analyzes text and fuel types using Regex rules:
* 🔌 **Full Electric (EV):** **0%**
* ⚡ **Hybrid ($\le 2.0\text{L}$):** **1.55%**
* ⚡ **Hybrid ($> 2.0\text{L}$):** **9.3%**
* ⛽ **Standard ICE ($\le 2.0\text{L}$):** **3.1%**
* ⛽ **High-Capacity ICE ($> 2.0\text{L}$):** **18.6%**
* 📝 **Polish technical inspection and state registration:** **~300 PLN (~€70)**

> 🔥 **Hot Deals Algorithm:** If $\text{Net Profit} \ge €1,500$ or the purchase price is $\ge 15\%$ below the market median, the listing is instantly forwarded to the dedicated **#HotDeals** stream!

---

## 🏛️ 6. Telegram Supergroup Forum Architecture

The system is fully integrated with Telegram's **Forum Topics** technology:
* ⚙️ `#Settings` (Topic ID: 2): Bot settings and filter creation panel.
* 🔥 `#HotDeals` (Topic ID: 4): High-margin anomaly deals across Pan-Europe.
* 📊 `#MarketPrices` (Topic ID: 6): Polish median price benchmark references.
* 💬 `#Community` (Topic ID: 12): Member discussion lounge.
* 🚗 **Dynamic Filters:** When a user sets up a filter, the bot automatically creates a new forum topic via Telegram API:
  - Format: `🚗 [{Country}] {Make} {Model} (<{Budget} €)`
  - Example: `🚗 [DE] BMW 520 (<15k €)`
  - When the filter is deleted, the topic is archived and closed (`closeForumTopic`).

---

## 💻 7. Web Admin Panel & Monetization Gateway

Browser-based management center (`http://<azure-ip>:port/subfolder`):
1. **Dashboard:** Active users, live listing streams, clicks, and earnings charts (Chart.js).
2. **Monetization & Sponsor:** Ability to append sponsor text, partner call-to-action buttons, and internal redirect links (`/r/{listing_id}`) to listing cards.
3. **Broadcaster:** Anti-Flood algorithm with randomized jitters to safely broadcast notifications to all topics or users.
4. **Proxy Management:** One-click bulk upload of proxy lists via TXT files and live testing.






