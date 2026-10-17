"""Centralized multilingual localization dictionaries for 3 languages (EN, PL, RU)."""
from typing import Dict, Any, Optional

LANGUAGES = {
    'en': '🇬🇧 English',
    'pl': '🇵🇱 Polski',
    'ru': '🇷🇺 Русский'
}

TOGGLE_OPTIONS = {
    'fuel': ['all', 'petrol', 'diesel', 'hybrid', 'electric'],
    'transmission': ['all', 'automatic', 'manual'],
    'condition': ['all', 'undamaged', 'damaged'],
    'body_type': ['all', 'sedan', 'universal', 'hatchback', 'suv', 'coupe'],
    'country': ['ALL', 'DE', 'FR', 'IT', 'LT', 'LV', 'CZ', 'SK']
}

OPTIONS_MAP: Dict[str, Dict[str, Dict[str, str]]] = {
    'fuel': {
        'all': {'en': 'All', 'pl': 'Wszystkie', 'ru': 'Все'},
        'petrol': {'en': 'Petrol ⛽', 'pl': 'Benzyna ⛽', 'ru': 'Бензин ⛽'},
        'diesel': {'en': 'Diesel 🛢️', 'pl': 'Diesel 🛢️', 'ru': 'Дизель 🛢️'},
        'hybrid': {'en': 'Hybrid ⚡', 'pl': 'Hybryda ⚡', 'ru': 'Гибрид ⚡'},
        'electric': {'en': 'Electric 🔌', 'pl': 'Elektryczny 🔌', 'ru': 'Электро 🔌'}
    },
    'transmission': {
        'all': {'en': 'All', 'pl': 'Wszystkie', 'ru': 'Все'},
        'automatic': {'en': 'Automatic 🕹️', 'pl': 'Automat 🕹️', 'ru': 'Автомат 🕹️'},
        'manual': {'en': 'Manual ⚙️', 'pl': 'Manualna ⚙️', 'ru': 'Механика ⚙️'}
    },
    'condition': {
        'all': {'en': 'All', 'pl': 'Wszystkie', 'ru': 'Все'},
        'undamaged': {'en': 'Undamaged only ✅', 'pl': 'Bezwypadkowe ✅', 'ru': 'Без ДТП ✅'},
        'damaged': {'en': 'Damaged ⚠️', 'pl': 'Uszkodzone ⚠️', 'ru': 'Поврежденные ⚠️'}
    },
    'body_type': {
        'all': {'en': 'All', 'pl': 'Wszystkie', 'ru': 'Все'},
        'sedan': {'en': 'Sedan 🚗', 'pl': 'Sedan 🚗', 'ru': 'Седан 🚗'},
        'universal': {'en': 'Universal/Estate 🚙', 'pl': 'Kombi 🚙', 'ru': 'Универсал 🚙'},
        'hatchback': {'en': 'Hatchback 🏎️', 'pl': 'Hatchback 🏎️', 'ru': 'Хэтчбек 🏎️'},
        'suv': {'en': 'SUV / Crossover 🚙', 'pl': 'SUV / Crossover 🚙', 'ru': 'Внедорожник/SUV 🚙'},
        'coupe': {'en': 'Coupe 🏎️', 'pl': 'Coupe 🏎️', 'ru': 'Купе 🏎️'}
    },
    'country': {
        'ALL': {'en': 'All Schengen 🇪🇺', 'pl': 'Cały Schengen 🇪🇺', 'ru': 'Весь Шенген 🇪🇺'},
        'DE': {'en': 'Germany 🇩🇪', 'pl': 'Niemcy 🇩🇪', 'ru': 'Германия 🇩🇪'},
        'FR': {'en': 'France 🇫🇷', 'pl': 'Francja 🇫🇷', 'ru': 'Франция 🇫🇷'},
        'IT': {'en': 'Italy 🇮🇹', 'pl': 'Włochy 🇮🇹', 'ru': 'Италия 🇮🇹'},
        'LT': {'en': 'Lithuania 🇱🇹', 'pl': 'Litwa 🇱🇹', 'ru': 'Литва 🇱🇹'},
        'LV': {'en': 'Latvia 🇱🇻', 'pl': 'Łotwa 🇱🇻', 'ru': 'Латвия 🇱🇻'},
        'CZ': {'en': 'Czechia 🇨🇿', 'pl': 'Czechy 🇨🇿', 'ru': 'Чехия 🇨🇿'},
        'SK': {'en': 'Slovakia 🇸🇰', 'pl': 'Słowacja 🇸🇰', 'ru': 'Словакия 🇸🇰'}
    }
}

TEXTS: Dict[str, Dict[str, str]] = {
    'btn_hot_deals_hub': {
        'en': '🔥 Hot Deals Scanner',
        'pl': '🔥 Skaner Hot Deals',
        'ru': '🔥 Сканер Hot Deals'
    },
    'select_language': {
        'en': '👋 <b>Welcome!</b> Please select your preferred language:\n\n👋 <b>Witaj!</b> Proszę wybrać preferowany język interfejsu:\n\n👋 <b>Добро пожаловать!</b> Пожалуйста, выберите язык:',
        'pl': '👋 Proszę wybrać język interfejsu:',
        'ru': '👋 Пожалуйста, выберите язык интерфейса:'
    },
    'language_saved': {
        'en': '✅ Language successfully set to <b>English</b>!',
        'pl': '✅ Język został pomyślnie zmieniony na <b>Polski</b>!',
        'ru': '✅ Язык успешно установлен на <b>Русский</b>!'
    },
    'welcome_message': {
        'en': '🚀 <b>Schengen Car Arbitrage & Live Scanner Bot</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\nSmart live scanner monitoring top European automotive markets (Germany, France, Italy, Baltics, Central Europe) and calculating net arbitrage profits compared against <b>Otomoto.pl</b> benchmark prices.\n\nUse the menu below to launch a new search or manage your active topics.',
        'pl': '🚀 <b>Schengen Car Arbitrage & Live Scanner Bot</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\nInteligentny skaner monitorujący rynki samochodowe w Europie (Niemcy, Francja, Włochy, Kraje Bałtyckie, Czechy, Słowacja) i obliczający zysk arbitrażowy w porównaniu z medianą cen na <b>Otomoto.pl</b>.\n\nWybierz opcję z menu poniżej, aby utworzyć nowe wyszukiwanie lub zarządzać tematami.',
        'ru': '🚀 <b>Schengen Car Arbitrage & Live Scanner Bot</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\nИнтеллектуальный сканер, отслеживающий авторынки Шенгена (Германия, Франция, Италия, Прибалтика, Чехия, Словакия) и рассчитывающий чистую арбитражную прибыль по сравнению с рыночными ценами <b>Otomoto.pl</b>.\n\nИспользуйте меню ниже для создания поиска или управления темами.'
    },
    'btn_new_search': {
        'en': '➕ New Search',
        'pl': '➕ Nowe Wyszukiwanie',
        'ru': '➕ Новый Поиск'
    },
    'btn_my_topics': {
        'en': '📋 My Filters',
        'pl': '📋 Moje Filtry',
        'ru': '📋 Мои Фильтры'
    },
    'btn_stats': {
        'en': '📊 Statistics',
        'pl': '📊 Statystyki',
        'ru': '📊 Статистика'
    },
    'btn_help': {
        'en': 'ℹ️ Help & Guide',
        'pl': 'ℹ️ Pomoc i Zasady',
        'ru': 'ℹ️ Помощь и Инфо'
    },
    'btn_settings': {
        'en': '⚙️ Settings',
        'pl': '⚙️ Ustawienia',
        'ru': '⚙️ Настройки'
    },
    'btn_main_menu': {
        'en': '🏠 Main Menu',
        'pl': '🏠 Menu Główne',
        'ru': '🏠 Главное Меню'
    },
    'settings_title': {
        'en': '⚙️ <b>SYSTEM SETTINGS</b>\n\n• Current language: <b>{current_lang}</b>\n• 🔔 Notification target: <b>{notify_dest}</b>\n• 🔥 Hot Deals alerts: <b>{hot_deals_status}</b>\n\nUse buttons below to adjust language or notifications:',
        'pl': '⚙️ <b>USTAWIENIA SYSTEMOWE</b>\n\n• Obecny język: <b>{current_lang}</b>\n• 🔔 Cel powiadomień: <b>{notify_dest}</b>\n• 🔥 Powiadomienia Hot Deals: <b>{hot_deals_status}</b>\n\nUżyj poniższych przycisków, aby zmienić język lub powiadomienia:',
        'ru': '⚙️ <b>НАСТРОЙКИ СИСТЕМЫ</b>\n\n• Текущий язык: <b>{current_lang}</b>\n• 🔔 Место отправки: <b>{notify_dest}</b>\n• 🔥 Уведомления Hot Deals: <b>{hot_deals_status}</b>\n\nИспользуйте кнопки ниже для настройки языка или уведомлений:'
    },
    'btn_hot_deals_on': {
        'en': '🔥 Hot Deals: Active ✅',
        'pl': '🔥 Hot Deals: Aktywne ✅',
        'ru': '🔥 Hot Deals: Включено ✅'
    },
    'btn_hot_deals_off': {
        'en': '🔥 Hot Deals: Disabled ❌',
        'pl': '🔥 Hot Deals: Wyłączone ❌',
        'ru': '🔥 Hot Deals: Выключено ❌'
    },
    'hot_deals_enabled_alert': {
        'en': '✅ Hot Deals notifications activated!',
        'pl': '✅ Powiadomienia Hot Deals włączone!',
        'ru': '✅ Уведомления Hot Deals активированы!'
    },
    'hot_deals_disabled_alert': {
        'en': '⏸️ Hot Deals notifications paused!',
        'pl': '⏸️ Powiadomienia Hot Deals wyłączone!',
        'ru': '⏸️ Уведомления Hot Deals приостановлены!'
    },
    'status_active': {
        'en': 'Active 🟢',
        'pl': 'Aktywny 🟢',
        'ru': 'Активен 🟢'
    },
    'status_disabled': {
        'en': 'Disabled ❌',
        'pl': 'Wyłączone ❌',
        'ru': 'Выключено ❌'
    },
    'status_paused': {
        'en': 'Paused ⏸️',
        'pl': 'Wstrzymany ⏸️',
        'ru': 'На паузе ⏸️'
    },
    'btn_hot_deals_settings': {
        'en': '🔥 Hot Deals Preferences',
        'pl': '🔥 Preferencje Hot Deals',
        'ru': '🔥 Настройки Hot Deals'
    },
    'hot_deals_dashboard_title': {
        'en': '🔥 <b>HOT DEALS PREFERENCES</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Status:</b> {status}\n• <b>Min. Net Profit:</b> ≥ {min_profit} €\n• <b>Min. Margin:</b> ≥ {min_pct}\n• <b>Focus:</b> {deal_type}\n• <b>Min. Year:</b> {min_year}\n• <b>Max. Price:</b> {max_price}\n• <b>Max. Mileage:</b> {max_mileage}\n• <b>Alert Frequency:</b> {interval}\n━━━━━━━━━━━━━━━━━━━━━\nSelect a parameter to adjust:',
        'pl': '🔥 <b>PREFERENCJE HOT DEALS</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Status:</b> {status}\n• <b>Min. Zysk Netto:</b> ≥ {min_profit} €\n• <b>Min. Marża:</b> ≥ {min_pct}\n• <b>Kategoria:</b> {deal_type}\n• <b>Min. Rok:</b> {min_year}\n• <b>Maks. Cena:</b> {max_price}\n• <b>Maks. Przebieg:</b> {max_mileage}\n• <b>Częstotliwość:</b> {interval}\n━━━━━━━━━━━━━━━━━━━━━\nWybierz parametr do zmiany:',
        'ru': '🔥 <b>НАСТРОЙКИ HOT DEALS</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Статус:</b> {status}\n• <b>Мин. Чистая Прибыль:</b> ≥ {min_profit} €\n• <b>Мин. Маржа:</b> ≥ {min_pct}\n• <b>Категория:</b> {deal_type}\n• <b>Мин. Год:</b> {min_year}\n• <b>Макс. Цена:</b> {max_price}\n• <b>Макс. Пробег:</b> {max_mileage}\n• <b>Частота:</b> {interval}\n━━━━━━━━━━━━━━━━━━━━━\nВыберите параметр для изменения:'
    },
    'btn_hd_profit': {
        'en': '💰 Min Profit: {v}',
        'pl': '💰 Min Zysk: {v}',
        'ru': '💰 Мин Прибыль: {v}'
    },
    'btn_hd_pct': {
        'en': '📈 Min Margin: {v}',
        'pl': '📈 Min Marża: {v}',
        'ru': '📈 Мин Маржа: {v}'
    },
    'btn_hd_focus': {
        'en': '🎯 Focus: {v}',
        'pl': '🎯 Kategoria: {v}',
        'ru': '🎯 Фокус: {v}'
    },
    'btn_hd_year': {
        'en': '📅 Year: {v}',
        'pl': '📅 Rok: {v}',
        'ru': '📅 Год: {v}'
    },
    'btn_hd_price': {
        'en': '🏷️ Price: {v}',
        'pl': '🏷️ Cena: {v}',
        'ru': '🏷️ Цена: {v}'
    },
    'btn_hd_mileage': {
        'en': '🧭 Max Mileage: {v}',
        'pl': '🧭 Maks Przebieg: {v}',
        'ru': '🧭 Макс Пробег: {v}'
    },
    'btn_hd_interval': {
        'en': '⏱️ Alert: {v}',
        'pl': '⏱️ Powiadomienie: {v}',
        'ru': '⏱️ Уведомление: {v}'
    },
    'interval_realtime': {
        'en': 'Real-Time ⚡',
        'pl': 'Na żywo ⚡',
        'ru': 'В реальном времени ⚡'
    },
    'interval_1h': {
        'en': 'Max 1 per 1h',
        'pl': 'Maks 1 na 1h',
        'ru': 'Макс 1 в час'
    },
    'interval_3h': {
        'en': 'Max 1 per 3h',
        'pl': 'Maks 1 na 3h',
        'ru': 'Макс 1 в 3 часа'
    },
    'interval_6h': {
        'en': 'Max 1 per 6h',
        'pl': 'Maks 1 na 6h',
        'ru': 'Макс 1 в 6 часов'
    },
    'interval_24h': {
        'en': 'Max 1 per day',
        'pl': 'Maks 1 dziennie',
        'ru': 'Макс 1 в день'
    },
    'unlimited_price': {
        'en': 'Unlimited ♾️',
        'pl': 'Bez limitu ♾️',
        'ru': 'Без лимита ♾️'
    },
    'any_year': {
        'en': 'Any Year',
        'pl': 'Dowolny',
        'ru': 'Любой'
    },
    'btn_back_to_settings': {
        'en': '🔙 Settings',
        'pl': '🔙 Ustawienia',
        'ru': '🔙 Настройки'
    },
    'btn_back_to_hd': {
        'en': '🔙 Hot Deals Menu',
        'pl': '🔙 Menu Hot Deals',
        'ru': '🔙 Меню Hot Deals'
    },
    'choose_min_profit': {
        'en': '💰 <b>Select Minimum Net Profit:</b>\nListings will be delivered only if estimated net profit is at least this amount:',
        'pl': '💰 <b>Wybierz Minimalny Zysk Netto:</b>\nOferty będą wysyłane tylko wtedy, gdy szacowany zysk wyniesie co najmniej tę kwotę:',
        'ru': '💰 <b>Выберите Минимальную Чистую Прибыль:</b>\nОбъявления будут приходить только если расчетная прибыль не меньше указанной суммы:'
    },
    'choose_min_year': {
        'en': '📅 <b>Select Minimum Year:</b>\nOnly receive Hot Deals for cars manufactured in this year or newer:',
        'pl': '📅 <b>Wybierz Minimalny Rok Produkcji:</b>\nOtrzymuj oferty tylko dla aut wyprodukowanych w tym roku lub nowszych:',
        'ru': '📅 <b>Выберите Минимальный Год Выпуска:</b>\nПолучать сделки только по автомобилям этого года или новее:'
    },
    'choose_max_price': {
        'en': '🏷️ <b>Select Maximum Price:</b>\nCars more expensive than this price will be filtered out:',
        'pl': '🏷️ <b>Wybierz Maksymalną Cenę Zakupu:</b>\nSamochody droższe niż ta kwota zostaną odfiltrowane:',
        'ru': '🏷️ <b>Выберите Максимальную Цену Покупки:</b>\nАвтомобили дороже этой суммы будут отфильтрованы:'
    },
    'choose_interval': {
        'en': '⏱️ <b>Select Alert Frequency / Interval:</b>\nHow frequently would you like to receive Hot Deals alerts?',
        'pl': '⏱️ <b>Wybierz Częstotliwość Powiadomień:</b>\nJak często chcesz otrzymywać powiadomienia o Hot Deals?',
        'ru': '⏱️ <b>Выберите Частоту / Интервал Уведомлений:</b>\nС какой периодичностью вы хотите получать уведомления Hot Deals?'
    },
    'hd_param_updated': {
        'en': '✅ Parameter updated successfully!',
        'pl': '✅ Parametr pomyślnie zaktualizowany!',
        'ru': '✅ Параметр успешно обновлен!'
    },
    'prompt_make': {
        'en': '🚘 Please enter the car make (Required. e.g. <code>BMW</code>, <code>Toyota</code>, <code>Audi</code>):',
        'pl': '🚘 Proszę podać markę samochodu (Wymagane. np. <code>BMW</code>, <code>Toyota</code>, <code>Audi</code>):',
        'ru': '🚘 Пожалуйста, введите марку автомобиля (Обязательно. Например: <code>BMW</code>, <code>Toyota</code>, <code>Audi</code>):'
    },
    'dashboard_header': {
        'en': '🛠 <b>SEARCH DASHBOARD: {make}</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Model:</b> {model}\n• <b>Year:</b> {year}\n• <b>Mileage:</b> {mileage}\n• <b>Price:</b> {price}\n• <b>Fuel:</b> {fuel}\n• <b>Condition:</b> {condition}\n• <b>Transmission:</b> {transmission}\n• <b>Body Type:</b> {body_type}\n• <b>Country:</b> {country}\n━━━━━━━━━━━━━━━━━━━━━\nSelect a parameter to modify:',
        'pl': '🛠 <b>PANEL WYSZUKIWANIA: {make}</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Model:</b> {model}\n• <b>Rok:</b> {year}\n• <b>Przebieg:</b> {mileage}\n• <b>Cena:</b> {price}\n• <b>Paliwo:</b> {fuel}\n• <b>Stan:</b> {condition}\n• <b>Skrzynia:</b> {transmission}\n• <b>Nadwozie:</b> {body_type}\n• <b>Kraj:</b> {country}\n━━━━━━━━━━━━━━━━━━━━━\nWybierz parametr do zmiany:',
        'ru': '🛠 <b>ПАНЕЛЬ ПОИСКА: {make}</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Модель:</b> {model}\n• <b>Год:</b> {year}\n• <b>Пробег:</b> {mileage}\n• <b>Цена:</b> {price}\n• <b>Топливо:</b> {fuel}\n• <b>Состояние:</b> {condition}\n• <b>Коробка:</b> {transmission}\n• <b>Кузов:</b> {body_type}\n• <b>Страна:</b> {country}\n━━━━━━━━━━━━━━━━━━━━━\nВыберите параметр для изменения:'
    },
    'not_selected': {
        'en': '{Not selected}',
        'pl': '{Nie wybrano}',
        'ru': '{Не выбрано}'
    },
    'btn_model': {'en': '🚘 Model', 'pl': '🚘 Model', 'ru': '🚘 Модель'},
    'btn_year': {'en': '📅 Year Range', 'pl': '📅 Rocznik', 'ru': '📅 Диапазон Лет'},
    'btn_mileage': {'en': '🧭 Mileage (km)', 'pl': '🧭 Przebieg (km)', 'ru': '🧭 Пробег (км)'},
    'btn_price': {'en': '💰 Price (€)', 'pl': '💰 Cena (€)', 'ru': '💰 Цена (€)'},
    'btn_fuel': {'en': '⛽ Fuel', 'pl': '⛽ Paliwo', 'ru': '⛽ Топливо'},
    'btn_condition': {'en': '🛠 Condition', 'pl': '🛠 Stan', 'ru': '🛠 Состояние'},
    'btn_transmission': {'en': '⚙️ Gearbox', 'pl': '⚙️ Skrzynia', 'ru': '⚙️ Коробка'},
    'btn_body_type': {'en': '🏎 Body Type', 'pl': '🏎 Typ Nadwozia', 'ru': '🏎 Тип Кузова'},
    'btn_country': {'en': '🌍 Target Country', 'pl': '🌍 Kraj', 'ru': '🌍 Страna'},
    'btn_submit_topic': {
        'en': '🚀 Launch Search & Monitor',
        'pl': '🚀 Rozpocznij i Monitoruj',
        'ru': '🚀 Запустить Поиск и Мониторинг'
    },
    'btn_cancel': {'en': '❌ Cancel', 'pl': '❌ Anuluj', 'ru': '❌ Отмена'},
    'prompt_model_input': {
        'en': '🚘 Enter car model (e.g. <code>X5</code>, <code>Camry</code>, <code>A6</code>) or enter <code>-</code> to reset:',
        'pl': '🚘 Podaj model samochodu (np. <code>X5</code>, <code>Camry</code>, <code>A6</code>) lub wpisz <code>-</code>, aby zresetować:',
        'ru': '🚘 Введите модель (например: <code>X5</code>, <code>Camry</code>, <code>A6</code>) или введите <code>-</code> для сброса:'
    },
    'prompt_year_input': {
        'en': '📅 Enter year range (e.g. <code>2015 2022</code> or single minimum year <code>2015</code>):',
        'pl': '📅 Podaj zakres rocznika (np. <code>2015 2022</code> lub minimalny <code>2015</code>):',
        'ru': '📅 Введите диапазон лет (например: <code>2015 2022</code> или минимальный <code>2015</code>):'
    },
    'prompt_mileage_input': {
        'en': '🧭 Enter mileage in km (e.g. max <code>180000</code> or range <code>50000 150000</code>):',
        'pl': '🧭 Podaj przebieg w km (np. maks <code>180000</code> lub zakres <code>50000 150000</code>):',
        'ru': '🧭 Введите пробег в км (например: макс <code>180000</code> или диапазон <code>50000 150000</code>):'
    },
    'prompt_price_input': {
        'en': '💰 Enter min and max price in EUR (e.g. <code>4000 9000</code> or just max <code>9000</code>):',
        'pl': '💰 Podaj minimalną i maksymalną cenę w EUR (np. <code>4000 9000</code> lub maks <code>9000</code>):',
        'ru': '💰 Введите мин и макс цену в EUR (например: <code>4000 9000</code> или просто макс <code>9000</code>):'
    },
    'input_invalid_format': {
        'en': '⚠️ Invalid format. Please try again or cancel.',
        'pl': '⚠️ Nieprawidłowy format. Spróbuj ponownie lub anuluj.',
        'ru': '⚠️ Неверный формат. Пожалуйста, попробуйте снова или отмените.'
    },
    'filter_cancelled': {
        'en': '❌ Search creation cancelled.',
        'pl': '❌ Tworzenie wyszukiwania zostało anulowane.',
        'ru': '❌ Создание поиска отменено.'
    },
    'topic_creating': {
        'en': '⏳ Creating your search filter...',
        'pl': '⏳ Tworzenie filtra wyszukiwania...',
        'ru': '⏳ Создание фильтра поиска...'
    },
    'topic_created_success': {
        'en': '✅ <b>Your search was successfully created!</b>',
        'pl': '✅ <b>Wyszukiwanie utworzone pomyślnie!</b>',
        'ru': '✅ <b>Ваш поиск успешно создан!</b>'
    },
    'btn_go_to_topic': {
        'en': '🔗 Go to Topic',
        'pl': '🔗 Przejdź do Tematu',
        'ru': '🔗 Перейти в Тему'
    },
    'topic_creation_error': {
        'en': '⚠️ An error occurred while creating search.',
        'pl': '⚠️ Wystąpił błąd podczas tworzenia wyszukiwania.',
        'ru': '⚠️ Произошла ошибка при создании поиска.'
    },
    'pinned_summary_card': {
        'en': '📌 <b>SEARCH PARAMETERS</b>\n━━━━━━━━━━━━━━━━━━━━━\n<b>Make:</b> {make}\n<b>Model:</b> {model}\n<b>Year:</b> {year}\n<b>Mileage:</b> {mileage}\n<b>Price:</b> {price}\n<b>Fuel:</b> {fuel}\n<b>Transmission:</b> {transmission}\n<b>Condition:</b> {condition}\n<b>Body:</b> {body_type}\n<b>Country:</b> {country}\n━━━━━━━━━━━━━━━━━━━━━\n⏳ <i>Scanner active. Matching deals will be delivered right here.</i>',
        'pl': '📌 <b>PARAMETRY WYSZUKIWANIA</b>\n━━━━━━━━━━━━━━━━━━━━━\n<b>Marka:</b> {make}\n<b>Model:</b> {model}\n<b>Rocznik:</b> {year}\n<b>Przebieg:</b> {mileage}\n<b>Cena:</b> {price}\n<b>Paliwo:</b> {fuel}\n<b>Skrzynia:</b> {transmission}\n<b>Stan:</b> {condition}\n<b>Nadwozie:</b> {body_type}\n<b>Kraj:</b> {country}\n━━━━━━━━━━━━━━━━━━━━━\n⏳ <i>Skaner aktywny. Pasujące oferty będą publikowane w tym wątku.</i>',
        'ru': '📌 <b>ПАРАМЕТРЫ ПОИСКА</b>\n━━━━━━━━━━━━━━━━━━━━━\n<b>Марка:</b> {make}\n<b>Модель:</b> {model}\n<b>Год:</b> {year}\n<b>Пробег:</b> {mileage}\n<b>Цена:</b> {price}\n<b>Топливо:</b> {fuel}\n<b>Коробка:</b> {transmission}\n<b>Состояние:</b> {condition}\n<b>Кузов:</b> {body_type}\n<b>Страна:</b> {country}\n━━━━━━━━━━━━━━━━━━━━━\n⏳ <i>Сканер активен. Подходящие авто будут публиковаться здесь.</i>'
    },
    'my_topics_title': {
        'en': '📋 <b>YOUR SEARCH FILTERS:</b>',
        'pl': '📋 <b>TWOJE FILTRY WYSZUKIWANIA:</b>',
        'ru': '📋 <b>ВАШИ ФИЛЬТРЫ ПОИСКА:</b>'
    },
    'my_topics_subtitle': {
        'en': '📋 <b>YOUR SEARCH FILTERS:</b>\n<i>Tap a filter below to manage settings or fetch current listings:</i>',
        'pl': '📋 <b>TWOJE FILTRY WYSZUKIWANIA:</b>\n<i>Kliknij filtr poniżej, aby zmienić ustawienia lub pobrać oferty:</i>',
        'ru': '📋 <b>ВАШИ ФИЛЬТРЫ ПОИСКА:</b>\n<i>Нажмите на фильтр ниже для настройки или загрузки объявлений:</i>'
    },
    'no_topics_found': {
        'en': 'ℹ️ <b>You do not have any active search filters yet.</b>\n\nCreate a new search below to start live scanning European car markets.',
        'pl': 'ℹ️ <b>Nie masz jeszcze aktywnych filtrów wyszukiwania.</b>\n\nUtwórz nowe wyszukiwanie poniżej, aby rozpocząć skanowanie ofert w Europie.',
        'ru': 'ℹ️ <b>У вас пока нет активных фильтров поиска.</b>\n\nСоздайте новый поиск ниже, чтобы запустить сканирование рынков Европы.'
    },
    'btn_pause': {'en': '⏸ Pause', 'pl': '⏸ Wstrzymaj', 'ru': '⏸ Пауза'},
    'btn_resume': {'en': '▶️ Resume', 'pl': '▶️ Wznów', 'ru': '▶️ Запустить'},
    'btn_delete_topic': {'en': '🗑 Delete', 'pl': '🗑 Usuń', 'ru': '🗑 Удалить'},
    'confirm_delete_prompt': {
        'en': '⚠️ Are you sure you want to delete this filter?',
        'pl': '⚠️ Czy na pewno chcesz usunąć ten filtr?',
        'ru': '⚠️ Вы уверены, что хотите удалить этот фильтр?'
    },
    'btn_confirm_yes': {'en': '✅ Yes, Delete', 'pl': '✅ Tak, Usuń', 'ru': '✅ Да, Удалить'},
    'btn_confirm_no': {'en': '❌ Cancel', 'pl': '❌ Anuluj', 'ru': '❌ Отмена'},
    'topic_deleted_success': {
        'en': '🗑 Filter successfully deleted.',
        'pl': '🗑 Filtr został pomyślnie usunięty.',
        'ru': '🗑 Фильтр успешно удален.'
    },
    'stats_template': {
        'en': '📊 <b>SYSTEM STATISTICS</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 Registered Users: <b>{total_users}</b>\n🚘 Active Filters: <b>{active_filters}</b>\n📁 Total Topics: <b>{total_topics}</b>\n🔍 Scraped Listings: <b>{seen_listings}</b>\n🇵🇱 Otomoto Market Benchmarks: <b>{cached_benchmarks}</b>',
        'pl': '📊 <b>STATYSTYKI SYSTEMU</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 Zarejestrowani Użytkownicy: <b>{total_users}</b>\n🚘 Aktywne Filtry: <b>{active_filters}</b>\n📁 Wszystkie Tematy: <b>{total_topics}</b>\n🔍 Przeskanowane Oferty: <b>{seen_listings}</b>\n🇵🇱 Otomoto Benchmarki Rynkowe: <b>{cached_benchmarks}</b>',
        'ru': '📊 <b>СТАТИСТИКА СИСТЕМЫ</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 Пользователей: <b>{total_users}</b>\n🚘 Активных Фильтров: <b>{active_filters}</b>\n📁 Всего Тем: <b>{total_topics}</b>\n🔍 Просканировано Объявлений: <b>{seen_listings}</b>\n🇵🇱 Otomoto Бенчмарков: <b>{cached_benchmarks}</b>'
    },
    'submenu_fuel': {
        'en': '⛽ <b>Select Fuel Type:</b>\nChoose preferred engine/fuel type from the list below:',
        'pl': '⛽ <b>Wybierz Rodzaj Paliwa:</b>\nWybierz rodzaj silnika z poniższej listy:',
        'ru': '⛽ <b>Выберите Тип Топлива:</b>\nВыберите тип топлива из списка ниже:'
    },
    'submenu_country': {
        'en': '🌍 <b>Select Target Country:</b>\nChoose European automotive market to scan:',
        'pl': '🌍 <b>Wybierz Kraj Docelowy:</b>\nWybierz rynek europejski do monitorowania:',
        'ru': '🌍 <b>Выберите Страну:</b>\nВыберите авторынок для сканирования:'
    },
    'submenu_transmission': {
        'en': '⚙️ <b>Select Transmission:</b>\nChoose preferred gearbox type:',
        'pl': '⚙️ <b>Wybierz Skrzynię Biegów:</b>\nWybierz rodzaj skrzyni biegów:',
        'ru': '⚙️ <b>Выберите Коробку Передач:</b>\nВыберите тип коробки передач:'
    },
    'submenu_condition': {
        'en': '🛠 <b>Select Vehicle Condition:</b>\nFilter by vehicle accident history / condition:',
        'pl': '🛠 <b>Wybierz Stan Pojazdu:</b>\nFiltruj według stanu technicznego:',
        'ru': '🛠 <b>Выберите Состояние:</b>\nФильтровать по состоянию авто:'
    },
    'submenu_body_type': {
        'en': '🏎 <b>Select Body Type:</b>\nChoose vehicle body styling:',
        'pl': '🏎 <b>Wybierz Typ Nadwozia:</b>\nWybierz rodzaj nadwozia:',
        'ru': '🏎 <b>Выберите Тип Кузова:</b>\nВыберите тип кузова автомобиля:'
    },
    'submenu_mileage': {
        'en': '🧭 <b>Select Maximum Mileage:</b>\nChoose acceptable maximum odometer reading:',
        'pl': '🧭 <b>Wybierz Maksymalny Przebieg:</b>\nWybierz akceptowalny maksymalny przebieg:',
        'ru': '🧭 <b>Выберите Максимальный Пробег:</b>\nВыберите допустимый максимальный пробег:'
    },
    'step_year_min_title': {
        'en': '📅 <b>Step 1/2: Select Minimum Year</b>\nChoose oldest acceptable production year:',
        'pl': '📅 <b>Krok 1/2: Wybierz Minimalny Rok</b>\nWybierz najstarszy akceptowany rok produkcji:',
        'ru': '📅 <b>Шаг 1/2: Выберите Минимальный Год</b>\nВыберите самый ранний год выпуска авто:'
    },
    'step_year_max_title': {
        'en': '📅 <b>Step 2/2: Select Maximum Year</b> (Min: {min_year})\nChoose newest production year:',
        'pl': '📅 <b>Krok 2/2: Wybierz Maksymalny Rok</b> (Min: {min_year})\nWybierz najnowszy rok produkcji:',
        'ru': '📅 <b>Шаг 2/2: Выберите Максимальный Год</b> (Мин: {min_year})\nВыберите самый поздний год выпуска:'
    },
    'step_price_min_title': {
        'en': '💰 <b>Step 1/2: Select Minimum Price (€)</b>\nChoose minimum purchase price:',
        'pl': '💰 <b>Krok 1/2: Wybierz Minimalną Cenę (€)</b>\nWybierz minimalną cenę zakupu:',
        'ru': '💰 <b>Шаг 1/2: Выберите Минимальную Цену (€)</b>\nВыберите минимальную стоимость авто:'
    },
    'step_price_max_title': {
        'en': '💰 <b>Step 2/2: Select Maximum Price (€)</b> (Min: {min_price})\nChoose maximum purchase budget:',
        'pl': '💰 <b>Krok 2/2: Wybierz Maksymalną Cenę (€)</b> (Min: {min_price})\nWybierz maksymalny budżet:',
        'ru': '💰 <b>Шаг 2/2: Выберите Максимальную Цену (€)</b> (Мин: {min_price})\nВыберите максимальный бюджет покупки:'
    },
    'btn_any_min': {
        'en': 'Any (No min)',
        'pl': 'Dowolny (Bez min)',
        'ru': 'Любой (Без мин)'
    },
    'btn_any_max': {
        'en': 'Any (No limit / ∞)',
        'pl': 'Bez limitu (∞)',
        'ru': 'Без лимита (∞)'
    },
    'select_make_title': {
        'en': '🚘 <b>Select Car Make:</b>\nChoose a popular brand or enter custom name below:',
        'pl': '🚘 <b>Wybierz Markę Samochodu:</b>\nWybierz popularną markę lub wpisz własną poniżej:',
        'ru': '🚘 <b>Выберите Марку Автомобиля:</b>\nВыберите марку из списка или введите вручную:'
    },
    'select_model_title': {
        'en': '🚘 <b>Select Model ({make}):</b>\nChoose a popular model or select all models:',
        'pl': '🚘 <b>Wybierz Model ({make}):</b>\nWybierz popularny model lub wszystkie modele:',
        'ru': '🚘 <b>Выберите Модель ({make}):</b>\nВыберите модель из списка или все модели:'
    },
    'btn_other_make': {
        'en': '✍️ Other Make (Type)',
        'pl': '✍️ Inna Marka (Wpisz)',
        'ru': '✍️ Другая Марка (Ввести)'
    },
    'btn_all_models': {
        'en': 'All Models (Any)',
        'pl': 'Wszystkie Modele (Dowolny)',
        'ru': 'Все Модели (Любая)'
    },
    'btn_custom_model': {
        'en': '✍️ Custom Model (Type)',
        'pl': '✍️ Inny Model (Wpisz)',
        'ru': '✍️ Другая Модель (Ввести)'
    },
    'btn_back_to_dashboard': {
        'en': '🔙 Back to Dashboard',
        'pl': '🔙 Panel Główny',
        'ru': '🔙 В Панель Поиска'
    },
    'btn_custom_input': {
        'en': '✍️ Custom Value',
        'pl': '✍️ Własna Wartość',
        'ru': '✍️ Свое Значение'
    },
    'btn_notify_dest_dm': {
        'en': '🔔 Delivery: Private Chat 🟢',
        'pl': '🔔 Dostawa: Czat Prywatny 🟢',
        'ru': '🔔 Доставка: Личный Чат 🟢'
    },
    'btn_notify_dest_group': {
        'en': '🔔 Delivery: Private Group 👥',
        'pl': '🔔 Dostawa: Grupa Prywatna 👥',
        'ru': '🔔 Доставка: Личная Группа 👥'
    },
    'btn_switch_to_group': {
        'en': '👥 Switch to Group (Pro)',
        'pl': '👥 Przełącz na Grupę (Pro)',
        'ru': '👥 Переключить на Группу (Pro)'
    },
    'btn_switch_to_dm': {
        'en': '🟢 Switch to Private Chat',
        'pl': '🟢 Przełącz na Czat Prywatny',
        'ru': '🟢 Переключить на Личный Чат'
    },
    'btn_connect_group': {
        'en': '👥 Connect Private Group (Topics)',
        'pl': '👥 Połącz Grupę Prywatną (Tematy)',
        'ru': '👥 Подключить Личную Группу (Темы)'
    },
    'btn_disconnect_group': {
        'en': '🔄 Change / Disconnect Group',
        'pl': '🔄 Zmień / Odłącz Grupę',
        'ru': '🔄 Сменить / Отключить Группу'
    },
    'admin_restricted': {
        'en': '⛔ This command is only for authorized administrators.',
        'pl': '⛔ Ta komenda jest dostępna tylko dla autoryzowanych administratorów.',
        'ru': '⛔ Эта команда доступна только для авторизованных администраторов.'
    },
    'group_error_fallback': {
        'en': '⚠️ <b>Error delivering to your group</b> (permissions changed or group deleted).\n\nTo ensure you do not miss deals, alerts are temporarily redirected to your <b>private chat</b>.',
        'pl': '⚠️ <b>Błąd dostarczania do grupy</b> (zmieniono uprawnienia lub usunięto grupę).\n\nAby nie przegapić ofert, powiadomienia zostały przekierowane na <b>czat prywatny</b>.',
        'ru': '⚠️ <b>Ошибка отправки в группу</b> (изменились права или группа удалена).\n\nЧтобы не пропустить предложения, уведомления временно направлены в <b>личный чат</b>.'
    },
    'btn_edit_model': {
        'en': '🚘 Change Make / Model',
        'pl': '🚘 Zmień Markę / Model',
        'ru': '🚘 Изменить Марку / Модель'
    },
    'btn_edit_year': {
        'en': '📅 Year Range',
        'pl': '📅 Zakres Lat',
        'ru': '📅 Диапазон Лет'
    },
    'btn_edit_price': {
        'en': '💰 Price Budget',
        'pl': '💰 Budżet Cenowy',
        'ru': '💰 Бюджет Цен'
    },
    'btn_edit_mileage': {
        'en': '🧭 Max Mileage',
        'pl': '🧭 Maks. Przebieg',
        'ru': '🧭 Макс. Пробег'
    },
    'btn_edit_limit': {
        'en': '📊 Daily Limit',
        'pl': '📊 Dzienny Limit',
        'ru': '📊 Дневной Лимит'
    },
    'btn_edit_age': {
        'en': '⏱️ Age Window',
        'pl': '⏱️ Zakres Czasu',
        'ru': '⏱️ Период'
    },
    'btn_fetch_now': {
        'en': '📥 Fetch Current Listings Now',
        'pl': '📥 Pobierz Oferty Teraz',
        'ru': '📥 Загрузить Объявления Сейчас'
    },
    'btn_delete_filter': {
        'en': '🗑️ Delete Filter',
        'pl': '🗑️ Usuń Filtr',
        'ru': '🗑️ Удалить Фильтр'
    },
    'btn_back_to_filters': {
        'en': '🔙 My Filters List',
        'pl': '🔙 Lista Filtrów',
        'ru': '🔙 Список Фильтров'
    },
    'btn_pause_action': {
        'en': '⏸️ Pause',
        'pl': '⏸️ Wstrzymaj',
        'ru': '⏸️ Приостановить'
    },
    'btn_resume_action': {
        'en': '▶️ Activate',
        'pl': '▶️ Aktywuj',
        'ru': '▶️ Активировать'
    },
    'filter_details_title': {
        'en': '🛠 <b>FILTER PARAMETERS: #{fid}</b>',
        'pl': '🛠 <b>PARAMETRY FILTRA: #{fid}</b>',
        'ru': '🛠 <b>ПАРАМЕТРЫ ФИЛЬТРА: #{fid}</b>'
    },
    'filter_car_label': {
        'en': 'Car',
        'pl': 'Samochód',
        'ru': 'Автомобиль'
    },
    'filter_year_label': {
        'en': 'Year',
        'pl': 'Rocznik',
        'ru': 'Год'
    },
    'filter_price_label': {
        'en': 'Price Budget',
        'pl': 'Budżet cenowy',
        'ru': 'Бюджет цен'
    },
    'filter_mileage_label': {
        'en': 'Max Mileage',
        'pl': 'Maks. Przebieg',
        'ru': 'Макс. Пробег'
    },
    'filter_fuel_label': {
        'en': 'Fuel',
        'pl': 'Paliwo',
        'ru': 'Топливо'
    },
    'filter_gearbox_label': {
        'en': 'Gearbox',
        'pl': 'Skrzynia biegów',
        'ru': 'Коробка'
    },
    'filter_market_label': {
        'en': 'Market',
        'pl': 'Rynek',
        'ru': 'Рынок'
    },
    'filter_limit_label': {
        'en': 'Daily Limit',
        'pl': 'Dzienny limit',
        'ru': 'Дневной лимит'
    },
    'filter_age_label': {
        'en': 'Age Window',
        'pl': 'Zakres czasu',
        'ru': 'Период'
    },
    'filter_status_label': {
        'en': 'Status',
        'pl': 'Status',
        'ru': 'Статус'
    },
    'filter_edit_hint': {
        'en': 'Select a parameter to modify or fetch live listings:',
        'pl': 'Wybierz parametr do zmiany lub pobierz oferty:',
        'ru': 'Выберите параметр для изменения или загрузите объявления:'
    },
    'filter_not_found': {
        'en': '⚠️ Filter not found.',
        'pl': '⚠️ Nie znaleziono filtra.',
        'ru': '⚠️ Фильтр не найден.'
    },
    'filter_deleted_msg': {
        'en': '🗑 <b>Filter successfully deleted.</b>',
        'pl': '🗑 <b>Filtr pomyślnie usunięty.</b>',
        'ru': '🗑 <b>Фильтр успешно удален.</b>'
    },
    'confirm_delete_filter_text': {
        'en': '⚠️ <b>Are you sure you want to delete this search filter?</b>\n\n🚙 <b>{make} {model}</b>',
        'pl': '⚠️ <b>Czy na pewno chcesz usunąć ten filtr wyszukiwania?</b>\n\n🚙 <b>{make} {model}</b>',
        'ru': '⚠️ <b>Вы уверены, что хотите удалить этот фильтр поиска?</b>\n\n🚙 <b>{make} {model}</b>'
    },
    'all_models': {
        'en': 'All Models',
        'pl': 'Wszystkie Modele',
        'ru': 'Все Модели'
    },
    'any_label': {
        'en': 'Any',
        'pl': 'Dowolny',
        'ru': 'Любой'
    },
    'unlimited': {
        'en': 'Unlimited',
        'pl': 'Bez limitu',
        'ru': 'Без лимита'
    },
    'limit_unlimited': {
        'en': '♾️ Unlimited',
        'pl': '♾️ Bez limitu',
        'ru': '♾️ Без лимита'
    },
    'limit_per_day': {
        'en': '{limit} listings / day',
        'pl': '{limit} ofert / dzień',
        'ru': '{limit} объявл. / день'
    },
    'sent_today_label': {
        'en': 'Sent today: {count}',
        'pl': 'Wysłano dzisiaj: {count}',
        'ru': 'Отправлено сегодня: {count}'
    },
    'age_realtime': {
        'en': '⚡ Real-Time (Instant)',
        'pl': '⚡ Na żywo (Błyskawicznie)',
        'ru': '⚡ В реальном времени (Мгновенно)'
    },
    'age_1h': {
        'en': '⏱️ Last 1 Hour',
        'pl': '⏱️ Ostatnia 1 godzina',
        'ru': '⏱️ За последний 1 час'
    },
    'age_24h': {
        'en': '📅 Last 24 Hours (1 day)',
        'pl': '📅 Ostatnie 24 godziny (1 dzień)',
        'ru': '📅 За последние 24 часа (1 день)'
    },
    'age_7d': {
        'en': '🗓️ Last 7 Days (1 week)',
        'pl': '🗓️ Ostatnie 7 dni (1 tydzień)',
        'ru': '🗓️ За последние 7 дней (1 tydzień)'
    },
    'age_30d': {
        'en': '🗓️ Last 30 Days (1 month)',
        'pl': '🗓️ Ostatnie 30 dni (1 miesiąc)',
        'ru': '🗓️ За последние 30 дней (1 месяц)'
    },
    'age_all': {
        'en': '🌐 All / No restriction',
        'pl': '🌐 Wszystkie / Bez ograniczeń',
        'ru': '🌐 Все / Без ограничений'
    },
    'search_activated_success': {
        'en': '✅ <b>Your search was successfully activated!</b>',
        'pl': '✅ <b>Wyszukiwanie zostało pomyślnie aktywowane!</b>',
        'ru': '✅ <b>Ваш поиск успешно активирован!</b>'
    },
    'group_topic_notice': {
        'en': '👥 <b>Topic Opened in Your Group:</b> All listings matching this filter will be sent to the dedicated <b>{topic_name}</b> topic in <b>{group_title}</b>.',
        'pl': '👥 <b>Utworzono Temat w Grupie:</b> Wszystkie oferty spełniające ten filtr będą wysyłane do dedykowanego tematu <b>{topic_name}</b> w grupie <b>{group_title}</b>.',
        'ru': '👥 <b>Создана Тема в Вашей Группе:</b> Все подходящие объявления будут направляться в ветку <b>{topic_name}</b> в группе <b>{group_title}</b>.'
    },
    'dm_protection_notice': {
        'en': '🔒 <b>100% Private Chat Delivery:</b> All matching listings will be delivered confidentially to this private chat.',
        'pl': '🔒 <b>100% Prywatny Czat:</b> Wszystkie pasujące oferty będą przesyłane poufnie bezpośrednio do tego czatu prywatnego.',
        'ru': '🔒 <b>100% Личный Чат:</b> Все подходящие объявления будут конфиденциально отправляться только в этот личный чат.'
    },
    'dm_multi_filter_tip': {
        'en': '💡 <b>Tip:</b> If you track multiple cars, you can connect your private group to organize each car into separate forum topics.',
        'pl': '💡 <b>Wskazówka:</b> Jeśli szukasz wielu aut, możesz połączyć swoją grupę, aby każde auto trafiało do osobnego tematu.',
        'ru': '💡 <b>Совет:</b> Если вы ищете несколько авто, подключите группу, чтобы каждое авто публиковалось в отдельной ветке (топике).'
    },
    'what_next_hint': {
        'en': '<i>What would you like to do next?</i>',
        'pl': '<i>Co chcesz teraz zrobić?</i>',
        'ru': '<i>Что вы хотите сделать дальше?</i>'
    },
    'btn_filter_settings': {
        'en': '⚙️ Filter Settings & Limit',
        'pl': '⚙️ Ustawienia Filtra i Limit',
        'ru': '⚙️ Настройки Фильтра и Лимит'
    },
    'btn_connect_group_pro': {
        'en': '👥 Connect Private Group (Topics Pro)',
        'pl': '👥 Połącz Grupę Prywatną (Tematy Pro)',
        'ru': '👥 Подключить Личную Группу (Темы Pro)'
    },
    'btn_go_to_group_topic': {
        'en': '🔗 Go to Group Topic',
        'pl': '🔗 Przejdź do Tematu w Grupie',
        'ru': '🔗 Перейти в Тему Группы'
    },
    'daily_limit_title': {
        'en': '📊 <b>Select Daily Alert Limit:</b>\nMaximum listings to send per day for this filter:',
        'pl': '📊 <b>Wybierz Dzienny Limit Alertów:</b>\nMaksymalna liczba ofert dziennie dla tego filtra:',
        'ru': '📊 <b>Выберите Дневной Лимит:</b>\nМаксимальное количество объявлений в день:'
    },
    'age_window_title': {
        'en': '⏱️ <b>Select Listing Age Window:</b>\nFilter deals by how recently they were posted on the market:',
        'pl': '⏱️ <b>Wybierz Zakres Wieku Ofert:</b>\nFiltruj oferty według czasu publikacji na rynku:',
        'ru': '⏱️ <b>Выберите Период Публикаций:</b>\nФильтровать объявления по времени размещения:'
    },
    'group_connected_success': {
        'en': '✅ <b>Private group connected successfully!</b>\nGroup: <b>{title}</b>\n\nNew searches will now automatically create dedicated forum topics.',
        'pl': '✅ <b>Grupa prywatna została pomyślnie połączona!</b>\nGrupa: <b>{title}</b>\n\nNowe wyszukiwania będą automatycznie tworzyć osobne tematy na forum.',
        'ru': '✅ <b>Личная группа успешно подключена!</b>\nГруппа: <b>{title}</b>\n\nНовые поиски теперь будут автоматически создавать темы на форуме.'
    },
    'group_switch_dm_alert': {
        'en': '✅ Notifications switched to Private Chat (DM).',
        'pl': '✅ Powiadomienia przełączone na Czat Prywatny.',
        'ru': '✅ Уведомления переключены в Личный Чат.'
    },
    'group_switch_group_alert': {
        'en': '✅ Notifications switched to Private Group Topics.',
        'pl': '✅ Powiadomienia przełączone na Tematy w Grupie Prywatnej.',
        'ru': '✅ Уведомления переключены в Темы Группы.'
    },
    'group_disconnected_alert': {
        'en': '🔄 Group disconnected. Notifications switched to Private Chat.',
        'pl': '🔄 Grupa odłączona. Powiadomienia przełączone na Czat Prywatny.',
        'ru': '🔄 Группа отключена. Уведомления переключены в Личный Чат.'
    },
    'group_connect_info': {
        'en': '👥 <b>HOW TO CONNECT YOUR PRIVATE GROUP:</b>\n━━━━━━━━━━━━━━━━━━━━━\n1. Create a supergroup with <b>Forum Topics enabled</b>.\n2. Add this bot as an <b>Administrator</b> with permissions to:\n   • Manage Topics\n   • Pin Messages\n3. Send /connect command in your group.\n\nOnce connected, all your searches will have their own dedicated topic!',
        'pl': '👥 <b>JAK POŁĄCZYĆ WŁASNĄ GRUPĘ:</b>\n━━━━━━━━━━━━━━━━━━━━━\n1. Utwórz supergrupę z <b>włączonymi tematami forum</b>.\n2. Dodaj tego bota jako <b>Administratora</b> z uprawnieniami:\n   • Zarządzanie tematami\n   • Przypinanie wiadomości\n3. Wyślij komendę /connect w swojej grupie.\n\nPo połączeniu każdy filtr otrzyma swój osobny wątek!',
        'ru': '👥 <b>КАК ПОДКЛЮЧИТЬ ЛИЧНУЮ ГРУППУ:</b>\n━━━━━━━━━━━━━━━━━━━━━\n1. Создайте супергруппу с <b>включенными темами (форумом)</b>.\n2. Добавьте бота в качестве <b>Администратора</b> с правами:\n   • Управление темами\n   • Закрепление сообщений\n3. Отправьте команду /connect в своей группе.\n\nПосле подключения для каждого фильтра будет создана отдельная тема!'
    },
    'group_only_command': {
        'en': '⚠️ Please run this command inside the Telegram Supergroup you want to connect.',
        'pl': '⚠️ Proszę uruchomić tę komendę wewnątrz supergrupy Telegram, którą chcesz połączyć.',
        'ru': '⚠️ Пожалуйста, выполните эту команду внутри группы Telegram, которую хотите подключить.'
    },
    'edit_model_prompt': {
        'en': '🚘 <b>Change Model or Make:</b>\n\nCurrent search: <b>{make} {model}</b>\n\nEnter new model (e.g. <code>Auris</code>, <code>Prius</code>, <code>X5</code>, <code>Passat</code>).\nTo change both make and model, type both (e.g. <code>Toyota Auris</code> or <code>BMW 520</code>).\nEnter <code>-</code> for all models.\n\n<i>Type /cancel to cancel.</i>',
        'pl': '🚘 <b>Zmiana Modelu lub Marki:</b>\n\nObecne wyszukiwanie: <b>{make} {model}</b>\n\nWpisz nowy model (np. <code>Auris</code>, <code>Prius</code>, <code>X5</code>, <code>Passat</code>).\nAby zmienić markę i model, wpisz oba (np. <code>Toyota Auris</code> lub <code>BMW 520</code>).\nWpisz <code>-</code> dla wszystkich modeli.\n\n<i>Wpisz /cancel, aby anulować.</i>',
        'ru': '🚘 <b>Изменение Модели или Марки:</b>\n\nТекущий поиск: <b>{make} {model}</b>\n\nВведите новую модель (например: <code>Auris</code>, <code>Prius</code>, <code>X5</code>, <code>Passat</code>).\nЧтобы изменить марку и модель, введите обе (например: <code>Toyota Auris</code> или <code>BMW 520</code>).\nВведите <code>-</code> для всех моделей.\n\n<i>Введите /cancel для отмены.</i>'
    },
    'edit_year_prompt': {
        'en': '📅 <b>Enter Year Range:</b>\n\nFor example: <code>2016 2023</code> (min and max) or just <code>2015</code> for minimum year.\nEnter <code>-</code> to remove year restriction.\n\n<i>Type /cancel to cancel.</i>',
        'pl': '📅 <b>Podaj Zakres Rocznika:</b>\n\nNa przykład: <code>2016 2023</code> (min i max) lub samo <code>2015</code> jako rok minimalny.\nWpisz <code>-</code>, aby usunąć ograniczenie rocznika.\n\n<i>Wpisz /cancel, aby anulować.</i>',
        'ru': '📅 <b>Введите Диапазон Лет:</b>\n\nНапример: <code>2016 2023</code> (мин и макс) или просто <code>2015</code> для минимального года.\nВведите <code>-</code>, чтобы снять ограничение года.\n\n<i>Введите /cancel для отмены.</i>'
    },
    'edit_price_prompt': {
        'en': '💰 <b>Enter Price Budget (EUR):</b>\n\nFor example: <code>4000 9000</code> (min and max) or just <code>9000</code> for maximum price.\nEnter <code>-</code> to remove price restriction.\n\n<i>Type /cancel to cancel.</i>',
        'pl': '💰 <b>Podaj Budżet Cenowy (EUR):</b>\n\nNa przykład: <code>4000 9000</code> (min i max) lub samo <code>9000</code> jako cena maksymalna.\nWpisz <code>-</code>, aby usunąć ograniczenie ceny.\n\n<i>Wpisz /cancel, aby anulować.</i>',
        'ru': '💰 <b>Введите Бюджет Цен (EUR):</b>\n\nНапример: <code>4000 9000</code> (мин и макс) или просто <code>9000</code> для максимальной цены.\nВведите <code>-</code>, чтобы снять ограничение цены.\n\n<i>Введите /cancel для отмены.</i>'
    },
    'edit_mileage_prompt': {
        'en': '🧭 <b>Enter Maximum Mileage (km):</b>\n\nFor example: <code>150000</code> or <code>180000</code>.\nEnter <code>-</code> to remove mileage restriction.\n\n<i>Type /cancel to cancel.</i>',
        'pl': '🧭 <b>Podaj Maksymalny Przebieg (km):</b>\n\nNa przykład: <code>150000</code> lub <code>180000</code>.\nWpisz <code>-</code>, aby usunąć ograniczenie przebiegu.\n\n<i>Wpisz /cancel, aby anulować.</i>',
        'ru': '🧭 <b>Введите Максимальный Пробег (км):</b>\n\nНапример: <code>150000</code> или <code>180000</code>.\nВведите <code>-</code>, чтобы снять ограничение пробега.\n\n<i>Введите /cancel для отмены.</i>'
    },
    'edit_cancelled': {
        'en': '❌ Changes cancelled.',
        'pl': '❌ Zmiany zostały anulowane.',
        'ru': '❌ Изменения отменены.'
    },
    'edit_model_success': {
        'en': '✅ Filter updated: <b>{label}</b>',
        'pl': '✅ Filtr zaktualizowany: <b>{label}</b>',
        'ru': '✅ Фильтр обновлен: <b>{label}</b>'
    },
    'edit_year_cleared': {
        'en': '✅ Year restriction removed.',
        'pl': '✅ Usunięto ograniczenie rocznika.',
        'ru': '✅ Ограничение по году снято.'
    },
    'edit_year_invalid': {
        'en': '⚠️ Please enter a valid year (e.g. <code>2015</code> or <code>2015 2022</code>):',
        'pl': '⚠️ Podaj poprawny rocznik (np. <code>2015</code> lub <code>2015 2022</code>):',
        'ru': '⚠️ Введите корректный год (например: <code>2015</code> или <code>2015 2022</code>):'
    },
    'edit_year_success': {
        'en': '✅ Year range updated: <b>{range}</b>',
        'pl': '✅ Zakres rocznika zaktualizowany: <b>{range}</b>',
        'ru': '✅ Диапазон лет обновлен: <b>{range}</b>'
    },
    'edit_price_cleared': {
        'en': '✅ Price restriction removed.',
        'pl': '✅ Usunięto ograniczenie ceny.',
        'ru': '✅ Ограничение цены снято.'
    },
    'edit_price_invalid': {
        'en': '⚠️ Please enter a valid price (e.g. <code>5000 12000</code>):',
        'pl': '⚠️ Podaj poprawną cenę (np. <code>5000 12000</code>):',
        'ru': '⚠️ Введите корректную цену (например: <code>5000 12000</code>):'
    },
    'edit_price_success': {
        'en': '✅ Price budget updated: <b>{price}</b>',
        'pl': '✅ Budżet cenowy zaktualizowany: <b>{price}</b>',
        'ru': '✅ Бюджет цен обновлен: <b>{price}</b>'
    },
    'edit_mileage_cleared': {
        'en': '✅ Mileage restriction removed.',
        'pl': '✅ Usunięto ograniczenie przebiegu.',
        'ru': '✅ Ограничение пробега снято.'
    },
    'edit_mileage_invalid': {
        'en': '⚠️ Please enter a valid number (e.g. <code>150000</code>):',
        'pl': '⚠️ Podaj poprawną liczbę (np. <code>150000</code>):',
        'ru': '⚠️ Введите корректное число (например: <code>150000</code>):'
    },
    'edit_mileage_success': {
        'en': '✅ Maximum mileage updated: <b>{mileage} km</b>',
        'pl': '✅ Maksymalny przebieg zaktualizowany: <b>{mileage} km</b>',
        'ru': '✅ Максимальный пробег обновлен: <b>{mileage} км</b>'
    },
    'age_window_updated': {
        'en': '✅ Age window updated!',
        'pl': '✅ Zakres czasu zaktualizowany!',
        'ru': '✅ Период публикации обновлен!'
    },
    'daily_limit_updated': {
        'en': '✅ Daily alert limit updated!',
        'pl': '✅ Dzienny limit powiadomień zaktualizowany!',
        'ru': '✅ Дневной лимит уведомлений обновлен!'
    },
    'btn_back': {
        'en': '🔙 Back',
        'pl': '🔙 Wstecz',
        'ru': '🔙 Назад'
    },
    'btn_yes_delete': {
        'en': '✅ Yes, Delete',
        'pl': '✅ Tak, Usuń',
        'ru': '✅ Да, Удалить'
    },
    'btn_no_cancel': {
        'en': '❌ No, Cancel',
        'pl': '❌ Nie, Anuluj',
        'ru': '❌ Нет, Отмена'
    },
    'confirm_delete_filter': {
        'en': '⚠️ <b>Are you sure you want to delete this search filter?</b>\n\n🚙 <b>{make_model}</b>',
        'pl': '⚠️ <b>Czy na pewno chcesz usunąć ten filtr wyszukiwania?</b>\n\n🚙 <b>{make_model}</b>',
        'ru': '⚠️ <b>Вы уверены, что хотите удалить этот фильтр поиска?</b>\n\n🚙 <b>{make_model}</b>'
    },
    'filter_deleted_msg': {
        'en': '🗑 <b>Filter deleted successfully.</b>',
        'pl': '🗑 <b>Filtr został pomyślnie usunięty.</b>',
        'ru': '🗑 <b>Фильтр успешно удален.</b>'
    },
    'filter_deleted_alert': {
        'en': 'Filter deleted!',
        'pl': 'Filtr usunięty!',
        'ru': 'Фильтр удален!'
    },
    'filter_toggle_activated': {
        'en': 'activated ▶️',
        'pl': 'aktywowany ▶️',
        'ru': 'активирован ▶️'
    },
    'filter_toggle_paused': {
        'en': 'paused ⏸️',
        'pl': 'wstrzymany ⏸️',
        'ru': 'приостановлен ⏸️'
    },
    'filter_toggle_alert': {
        'en': 'Filter #{fid} {status}!',
        'pl': 'Filtr #{fid} {status}!',
        'ru': 'Фильтр #{fid} {status}!'
    },
    'fetch_searching': {
        'en': '🔍 Searching existing listings...',
        'pl': '🔍 Szukanie istniejących ogłoszeń...',
        'ru': '🔍 Поиск существующих объявлений...'
    },
    'fetch_not_found': {
        'en': 'ℹ️ <b>No past listings matching these parameters found in database yet:</b>\n🚙 <b>{make_model}</b>\n\n<i>European scanner is active 24/7. As soon as a matching car is published, it will be delivered directly here!</i>',
        'pl': 'ℹ️ <b>W bazie nie znaleziono jeszcze archiwalnych ogłoszeń pasujących do tych kryteriów:</b>\n🚙 <b>{make_model}</b>\n\n<i>Europejski skaner działa 24/7. Gdy tylko pojawi się nowe ogłoszenie, zostanie wysłane tutaj!</i>',
        'ru': 'ℹ️ <b>В базе пока не найдено объявлений по данным параметрам:</b>\n🚙 <b>{make_model}</b>\n\n<i>Европейский сканер работает 24/7. Как только появится подходящее объявление, оно сразу придет сюда!</i>'
    },
    'fetch_sending': {
        'en': '✅ <b>Sending {count} most recent matching listings from database:</b>',
        'pl': '✅ <b>Wysyłanie {count} najnowszych pasujących ogłoszeń z bazy:</b>',
        'ru': '✅ <b>Отправка {count} последних найденных объявлений из базы:</b>'
    },
    'fetch_card': {
        'en': '🚗 <b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Source:</b> {country} ({platform})\n• <b>Year:</b> {year} | <b>Mileage:</b> {mileage}\n• <b>Price:</b> <b>{price:,.0f} €</b>\n━━━━━━━━━━━━━━━━━━━━━\n🔗 <a href="{url}">Original Listing</a>',
        'pl': '🚗 <b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Źródło:</b> {country} ({platform})\n• <b>Rok:</b> {year} | <b>Przebieg:</b> {mileage}\n• <b>Cena:</b> <b>{price:,.0f} €</b>\n━━━━━━━━━━━━━━━━━━━━━\n🔗 <a href="{url}">Oryginalne Ogłoszenie</a>',
        'ru': '🚗 <b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━━\n• <b>Источник:</b> {country} ({platform})\n• <b>Год:</b> {year} | <b>Пробег:</b> {mileage}\n• <b>Цена:</b> <b>{price:,.0f} €</b>\n━━━━━━━━━━━━━━━━━━━━━\n🔗 <a href="{url}">Оригинальное Объявление</a>'
    },
    'btn_view_listing': {
        'en': '🔗 View Listing',
        'pl': '🔗 Zobacz Ogłoszenie',
        'ru': '🔗 Посмотреть Объявление'
    },
    'flim_unlimited': {
        'en': '♾️ Unlimited',
        'pl': '♾️ Bez limitu',
        'ru': '♾️ Без лимита'
    },
    'flim_per_day': {
        'en': '{n} listings / day',
        'pl': '{n} ogłoszeń / dzień',
        'ru': '{n} объявл. / день'
    },
    'fage_realtime': {
        'en': '⚡ Real-Time (Live only)',
        'pl': '⚡ Na żywo (Tylko nowe)',
        'ru': '⚡ Real-Time (Только новые)'
    },
    'fage_1h': {
        'en': '⏱️ Last 1 Hour',
        'pl': '⏱️ Ostatnia 1 godzina',
        'ru': '⏱️ За последний 1 час'
    },
    'fage_24h': {
        'en': '📅 Last 24 Hours',
        'pl': '📅 Ostatnie 24 godziny',
        'ru': '📅 За последние 24 часа'
    },
    'fage_7d': {
        'en': '🗓️ Last 7 Days',
        'pl': '🗓️ Ostatnie 7 dni',
        'ru': '🗓️ За последние 7 дней'
    },
    'fage_30d': {
        'en': '🗓️ Last 30 Days',
        'pl': '🗓️ Ostatnie 30 dni',
        'ru': '🗓️ За последние 30 дней'
    },
    'fage_all': {
        'en': '🌐 All Available',
        'pl': '🌐 Wszystkie dostępne',
        'ru': '🌐 Все доступные'
    },
    'choose_min_pct': {
        'en': '📈 <b>Select Minimum Profit Percentage:</b>\nOnly receive listings where estimated net profit margin is at least this percentage:',
        'pl': '📈 <b>Wybierz Minimalny Procent Zysku:</b>\nTylko oferty, w których marża zysku netto wynosi co najmniej ten procent:',
        'ru': '📈 <b>Выберите Минимальный Процент Прибыли:</b>\nТолько объявления с чистой прибылью не ниже этого процента:'
    },
    'hd_pct_updated': {
        'en': '✅ Profit percentage updated!',
        'pl': '✅ Procent zysku zaktualizowany!',
        'ru': '✅ Процент прибыли обновлен!'
    },
    'choose_deal_type': {
        'en': '🎯 <b>Select Hot Deals Focus Category:</b>\nWhich type of deals would you prefer?',
        'pl': '🎯 <b>Wybierz Kategorię Hot Deals:</b>\nJaki rodzaj okazji preferujesz?',
        'ru': '🎯 <b>Выберите Категорию Hot Deals:</b>\nКаким предложениям вы отдаете предпочтение?'
    },
    'hd_type_updated': {
        'en': '✅ Category updated!',
        'pl': '✅ Kategoria zaktualizowana!',
        'ru': '✅ Категория обновлена!'
    },
    'choose_max_mileage': {
        'en': '🧭 <b>Select Maximum Mileage:</b>\nCars exceeding this mileage will be excluded from Hot Deals:',
        'pl': '🧭 <b>Wybierz Maksymalny Przebieg:</b>\nSamochody z większym przebiegiem zostaną wykluczone z Hot Deals:',
        'ru': '🧭 <b>Выберите Максимальный Пробег:</b>\nАвтомобили с большим пробегом будут исключены из Hot Deals:'
    },
    'hd_mileage_updated': {
        'en': '✅ Mileage limit updated!',
        'pl': '✅ Limit przebiegu zaktualizowany!',
        'ru': '✅ Лимит пробега обновлен!'
    },
    'group_connected_chat': {
        'en': '✅ <b>Your group was connected successfully!</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 <b>Group:</b> {title}\n👤 <b>Owner ID:</b> <code>{user_id}</code>\n\nDedicated topics will now be automatically created in this group for each of your searches.',
        'pl': '✅ <b>Twoja grupa została pomyślnie połączona!</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 <b>Grupa:</b> {title}\n👤 <b>ID Właściciela:</b> <code>{user_id}</code>\n\nDla każdego z Twoich wyszukiwań w tej grupie będą automatycznie tworzone osobne wątki.',
        'ru': '✅ <b>Ваша группа успешно подключена!</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 <b>Группа:</b> {title}\n👤 <b>ID Владельца:</b> <code>{user_id}</code>\n\nТеперь для каждого поиска в этой группе будут автоматически создаваться отдельные темы.'
    },
    'group_connected_user': {
        'en': '🎉 <b>Your Personal Group Connected!</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 <b>Group:</b> {title}\n🔔 <b>Notification Channel:</b> Group (Topics) 👥\n\nDedicated forum topics will be automatically created in your group for future searches.\nYou can switch back to Private Chat anytime in Settings.',
        'pl': '🎉 <b>Twoja prywatna grupa została połączona!</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 <b>Grupa:</b> {title}\n🔔 <b>Miejsce powiadomień:</b> Grupa (Wątki) 👥\n\nDla przyszłych wyszukiwań w Twojej grupie automatycznie powstaną dedykowane wątki.\nW każdej chwili możesz wrócić do Czatu Prywatnego w Ustawieniach.',
        'ru': '🎉 <b>Ваша личная группа подключена!</b>\n━━━━━━━━━━━━━━━━━━━━━\n👥 <b>Группа:</b> {title}\n🔔 <b>Куда отправлять:</b> Группа (Темы) 👥\n\nДля будущих поисков в вашей группе будут автоматически создаваться темы.\nВы можете вернуться к личному чату в любой момент в Настройках.'
    },
    'group_default_title': {
        'en': 'Personal Group',
        'pl': 'Prywatna Grupa',
        'ru': 'Личная Группа'
    },
    'group_only_supergroup_msg': {
        'en': 'ℹ️ This command can only be used inside a Telegram supergroup.',
        'pl': 'ℹ️ Ta komenda może być używana tylko wewnątrz supergrupy Telegram.',
        'ru': 'ℹ️ Эта команда может быть использована только внутри супергруппы Telegram.'
    },
    'validate_not_forum': {
        'en': '⚠️ <b>Forum Topics are disabled in this group.</b>\n\nPlease go to Group Settings, enable "Topics", and send <code>/connect</code> again.',
        'pl': '⚠️ <b>Tematy (Topics) są wyłączone w tej grupie.</b>\n\nPrzejdź do Ustawień grupy, włącz "Topics" (Tematy) i wyślij <code>/connect</code> ponownie.',
        'ru': '⚠️ <b>Темы (Topics) отключены в этой группе.</b>\n\nВключите "Темы" в настройках группы и отправьте <code>/connect</code> снова.'
    },
    'validate_not_admin': {
        'en': '⚠️ <b>The bot is not an Administrator in this group.</b>\n\nPlease promote the bot to Administrator and send <code>/connect</code> again.',
        'pl': '⚠️ <b>Bot nie posiada uprawnień Administratora w tej grupie.</b>\n\nNadaj botowi uprawnienia Administratora i wyślij <code>/connect</code> ponownie.',
        'ru': '⚠️ <b>Бот не является Администратором в этой группе.</b>\n\nСделайте бота администратором группы и отправьте <code>/connect</code> снова.'
    },
    'validate_no_manage_topics': {
        'en': '⚠️ <b>The bot lacks permission to create and manage topics.</b>\n\nIn Admin Rights, enable "Manage Topics" and send <code>/connect</code> again.',
        'pl': '⚠️ <b>Bot nie ma uprawnień do zarządzania tematami.</b>\n\nW uprawnieniach administratora włącz "Zarządzanie tematami" i wyślij <code>/connect</code> ponownie.',
        'ru': '⚠️ <b>У бота нет прав на создание и управление темами.</b>\n\nВ правах администратора включите "Управление темами" и отправьте <code>/connect</code> снова.'
    },
    'validate_no_pin': {
        'en': '⚠️ <b>Please grant the "Pin Messages" permission to pin filter details.</b>',
        'pl': '⚠️ <b>Włącz uprawnienie "Przypinanie wiadomości", aby przypinać szczegóły filtra.</b>',
        'ru': '⚠️ <b>Включите право "Закрепление сообщений", чтобы закреплять параметры фильтра.</b>'
    },
    'validate_error': {
        'en': '⚠️ Error validating group: {e}',
        'pl': '⚠️ Błąd podczas weryfikacji grupy: {e}',
        'ru': '⚠️ Ошибка при проверке группы: {e}'
    }
}

_CUSTOM_BUTTON_LABELS: Dict[str, Dict[str, str]] = {}

def set_custom_button_labels(labels: Dict[str, Dict[str, str]]):
    global _CUSTOM_BUTTON_LABELS
    _CUSTOM_BUTTON_LABELS = dict(labels)

def get_custom_button_label(key: str, lang: Optional[str] = 'en') -> Optional[str]:
    sub = _CUSTOM_BUTTON_LABELS.get(key)
    if sub:
        return sub.get(lang or 'en') or sub.get('en')
    return None

def t(key: str, lang: Optional[str] = 'en', **kwargs) -> str:
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
    text_template = sub_dict.get(normalized_lang) or sub_dict.get('en') or key
    if kwargs:
        try:
            return text_template.format(**kwargs)
        except Exception:
            return text_template
    return text_template

def get_text(key: str, lang: Optional[str] = 'en', **kwargs) -> str:
    return t(key, lang, **kwargs)

def get_option_label(category: str, value: str, lang: Optional[str] = 'en') -> str:
    normalized_lang = (lang or 'en').lower()
    if normalized_lang not in LANGUAGES:
        normalized_lang = 'en'
    cat = OPTIONS_MAP.get(category, {})
    val_map = cat.get(str(value).lower()) or cat.get(str(value).upper())
    if val_map:
        return val_map.get(normalized_lang) or val_map.get('en') or str(value)
    return str(value)
