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
    CsvList,
    Dashboard,
    Live,
    Login,
    Logout,
    Main,
    PhotoFinish,
    Photos,
    PhotosEdit,
    PhotoUpdate,
    Ping,
    PrintLists,
    Resultat,
    ResultatEdit,
    ResultatUpdate,
    Start,
    StartEdit,
    Timing,
    TimingDash,
    TimingInfo,
    VideoEvents
)

load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
PROJECT_ROOT = os.path.join(os.getcwd(), "result_service_gui")
logging.info(f"PROJECT_ROOT: {PROJECT_ROOT}")


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
            web.view("/csv", CsvList),
            web.view("/control", Control),
            web.view("/dashboard", Dashboard),
            web.view("/live", Live),
            web.view("/login", Login),
            web.view("/logout", Logout),
            web.view("/ping", Ping),
            web.view("/photo_finish", PhotoFinish),
            web.view("/photos_edit", PhotosEdit),
            web.view("/photos", Photos),
            web.view("/photo_update", PhotoUpdate),
            web.view("/print_lists", PrintLists),
            web.view("/resultat", Resultat),
            web.view("/resultat_edit", ResultatEdit),
            web.view("/resultat_update", ResultatUpdate),
            web.view("/start", Start),
            web.view("/start_edit", StartEdit),
            web.view("/timing", Timing),
            web.view("/timing_dash", TimingDash),
            web.view("/timing_info", TimingInfo),
            web.view("/video_events", VideoEvents),
        ]
    )
    static_dir = os.path.join(PROJECT_ROOT, "static")
    files_dir = os.path.join(PROJECT_ROOT, "files")
    logging.info(f"static_dir: {static_dir}")
    logging.info(f"files_dir: {files_dir}")

    app.router.add_static("/static/", path=static_dir, name="static")
    app.router.add_static("/files/", path=files_dir, name="files")

    return app
