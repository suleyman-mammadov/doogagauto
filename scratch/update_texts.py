import re
from bot.locales.texts import OPTIONS_MAP, TEXTS

options_map_az = {
    'fuel': {
        'all': 'Hamısı', 'petrol': 'Benzin ⛽', 'diesel': 'Dizel 🛢️', 'hybrid': 'Hibrid ⚡', 'electric': 'Elektrik 🔌'
    },
    'transmission': {
        'all': 'Hamısı', 'automatic': 'Avtomat 🕹️', 'manual': 'Mexanika ⚙️'
    },
    'condition': {
        'all': 'Hamısı', 'undamaged': 'Zədəsiz ✅', 'damaged': 'Qəzalı ⚠️'
    },
    'body_type': {
        'all': 'Hamısı', 'sedan': 'Sedan 🚗', 'universal': 'Universal 🚙', 'hatchback': 'Hetçbek 🏎️', 'suv': 'SUV / Krossover 🚙', 'coupe': 'Kupe 🏎️'
    },
    'country': {
        'ALL': 'Bütün Şengen 🇪🇺', 'DE': 'Almaniya 🇩🇪', 'FR': 'Fransa 🇫🇷', 'IT': 'İtaliya 🇮🇹', 'LT': 'Litva 🇱🇹', 'LV': 'Latviya 🇱🇻', 'CZ': 'Çexiya 🇨🇿', 'SK': 'Slovakiya 🇸🇰'
    }
}

for cat, vals in options_map_az.items():
    for val, az_text in vals.items():
        if cat in OPTIONS_MAP and val in OPTIONS_MAP[cat]:
            OPTIONS_MAP[cat][val]['az'] = az_text

az_translations = {
    'btn_hot_deals_hub': '🔥 Hot Deals Skaneri',
    'select_language': '👋 <b>Xoş gəlmisiniz!</b> Zəhmət olmasa interfeys dilini seçin:\n\n👋 <b>Welcome!</b> Please select your preferred language:\n\n👋 <b>Witaj!</b> Proszę wybrać preferowany język interfejsu:\n\n👋 <b>Добро пожаловать!</b> Пожалуйста, выберите язык:',
    'language_saved': '✅ İnterfeys dili uğurla <b>Azərbaycan</b> dilinə dəyişdirildi!',
    'welcome_message': '🚀 <b>Schengen Car Arbitrage & Live Scanner Bot</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\nAvropanın (Almaniya, Fransa, İtaliya, Baltikyanı, Çexiya, Slovakiya) avtomobil bazarlarını canlı izləyən və Polşa (<b>Otomoto.pl</b>) bazar qiymətləri ilə müqayisə edərək xalis arbitraj qazancını hesablayan ağıllı sistem.\n\nAşağıdakı menyudan yeni axtarış başlada və ya mövcud filtrlərinizi idarə edə bilərsiniz.',
    'btn_new_search': '➕ Yeni Axtarış',
    'btn_my_topics': '📋 Filtrlərim',
    'btn_stats': '📊 Statistika',
    'btn_help': 'ℹ️ Kömək & Qaydalar',
    'btn_settings': '⚙️ Tənzimləmələr',
    'settings_title': '⚙️ <b>SİSTEM TƏNZİMLƏMƏLƏRİ</b>\n\n• Cari dil: <b>{current_lang}</b>\n• 🔔 Bildiriş yeri: <b>{notify_dest}</b>\n• 🔥 Hot Deals bildirişləri: <b>{hot_deals_status}</b>\n\nAşağıdakı düymələrlə tənzimləmələri dəyişə bilərsiniz:',
    'btn_hot_deals_on': '🔥 Hot Deals: Aktiv ✅',
    'btn_hot_deals_off': '🔥 Hot Deals: Deaktiv ❌',
    'hot_deals_enabled_alert': '✅ Hot Deals bildirişləri aktivləşdirildi!',
    'hot_deals_disabled_alert': '⏸️ Hot Deals bildirişləri dayandırıldı!',
    'status_active': 'Aktiv 🟢',
    'status_disabled': 'Deaktiv ❌',
    'btn_hot_deals_settings': '🔥 Hot Deals Tənzimləmələri',
    'hot_deals_dashboard_title': '🔥 <b>FƏRDİ HOT DEALS TƏNZİMLƏMƏLƏRİ</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Status:</b> {status}\n• <b>Min. Xalis Qazanc:</b> ≥ {min_profit} €\n• <b>Min. İl:</b> {min_year}\n• <b>Maks. Qiymət:</b> {max_price}\n• <b>Tezlik:</b> {interval}\n━━━━━━━━━━━━━━━━━━━━━\nDəyişmək üçün parametri seçin:',
    'interval_realtime': 'Canlı (Real-Time) ⚡',
    'interval_1h': 'Maks 1 ədəd / 1 saat',
    'interval_3h': 'Maks 1 ədəd / 3 saat',
    'interval_6h': 'Maks 1 ədəd / 6 saat',
    'interval_24h': 'Maks 1 ədəd / gün',
    'unlimited_price': 'Limitsiz ♾️',
    'any_year': 'İstənilən',
    'btn_back_to_settings': '🔙 Tənzimləmələr',
    'btn_back_to_hd': '🔙 Hot Deals Menyu',
    'choose_min_profit': '💰 <b>Minimum Xalis Qazancı Seçin:</b>\nElanlar yalnız təxmini qazanc bu məbləğdən yüksək olduqda göndəriləcək:',
    'choose_min_year': '📅 <b>Minimum İli Seçin:</b>\nYalnız bu ildən və daha təzə avtomobillər üçün Hot Deals alın:',
    'choose_max_price': '🏷️ <b>Maksimum Alış Qiymətini Seçin:</b>\nBu qiymətdən baha olan maşınlar göstərilməyəcək:',
    'choose_interval': '⏱️ <b>Bildiriş Tezliyini Seçin:</b>\nHot Deals bildirişlərini hansı tezliklə almaq istəyirsiniz?',
    'hd_param_updated': '✅ Parametr uğurla yeniləndi!',
    'prompt_make': '🚘 Zəhmət olmasa avtomobilin markasını daxil edin (Məs: <code>BMW</code>, <code>Toyota</code>, <code>Audi</code>):',
    'dashboard_header': '🛠 <b>AXTARIŞ PANELİ: {make}</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Model:</b> {model}\n• <b>İl:</b> {year}\n• <b>Yürüş:</b> {mileage}\n• <b>Qiymət:</b> {price}\n• <b>Yanacaq:</b> {fuel}\n• <b>Vəziyyət:</b> {condition}\n• <b>Sürətlər Qutusu:</b> {transmission}\n• <b>Ban:</b> {body_type}\n• <b>Bazar:</b> {country}\n━━━━━━━━━━━━━━━━━━━━━\nDəyişmək üçün parametri seçin:',
    'not_selected': '{Seçilməyib}',
    'btn_model': '🚘 Model',
    'btn_year': '📅 İl Aralığı',
    'btn_mileage': '🧭 Yürüş (km)',
    'btn_price': '💰 Qiymət (€)',
    'btn_fuel': '⛽ Yanacaq',
    'btn_condition': '🛠 Vəziyyət',
    'btn_transmission': '⚙️ Sürətlər Qutusu',
    'btn_body_type': '🏎 Ban Növü',
    'btn_country': '🌍 Hədəf Bazar',
    'btn_submit_topic': '🚀 Axtarışı Başlat',
    'btn_cancel': '❌ İmtina',
    'prompt_model_input': '🚘 Model daxil edin (məs: <code>X5</code>, <code>Prius</code>, <code>A6</code>) və ya sıfırlamaq üçün <code>-</code> yazın:',
    'prompt_year_input': '📅 İl aralığını daxil edin (məs: <code>2015 2022</code> və ya sadəcə min il <code>2015</code>):',
    'prompt_mileage_input': '🧭 Yürüşü km ilə daxil edin (məs: maks <code>180000</code> və ya aralıq <code>50000 150000</code>):',
    'prompt_price_input': '💰 Qiyməti EUR ilə daxil edin (məs: <code>4000 9000</code> və ya sadəcə maks <code>9000</code>):',
    'input_invalid_format': '⚠️ Format düzgün deyil. Yenidən cəhd edin və ya imtina edin.',
    'filter_cancelled': '❌ Axtarışın yaradılması ləğv edildi.',
    'topic_creating': '⏳ Axtarış aktivləşdirilir...',
    'topic_created_success': '✅ <b>Axtarışınız uğurla yaradıldı!</b>',
    'btn_go_to_topic': '🔗 Mövzuya Keç',
    'topic_creation_error': '⚠️ Mövzu yaradılarkən xəta baş verdi.',
    'pinned_summary_card': '📌 <b>AXTARIŞ PARAMETRLƏRİ</b>\n━━━━━━━━━━━━━━━━━━━━━\n<b>Marka:</b> {make}\n<b>Model:</b> {model}\n<b>İl:</b> {year}\n<b>Yürüş:</b> {mileage}\n<b>Qiymət:</b> {price}\n<b>Yanacaq:</b> {fuel}\n<b>Sürətlər Qutusu:</b> {transmission}\n<b>Vəziyyət:</b> {condition}\n<b>Ban:</b> {body_type}\n<b>Bazar:</b> {country}\n━━━━━━━━━━━━━━━━━━━━━\n⏳ <i>Skaner aktivdir. Uyğun elanlar dərhal bura çatdırılacaq.</i>',
    'my_topics_title': '📋 <b>AXTARIŞ FİLTRLƏRİNİZ:</b>',
    'no_topics_found': 'ℹ️ Hələ heç bir axtarış filtriniz yoxdur.\nYeni filtr yaratmaq üçün /newfilter əmrindən istifadə edin.',
    'status_paused': 'Dayandırılıb ⏸',
    'btn_pause': '⏸ Dayandır',
    'btn_resume': '▶️ Başlat',
    'btn_delete_topic': '🗑 Sil',
    'confirm_delete_prompt': '⚠️ Bu filtri silmək istədiyinizdən əminsiniz?',
    'btn_confirm_yes': '✅ Bəli, Sil',
    'btn_confirm_no': '❌ Xeyr',
    'topic_deleted_success': '🗑 Filtr uğurla silindi.',
    'stats_template': '📊 <b>SİSTEM STATİSTİKASI</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 Qeydiyyatlı İstifadəçilər: <b>{total_users}</b>\n🚘 Aktiv Filtrlər: <b>{active_filters}</b>\n📁 Cəmi Axtarışlar: <b>{total_topics}</b>\n🔍 Skan Olunmuş Elanlar: <b>{seen_listings}</b>\n🇵🇱 Otomoto Bazar Qiymətləri: <b>{cached_benchmarks}</b>',
    'submenu_fuel': '⛽ <b>Yanacaq Növünü Seçin:</b>\nAşağıdakı siyahıdan mühərrik növünü seçin:',
    'submenu_country': '🌍 <b>Hədəf Bazarı Seçin:</b>\nMonitorinq etmək istədiyiniz bazarı seçin:',
    'submenu_transmission': '⚙️ <b>Sürətlər Qutusunu Seçin:</b>\nÖtürücü qutusunun tipini seçin:',
    'submenu_condition': '🛠 <b>Nəqliyyat Vasitəsinin Vəziyyətini Seçin:</b>\nQəza və texniki vəziyyətə görə filtrləyin:',
    'submenu_body_type': '🏎 <b>Ban Növünü Seçin:</b>\nAvtomobilin gövdə növünü seçin:',
    'submenu_mileage': '🧭 <b>Maksimum Yürüşü Seçin:</b>\nQəbul edilən maksimum kilometrajı təyin edin:',
    'step_year_min_title': '📅 <b>Addım 1/2: Minimum İli Seçin</b>\nƏn qədim buraxılış ilini seçin:',
    'step_year_max_title': '📅 <b>Addım 2/2: Maksimum İli Seçin</b> (Min: {min_year})\nƏn yeni buraxılış ilini seçin:',
    'step_price_min_title': '💰 <b>Addım 1/2: Minimum Qiyməti Seçin (€)</b>\nMinimum alış büdcəsini təyin edin:',
    'step_price_max_title': '💰 <b>Addım 2/2: Maksimum Qiyməti Seçin (€)</b> (Min: {min_price})\nMaksimum alış büdcəsini təyin edin:',
    'btn_any_min': 'İstənilən (Limitsiz)',
    'btn_any_max': 'İstənilən (∞)',
    'select_make_title': '🚘 <b>Avtomobil Markasını Seçin:</b>\nPopulyar markalardan birini seçin və ya özünüz daxil edin:',
    'select_model_title': '🚘 <b>Model Seçin ({make}):</b>\nPopulyar modellərdən birini seçin və ya bütün modelləri saxlayın:',
    'btn_other_make': '✍️ Digər Marka (Yaz)',
    'btn_all_models': 'Bütün Modellər (İstənilən)',
    'btn_custom_model': '✍️ Xüsusi Model (Yaz)',
    'btn_back_to_dashboard': '🔙 Axtarış Panelinə Qayıt',
    'btn_notify_dest_dm': '🔔 Bildiriş Yeri: Şəxsi Çat 🟢',
    'btn_notify_dest_group': '🔔 Bildiriş Yeri: Şəxsi Qrup 👥',
    'btn_switch_to_group': '👥 Qrupa Keçir (Pro)',
    'btn_switch_to_dm': '🟢 Şəxsi Çata Keçir',
    'btn_connect_group': '👥 Şəxsi Qrupu Qoş (Topics)',
    'btn_disconnect_group': '🔄 Qrupu Dəyiş / Ayır'
}

for k, v in az_translations.items():
    if k not in TEXTS:
        TEXTS[k] = {'az': v, 'en': v, 'pl': v, 'ru': v}
    else:
        TEXTS[k]['az'] = v

out = f'''"""Centralized multilingual localization dictionaries for 4 languages (AZ, EN, PL, RU)."""
from typing import Dict, Any, Optional

LANGUAGES = {{'az': '🇦🇿 Azərbaycan', 'en': '🇬🇧 English', 'pl': '🇵🇱 Polski', 'ru': '🇷🇺 Русский'}}

TOGGLE_OPTIONS = {{'fuel': ['all', 'petrol', 'diesel', 'hybrid', 'electric'], 'transmission': ['all', 'automatic', 'manual'], 'condition': ['all', 'undamaged', 'damaged'], 'body_type': ['all', 'sedan', 'universal', 'hatchback', 'suv', 'coupe'], 'country': ['ALL', 'DE', 'FR', 'IT', 'LT', 'LV', 'CZ', 'SK']}}

OPTIONS_MAP: Dict[str, Dict[str, Dict[str, str]]] = {repr(OPTIONS_MAP)}

TEXTS: Dict[str, Dict[str, str]] = {repr(TEXTS)}

_CUSTOM_BUTTON_LABELS: Dict[str, Dict[str, str]] = {{}}

def set_custom_button_labels(labels: Dict[str, Dict[str, str]]):
    global _CUSTOM_BUTTON_LABELS
    _CUSTOM_BUTTON_LABELS = dict(labels)

def get_custom_button_label(key: str, lang: str = 'en') -> Optional[str]:
    sub = _CUSTOM_BUTTON_LABELS.get(key)
    if sub:
        return sub.get(lang) or sub.get('az') or sub.get('en')
    return None

def t(key: str, lang: str = 'en', **kwargs) -> str:
    normalized_lang = (lang or 'en').lower()
    if normalized_lang not in LANGUAGES:
        normalized_lang = 'en'
    custom = get_custom_button_label(key, normalized_lang)
    if custom and custom.strip():
        if kwargs:
            try:
                return custom.format(**kwargs)
            except Exception:
                return custom
        return custom
    sub_dict = TEXTS.get(key)
    if not sub_dict:
        return key
    text_template = sub_dict.get(normalized_lang) or sub_dict.get('az') or sub_dict.get('en') or key
    if kwargs:
        try:
            return text_template.format(**kwargs)
        except Exception:
            return text_template
    return text_template

def get_text(key: str, lang: str = 'en', **kwargs) -> str:
    return t(key, lang, **kwargs)

def get_option_label(category: str, value: str, lang: str = 'en') -> str:
    normalized_lang = (lang or 'en').lower()
    cat = OPTIONS_MAP.get(category, {{}})
    val_map = cat.get(str(value).lower()) or cat.get(str(value).upper())
    if val_map:
        return val_map.get(normalized_lang) or val_map.get('az') or val_map.get('en') or str(value)
    return str(value)
'''

with open('bot/locales/texts.py', 'w', encoding='utf-8') as f:
    f.write(out)
print('SUCCESSFULLY UPDATED bot/locales/texts.py with Azerbaijani (AZ) translations!')
