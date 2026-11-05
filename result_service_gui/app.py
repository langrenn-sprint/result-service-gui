"""Package for exposing validation endpoint."""

import base64
import binascii
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from dotenv import load_dotenv

from .views import (
    Config,
    Control,
    Corrections,
    CsvList,
    Live,
    Login,
    Logout,
    Main,
    PhotoFinish,
    Photos,
    PhotosEdit,
    PhotoUpdate,
    Ping,
    PrintDash,
    PrintLists,
    Resultat,
    ResultatEditNew,
    ResultatUpdate,
    Start,
    StartEdit,
    TdReport,
    Timing,
    TimingDash,
    TimingInfo,
    VideoEvents,
)

load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
PROJECT_ROOT = f"{Path.cwd()}/result_service_gui"
logging.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
ERROR_FILE = str(os.getenv("ERROR_FILE"))
STATIC_CACHE_MAX_AGE_SECONDS = int(os.getenv("STATIC_CACHE_MAX_AGE_SECONDS", "3600"))

FERNET_KEY_LENGTH = 32
FERNET_KEY_HELP = (
    "Set FERNET_KEY to 32 url-safe base64-encoded bytes, e.g. generated with: "
    "python3 -c 'import base64, os; "
    "print(base64.urlsafe_b64encode(os.urandom(32)).decode())'"
)


def get_session_secret_key() -> bytes:
    """Return the key that encrypts the session cookie, from FERNET_KEY.

    There is no default: a key in the source code would let anyone make a
    valid session cookie. A missing or invalid key stops the app.
    """
    fernet_key = os.getenv("FERNET_KEY", "").strip()
    if not fernet_key:
        msg = f"FERNET_KEY is not set. {FERNET_KEY_HELP}"
        raise RuntimeError(msg)
    try:
        secret_key = base64.urlsafe_b64decode(fernet_key)
    except (binascii.Error, ValueError):
        secret_key = b""
    if len(secret_key) != FERNET_KEY_LENGTH:
        msg = f"FERNET_KEY is not valid. {FERNET_KEY_HELP}"
        raise RuntimeError(msg)
    return secret_key


def get_session_storage() -> EncryptedCookieStorage:
    """Return the session cookie storage.

    max_age is the maximum session length (JWT_MAX_SESSION_SECONDS, same as in
    user-service), so the session survives a browser restart. The cookie is
    only sent over https when SESSION_COOKIE_SECURE is true, which should be
    set when the GUI runs behind https.
    """
    max_age = int(os.getenv("JWT_MAX_SESSION_SECONDS", "86400"))
    secure = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    return EncryptedCookieStorage(
        get_session_secret_key(),
        max_age=max_age,
        secure=secure,
        httponly=True,
        samesite="Lax",
    )


async def add_static_cache_headers(request, response) -> None:
    """Add browser cache headers for static assets.

    This avoids unnecessary image re-downloads on page refresh while keeping
    compatibility with aiohttp versions where add_static() has no max_age arg.
    """
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = (
            f"public, max-age={STATIC_CACHE_MAX_AGE_SECONDS}"
        )


async def handler(request) -> web.Response:
    """Create a session handler."""
    session = await get_session(request)
    text = f"Last visited: {session.get('last_visit', None)}"
    return web.Response(text=text)


async def create_app() -> web.Application:
    """Create an web application."""
    app = web.Application()
    app.on_response_prepare.append(add_static_cache_headers)

    # session handling
    setup(app, get_session_storage())
    app.router.add_get("/secret", handler)

    # Set up logging - errors to separate file
    logging.basicConfig(level=LOGGING_LEVEL)
    logging.getLogger().setLevel(
        LOGGING_LEVEL
    )  # always applies, even if handlers pre-exist
    file_handler = RotatingFileHandler(ERROR_FILE, maxBytes=1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)

    # Set up template path
    template_path = Path(PROJECT_ROOT) / "templates"
    aiohttp_jinja2.setup(
        app,
        enable_async=True,
        loader=jinja2.FileSystemLoader(template_path),
    )
    logging.debug(f"template_path: {template_path}")

    app.add_routes(
        [
            web.view("/", Main),
            web.view("/corrections", Corrections),
            web.view("/config", Config),
            web.view("/control", Control),
            web.view("/csv", CsvList),
            web.view("/live", Live),
            web.view("/login", Login),
            web.view("/logout", Logout),
            web.view("/ping", Ping),
            web.view("/photo_finish", PhotoFinish),
            web.view("/photos_edit", PhotosEdit),
            web.view("/photos", Photos),
            web.view("/photo_update", PhotoUpdate),
            web.view("/print_dash", PrintDash),
            web.view("/print_lists", PrintLists),
            web.view("/resultat", Resultat),
            web.view("/resultat_edit_new", ResultatEditNew),
            web.view("/resultat_update", ResultatUpdate),
            web.view("/start", Start),
            web.view("/start_edit", StartEdit),
            web.view("/td_report", TdReport),
            web.view("/timing", Timing),
            web.view("/timing_dash", TimingDash),
            web.view("/timing_info", TimingInfo),
            web.view("/video_events", VideoEvents),
        ]
    )

    static_dir = Path(PROJECT_ROOT) / "static"
    logging.info(f"static_dir: {static_dir}")
    app.router.add_static("/static/", path=str(static_dir), name="static")

    files_dir = Path(PROJECT_ROOT) / "files"
    logging.info(f"files_dir: {files_dir}")
    app.router.add_static("/files/", path=files_dir, name="files")

    return app
