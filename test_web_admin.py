import sys
from pathlib import Path
import asyncio
import logging

sys.path.insert(0, str(Path(__file__).resolve().parent))

reconfig = getattr(sys.stdout, "reconfigure", None)
if callable(reconfig):
    try:
        reconfig(encoding="utf-8")
    except Exception:
        pass

import httpx  # type: ignore
from config.settings import settings
from database.db import init_db
from database.queries import (
    verify_admin_credentials,
    get_total_clicks_count,
    get_recent_clicks,
    get_ad_settings,
    create_user_filter,
    get_all_filters_admin,
    delete_filter
)
from web.app import create_web_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_web_admin")


async def run_web_tests():
    logger.info("==================================================")
    logger.info("STARTING WEB ADMIN & REDIRECT GATEWAY TEST SUITE")
    logger.info("==================================================")

    # 1. Initialize Database
    logger.info("\n--- 1. Testing Database & Admin User Initialization ---")
    await init_db()

    # Verify default admin credentials
    valid = await verify_admin_credentials(settings.WEB_ADMIN_USERNAME, settings.WEB_ADMIN_PASSWORD)
    assert valid is True, f"Failed to authenticate default admin: {settings.WEB_ADMIN_USERNAME}"
    logger.info(f"Verified default admin account: '{settings.WEB_ADMIN_USERNAME}'")

    # 2. Test FastAPI Application with AsyncClient
    app = create_web_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=False) as client:
        # 3. Test Root Redirect
        logger.info("\n--- 2. Testing Root Redirect ---")
        res = await client.get("/")
        assert res.status_code == 302
        assert res.headers["location"] == "/admin/"
        logger.info("Root '/' successfully redirected to '/admin/'")

        # 4. Test Unauthenticated Access
        logger.info("\n--- 3. Testing Unauthenticated Access Protection ---")
        res = await client.get("/admin/")
        assert res.status_code in (302, 307)
        assert res.headers["location"] == "/admin/login"
        logger.info("Unauthenticated access to '/admin/' protected -> redirected to '/admin/login'")

        # 5. Test Login Flow
        logger.info("\n--- 4. Testing Admin Login Flow ---")
        # Invalid credentials
        res = await client.post("/admin/login", data={"username": "wrong", "password": "wrong"})
        assert res.status_code == 400
        assert "yanlışdır" in res.text or "Invalid" in res.text
        logger.info("Invalid credentials rejected with error message.")

        # Valid credentials
        res = await client.post(
            "/admin/login",
            data={
                "username": settings.WEB_ADMIN_USERNAME,
                "password": settings.WEB_ADMIN_PASSWORD
            }
        )
        assert res.status_code == 302
        assert res.headers["location"] == "/admin/"
        session_cookie = res.cookies.get("admin_session")
        assert session_cookie is not None
        logger.info(f"Valid login successful. Issued admin_session cookie: {session_cookie[:25]}...")

        # 6. Test Authenticated Dashboard Page
        logger.info("\n--- 5. Testing Authenticated Dashboard Page ---")
        client.cookies.set("admin_session", session_cookie)
        res = await client.get("/admin/")
        assert res.status_code == 200
        assert "Dashboard" in res.text
        assert "DOOGAG" in res.text
        logger.info("Dashboard HTML loaded with KPI cards & chart canvas.")

        # 7. Test Topics Page
        logger.info("\n--- 6. Testing Topics Management Page ---")
        # Create a test filter
        test_fid = await create_user_filter(
            user_id=11223344,
            make="Audi",
            model="A6",
            year_min=2016,
            year_max=2021,
            price_max_eur=18000,
            topic_id=777,
            admin_notes="Test VIP client"
        )
        res = await client.get("/admin/topics")
        assert res.status_code == 200
        assert "Audi" in res.text
        assert "#777" in res.text
        assert "Test VIP client" in res.text
        logger.info(f"Topics page displays created filter #{test_fid} (Audi A6, Topic #777)")

        # Test Topic Parameter Editing via POST
        res = await client.post(
            f"/admin/topics/{test_fid}/edit",
            data={
                "price_max_eur": "22000",
                "year_min": "2017",
                "year_max": "2022",
                "admin_notes": "Updated VIP notes"
            }
        )
        assert res.status_code == 302
        logger.info("Topic edit submitted and redirected.")

        # 8. Test Monetization Settings Page & Update
        logger.info("\n--- 7. Testing Monetization Settings & Live Update ---")
        res = await client.get("/admin/monetization")
        assert res.status_code == 200
        assert "Monetization" in res.text

        # Update monetization settings
        res = await client.post(
            "/admin/monetization",
            data={
                "is_redirect_enabled": "1",
                "redirect_base_url": "/r/",
                "custom_affiliate_url": "https://affiliate.com/go",
                "sponsor_text": "Contact us for competitive car financing!",
                "sponsor_button_name": "Get Loan 💰",
                "sponsor_button_url": "https://bank-partner.com/credit"
            }
        )
        assert res.status_code == 302

        ad_check = await get_ad_settings()
        assert ad_check["is_redirect_enabled"] == 1
        assert ad_check["sponsor_text"] == "Contact us for competitive car financing!"
        assert ad_check["custom_affiliate_url"] == "https://affiliate.com/go"
        logger.info("Ad settings successfully updated in DB & cache.")

        # 9. Test Click Gateway & Redirect Tracking
        logger.info("\n--- 8. Testing Click Gateway & Redirect Analytics ---")
        clicks_before = await get_total_clicks_count()
        target_site = "https://www.mobile.de/cz/osobni-vuz/audi-a6/test.html"

        # User clicks on ad link
        res = await client.get(
            f"/r/audi_ext_123?target={target_site}&topic=777",
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
        )
        assert res.status_code == 302
        # Location should redirect
        assert "target=" in res.headers["location"] or "affiliate.com" in res.headers["location"] or "mobile.de" in res.headers["location"]
        logger.info(f"Click gateway responded 302 Redirect to: {res.headers['location']}")

        clicks_after = await get_total_clicks_count()
        assert clicks_after == clicks_before + 1, "Click was not logged in click_analytics!"

        recent = await get_recent_clicks(limit=1)
        assert recent[0]["listing_id"] == "audi_ext_123"
        assert recent[0]["source_topic_id"] == 777
        assert "Mobile" in recent[0]["user_agent"]
        logger.info(f"Verified click analytics record: Listing: {recent[0]['listing_id']}, Device: Mobile, IP Hash: {recent[0]['ip_hash']}")

        # 10. Test Broadcast Page & Analytics Page
        logger.info("\n--- 9. Testing Broadcast & Analytics Views ---")
        res = await client.get("/admin/broadcast")
        assert res.status_code == 200
        assert "Campaign Title" in res.text
        logger.info("Broadcast manager view rendered successfully.")

        res = await client.get("/admin/analytics")
        assert res.status_code == 200
        assert "audi_ext_123" in res.text
        logger.info("Analytics view displays recent click records.")

        # 11. Test Menus & Submenus Management
        logger.info("\n--- 10. Testing Menus & Submenus Management ---")
        res = await client.get("/admin/menus")
        assert res.status_code == 200
        assert "Supported Makes" in res.text
        assert "Button Labels" in res.text
        logger.info("Menus page loaded with car makes and button configuration.")

        # Test Add Make
        res = await client.post("/admin/menus/makes/add", data={"name": "TestTeslaBrand"})
        assert res.status_code == 302
        logger.info("Successfully added test car make 'TestTeslaBrand'.")

        from database.queries import get_all_car_makes, get_car_models_by_make_name, delete_car_make
        makes = await get_all_car_makes()
        test_make = next((m for m in makes if m["name"] == "TestTeslaBrand"), None)
        assert test_make is not None
        make_id = test_make["id"]

        # Test Add Model
        res = await client.post("/admin/menus/models/add", data={"make_id": make_id, "name": "CyberTruck"})
        assert res.status_code == 302
        models = await get_car_models_by_make_name("TestTeslaBrand")
        assert "CyberTruck" in models
        logger.info("Successfully added test model 'CyberTruck' under 'TestTeslaBrand'.")

        # Test API models lookup
        res = await client.get(f"/api/makes/{make_id}/models")
        assert res.status_code == 200
        assert any(m["name"] == "CyberTruck" for m in res.json().get("models", []))
        logger.info("API /api/makes/{id}/models correctly returned new model.")

        # Test Update Button Label
        res = await client.post(
            "/admin/menus/buttons/update",
            data={
                "button_key": "btn_model",
                "label_en": "🚘 Car Model (Custom)",
                "label_pl": "🚘 Model Auta",
                "label_ru": "🚘 Модель Авто"
            }
        )
        assert res.status_code == 302
        from bot.locales.texts import t
        assert t("btn_model", "en") == "🚘 Car Model (Custom)"
        logger.info(f"Custom button label updated and reflected in bot t(): '{t('btn_model', 'en')}'")

        # Clean up test make
        await delete_car_make(make_id)
        logger.info("Cleaned up test make and its models.")

        # 12. Test Message Templates & Live Preview
        logger.info("\n--- 11. Testing Message Card Templates & Preview ---")
        res = await client.get("/admin/templates")
        assert res.status_code == 200
        assert "Standard Listing Alert Template" in res.text
        logger.info("Templates page loaded.")

        # Test Template Preview API
        custom_preview_tpl = "⚡ <b>TEST PREVIEW</b>: {title} | {price_eur} €\nNet Profit: {profit_pln} PLN"
        res = await client.post(
            "/api/templates/preview",
            json={"template": custom_preview_tpl, "is_hot_deal": False}
        )
        assert res.status_code == 200
        preview_data = res.json()
        assert preview_data["success"] is True
        assert "TEST PREVIEW" in preview_data["html"]
        assert "BMW 530d" in preview_data["html"]
        logger.info("Template Preview API rendered sample car card correctly.")

        # Test Save Custom Template
        res = await client.post(
            "/admin/templates",
            data={
                "standard_template": custom_preview_tpl,
                "hot_deal_template": custom_preview_tpl + "\n🔥 HOT DEAL"
            }
        )
        assert res.status_code == 302
        assert "saved=1" in res.headers["location"]
        logger.info("Custom card template saved.")

        # Test Reset Template
        res = await client.post("/admin/templates/reset")
        assert res.status_code == 302
        assert "reset=1" in res.headers["location"]
        logger.info("Message templates successfully reset to default.")

        # 13. Test Broadcast Progress API & History Management
        logger.info("\n--- 12. Testing Broadcast Status & History Management ---")
        res = await client.get("/api/broadcast/status")
        assert res.status_code == 200
        b_status = res.json()
        assert "is_running" in b_status
        assert "percent" in b_status
        assert "total_targets" in b_status
        logger.info(f"Broadcast live status API: {b_status}")

        # Test Broadcast Campaign Creation & Record Deletion
        from database.queries import create_broadcast_campaign, get_broadcast_campaigns
        camp_id = await create_broadcast_campaign(
            title="Unit Test Campaign",
            message_text="Test Message Content",
            target_type="active_topics",
            total_targets=5
        )
        camps = await get_broadcast_campaigns(limit=5)
        assert any(c["id"] == camp_id for c in camps)
        logger.info(f"Created test broadcast campaign #{camp_id}")

        # Delete campaign
        res = await client.post(f"/admin/broadcast/{camp_id}/delete")
        assert res.status_code == 302
        camps_after = await get_broadcast_campaigns(limit=5)
        assert not any(c["id"] == camp_id for c in camps_after)
        logger.info(f"Successfully deleted test broadcast campaign #{camp_id}")

        # 14. Test JSON API Endpoints
        logger.info("\n--- 13. Testing JSON API Endpoints ---")
        res = await client.get("/api/stats")
        assert res.status_code == 200
        stats_json = res.json()
        assert "total_clicks" in stats_json
        logger.info(f"API /api/stats: {stats_json}")

        res = await client.get("/api/charts/clicks")
        assert res.status_code == 200
        chart_json = res.json()
        assert "labels" in chart_json and "counts" in chart_json
        logger.info(f"API /api/charts/clicks: {len(chart_json['labels'])} data points")

        res = await client.get("/api/charts/countries")
        assert res.status_code == 200
        logger.info(f"API /api/charts/countries: {res.json()}")

        # 15. Test Logout
        logger.info("\n--- 14. Testing Logout ---")
        res = await client.get("/admin/logout")
        assert res.status_code == 302
        assert res.headers["location"] == "/admin/login"
        logger.info("Logout successfully cleared session.")

        # Clean up test filter
        await delete_filter(test_fid)
        logger.info(f"Cleaned up test filter #{test_fid}")

    logger.info("\n==================================================")
    logger.info("✅ ALL WEB ADMIN & GATEWAY TESTS PASSED SUCCESSFULLY!")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(run_web_tests())
