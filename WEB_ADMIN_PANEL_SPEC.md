# DOOGAGAUTO: VİZUAL VEB İDARƏETMƏ PANELİ VƏ MONETİZASİYA SİSTEMİ (SPECIFICATION)

## 1. MƏQSƏD VƏ İCMAL
Mövcud Telegram bot və avto-arbitraj skaner sistemimizə (`doogagauto`) brauzer üzərindən daxil oluna bilən (`/admin`), müasir qaranlıq interfeysli (Dark Theme), şifrə ilə qorunan **Veb İdarəetmə Paneli (Web Dashboard)** və **Klik İzləmə / Yönləndirmə Şlüzü** əlavə edilməlidir.

Bu panel sayəsində heç bir Python kodunu dəyişmədən:
1. İstifadəçi, aktiv mövzu, tapılan elan və kliklərin real vaxt statistikasını vizual qrafiklərlə (Chart.js) görmək.
2. Elan kartlarındakı sponsor mətnlərini, düymələrini və daxili redirect reklam linklərini tənzimləmək.
3. Telegram qrupunda açılmış bütün fərdi Topic-ləri cədvəl kimi izləmək, parametrlərini redaktə etmək, dayandırmaq və ya Telegram API ilə birbaşa bağlayıb arxivləşdirmək.
4. Bütün aktiv mövzulara və ya istifadəçilərə təsadüfi gecikmə (Anti-flood jitter) və canlı tərəqqi paneli (Live Progress Bar) ilə reklam yayımı göndərmək.
5. Arxivləşdirilmiş mövzuların və keçmiş reklam kampaniyalarının audit tarixçəsini saxlamaq.

---

## 2. TEXNOLOJİ STEK VƏ MEMARLIQ
- **Backend:** FastAPI (asinxron, yüksək performanslı)
- **Veb Server:** Uvicorn (mövcud `main.py` daxilində aiogram botu ilə eyni `asyncio` dövrəsində paralel işə düşür)
- **Şablonlaşdırma:** Jinja2 Şablonları (`web/templates/`)
- **UI / Dizayn:** TailwindCSS (CDN vasitəsilə, təmiz Dark/Modern Dashboard üslubu) + FontAwesome ikonları
- **Qrafiklər və Diaqramlar:** Chart.js (CDN)
- **Verilənlər Bazası:** Mövcud SQLite bazası (`data/car_arbitrage.db`) ilə `aiosqlite` üzərindən tam inteqrasiya

---

## 3. VERİLƏNLƏR BAZASI GENİŞLƏNMƏSİ (`database/`)
Mövcud bazaya bu yeni cədvəllər əlavə edilməlidir:

```sql
-- 1. Veb Panel Admin Hesabları və Təhlükəsizlik
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Reklam, Sponsor və Klik Şlüzü Ayarları
CREATE TABLE IF NOT EXISTS ad_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    is_redirect_enabled BOOLEAN DEFAULT 0,
    redirect_base_url TEXT DEFAULT '/r/',     -- Daxili yönləndirici prefiksi
    custom_affiliate_url TEXT DEFAULT '',     -- Tərəfdaş linki və ya hədəf şəbəkə
    sponsor_text TEXT DEFAULT '',              -- Elan kartının altındakı reklam mətni
    sponsor_button_name TEXT DEFAULT '',       -- Sponsor düyməsinin adı
    sponsor_button_url TEXT DEFAULT '',        -- Sponsor düyməsinin linki
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- İlkin tək sətri təmin et:
INSERT OR IGNORE INTO ad_settings (id, is_redirect_enabled, redirect_base_url, custom_affiliate_url, sponsor_text, sponsor_button_name, sponsor_button_url)
VALUES (1, 0, '/r/', '', '', '', '');

-- 3. Klik və Reklam Analitikası (Hər klik qeydiyyatı)
CREATE TABLE IF NOT EXISTS click_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT,                          -- Kliklənən maşının external_id-si
    source_topic_id INTEGER,                  -- Hansı Telegram mövzusundan kliklənib
    target_url TEXT NOT NULL,                 -- Əsl elan ünvanı
    ip_hash TEXT,                             -- Anonimləşdirilmiş istifadəçi IP izi
    user_agent TEXT,                          -- Cihaz məlumatı (Mobil/Desktop)
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Kütləvi Reklam Kampaniyaları və Canlı Yayım Tarixçəsi
CREATE TABLE IF NOT EXISTS broadcast_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message_text TEXT NOT NULL,
    image_url TEXT,
    button_name TEXT,
    button_url TEXT,
    target_type TEXT NOT NULL,                -- 'all_topics', 'active_topics', 'all_users'
    total_targets INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',            -- 'pending', 'running', 'completed', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 5. user_filters cədvəlinə status və qeyd sahələri
-- (Əgər cədvəldə yoxdursa: is_archived BOOLEAN DEFAULT 0, admin_notes TEXT)
```

---

## 4. VEB PANELDƏ AUTH VƏ TƏHLÜKƏSİZLİK
- `/admin/login`: İstifadəçi adı və şifrə ilə daxil olma.
- `/admin/logout`: Çıxış və sessiyanın sonlandırılması.
- Sessiya təhlükəsiz HTTP-only cookie ilə qorunur (`admin_session`).
- İlkin admin hesabı mövcud olmadıqda avtomatik yaradılır: istifadəçi adı `admin`, ilkin şifrə `admin123` (və ya `.env`-dən `WEB_ADMIN_PASSWORD`).
- Bütün `/admin/*` marşrutları daxil olmamış istifadəçiləri avtomatik olaraq `/admin/login` səhifəsinə yönləndirir.

---

## 5. DASHBOARD VƏ REAL VAXT ANALİTİKASI (`/admin/`)
- **KPI Kartları:**
  - 👥 Toplam İstifadəçilər
  - 🚘 Aktiv Mövzular / Filtrlər
  - 🔍 Skan Edilmiş Elanlar
  - 🖱️ Toplam Reklam Klikləri
  - 🔥 Hot Deals Sayı
  - 💰 Təxmini Arbitraj Dövriyyəsi
- **Chart.js Diaqramları:**
  - Son 7 günün klik dinamikası və elan axını (Line Chart)
  - Ölkələr üzrə filtr paylanması (Almaniya, Fransa, İtaliya, Baltik və s. - Doughnut Chart)
- **Son Fəaliyyətlər:** Son 5 klik və son yaradılan filtrlərin qısa xülasəsi.

---

## 6. MÖVZULARIN İDARƏ EDİLMƏSİ (`/admin/topics`)
- Telegram Forum Topic-lərinin cədvəli:
  - ID, İstifadəçi ID, Marka, Model, İl aralığı, Qiymət, Yürüş, Yanacaq, Ölkə, Topic ID, Status (Aktiv 🟢 / Pauzada ⏸ / Arxiv 🗄), Qeydlər.
- Əməliyyatlar:
  - **Statusu dəyişmək:** Pauza / Aktiv etmə.
  - **Parametrləri redaktə etmək:** Modal pəncərə ilə qiymət, il və qeydləri yeniləmək.
  - **Arxivləşdirmək / Bağlamaq:** Telegram API `close_forum_topic` vasitəsilə qrupdakı mövzunu bağlayır və bazada `is_archived = 1` qeyd edir.

---

## 7. MONETİZASİYA VƏ KLİK ŞLÜZÜ (`/admin/monetization` & `/r/{listing_id}`)
- **Veb Paneldən İdarəetmə:**
  - Redirect şlüzünü aktiv/deaktiv etmək.
  - Baza yönləndirici linki (`/r/` və ya xüsusi domen).
  - Tərəfdaş (Affiliate) şəbəkə linki şablonu.
  - Sponsor mətni, düymə adı və linki.
- **Klik Şlüzü (`/r/{listing_id}` və ya `/r/?target=...`):**
  - Klik gəldikdə anonimləşdirilmiş IP hash-i və User-Agent-i `click_analytics` cədvəlinə yazır.
  - İstifadəçini dərhal orijinal elan linkinə və ya affiliate linkinə 302 yönləndirir.

---

## 8. KÜTLƏVİ REKLAM YAYIMI PANELİ (`/admin/broadcast`)
- Veb interfeys üzərindən forma:
  - Kampaniya başlığı
  - Mesaj mətni (HTML dəstəyi ilə)
  - Şəkil URL-i (könüllü)
  - Düymə mətni və linki (könüllü)
  - Hədəf: Bütün mövzular, Aktiv mövzular, Bütün istifadəçilər (DM)
- Başladıldıqda:
  - Arxa fonda təsadüfi gecikməli (Anti-flood jitter 1.5 - 3.5s) asinxron yayım işə düşür.
  - Panel səhifəsində real vaxt canlı tərəqqi göstəricisi (Live Progress Bar) və statistikası (Göndərildi / Xəta) göstərilir.
  - Keçmiş kampaniyaların cədvəl tarixçəsi.

---

## 9. PARALEL ÇALIŞMA VƏ SERVER QURULMASI
- `main.py` daxilində FastAPI tətbiqi (`uvicorn.Server`) ilə Aiogram botu eyni `asyncio.gather` ilə paralel işləyir.
- Veb server portu `config/settings.py` daxilində `WEB_PORT` (defolt: `8000`) və `WEB_HOST` (defolt: `0.0.0.0`) kimi tənzimlənir.
