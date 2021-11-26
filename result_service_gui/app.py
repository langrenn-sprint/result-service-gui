"""Package for exposing validation endpoint."""
import base64
import logging
import os
import time

from aiohttp import web
import aiohttp_jinja2
from aiohttp_middlewares import cors_middleware, error_middleware
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from dotenv import load_dotenv
import jinja2

from .views import (
    Control,
    Dashboard,
    Events,
    Live,
    Login,
    Logout,
    Main,
    Ping,
    Resultat,
    ResultatHeat,
    Start,
    Timing,
)

load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
PROJECT_ROOT = os.path.join(os.getcwd(), "result_service_gui")
logging.debug(f"PROJECT_ROOT: {PROJECT_ROOT}")


async def handler(request) -> web.Response:
    """Create a session handler."""
    session = await get_session(request)
    last_visit = session["last_visit"] if "last_visit" in session else None
    session["last_visit"] = time.time()
    text = "Last visited: {}".format(last_visit)
    return web.Response(text=text)


async def create_app() -> web.Application:
    """Create an web application."""
    app = web.Application(
        middlewares=[
            cors_middleware(allow_all=True),
            error_middleware(),  # default error handler for whole application
        ]
    )

    # sesson handling - secret_key must be 32 url-safe base64-encoded bytes
    fernet_key = os.getenv("FERNET_KEY", "23EHUWpP_tpleR_RjuX5hxndWqyc0vO-cjNUMSzbjN4=")
    secret_key = base64.urlsafe_b64decode(fernet_key)
    setup(app, EncryptedCookieStorage(secret_key))
    app.router.add_get("/secret", handler)

    # Set up logging
    logging.basicConfig(level=LOGGING_LEVEL)
    # Set up template path
    template_path = os.path.join(PROJECT_ROOT, "templates")
    aiohttp_jinja2.setup(
        app,
        enable_async=True,
        loader=jinja2.FileSystemLoader(template_path),
    )
    logging.debug(f"template_path: {template_path}")

    app.add_routes(
        [
            web.view("/", Main),
            web.view("/control", Control),
            web.view("/dashboard", Dashboard),
            web.view("/events", Events),
            web.view("/live", Live),
            web.view("/login", Login),
            web.view("/logout", Logout),
            web.view("/timing", Timing),
            web.view("/ping", Ping),
            web.view("/resultat", Resultat),
            web.view("/resultat/heat", ResultatHeat),
            web.view("/start", Start),
        ]
    )
    static_dir = os.path.join(PROJECT_ROOT, "static")
    logging.debug(f"static_dir: {static_dir}")

    app.router.add_static("/static/", path=static_dir, name="static")

    return app
