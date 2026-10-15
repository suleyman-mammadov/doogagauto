import logging
from fastapi import FastAPI, Request  # type: ignore
from fastapi.responses import RedirectResponse  # type: ignore

from web.routes.admin import router as admin_router
from web.routes.redirect import router as redirect_router
from web.routes.api import router as api_router

logger = logging.getLogger(__name__)


def create_web_app() -> FastAPI:
    """Create and configure FastAPI application for Web Admin and Click Gateway."""
    app = FastAPI(
        title="DoogagAuto Web Admin",
        description="Visual Web Dashboard & Click Tracking Gateway for Car Arbitrage",
        docs_url=None,
        redoc_url=None
    )

    from web.auth import NotAuthenticatedException

    # Exception handler for unauthenticated admin access -> redirect cleanly to login
    @app.exception_handler(NotAuthenticatedException)
    async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
        return RedirectResponse(url="/admin/login", status_code=302)

    # Root redirect to /admin/
    @app.get("/")
    async def root_redirect():
        return RedirectResponse(url="/admin/", status_code=302)

    # Bare /admin redirect to /admin/
    @app.get("/admin")
    async def admin_redirect():
        return RedirectResponse(url="/admin/", status_code=302)

    # Include routers
    app.include_router(redirect_router)
    app.include_router(admin_router)
    app.include_router(api_router)

    @app.on_event("startup")
    async def on_startup():
        from web.routes.admin import sync_all_caches
        await sync_all_caches()

    logger.info("FastAPI Web Application initialized successfully.")
    return app
