"""Integration test cases for token renewal of active users (#226).

The calls to user-service and the backend are replaced with fakes, see
"Testing adapters against HTTP" in tests/conftest.py.
"""

import base64
import json
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from aiohttp.test_utils import TestClient as _TestClient
from aiohttp_session import Session

from result_service_gui.adapters import UserAdapter
from result_service_gui.adapters.user_adapter import store_token, token_needs_renewal
from result_service_gui.middleware import skip_token_renewal

LIFETIME = 3600
PAGE = "/timing?event_id=1"


def make_token(claims: dict) -> str:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64(claims)}.signature"


def token_at(clock_time: float, name: str) -> str:
    """Return a token issued at clock_time, with `name` to tell tokens apart."""
    return make_token({"username": "tester", "name": name, "exp": clock_time + LIFETIME})


class Clock:
    """Shifts time.time() by `offset` seconds."""

    offset = 0.0


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    real_time = time.time
    clock = Clock()
    monkeypatch.setattr(time, "time", lambda: real_time() + clock.offset)
    return clock


class FakeServices:
    """Fake user-service and backend.

    login_token: token returned by login.
    renew_result: (status, token) returned by renew_token.
    renewed: tokens sent to renew_token.
    page_tokens: tokens the page used against the backend.
    """

    def __init__(self) -> None:
        self.login_token = ""
        self.renew_result: tuple[int, str] = (500, "")
        self.renewed: list[str] = []
        self.page_tokens: list[str] = []


@pytest.fixture
def services(monkeypatch: pytest.MonkeyPatch) -> FakeServices:
    fake = FakeServices()

    async def fake_login(self, username: str, password: str, cookiestorage) -> int:
        store_token(cookiestorage, fake.login_token)
        cookiestorage["name"] = username
        cookiestorage["loggedin"] = True
        return 200

    async def fake_renew_token(self, token: str) -> tuple[int, str]:
        fake.renewed.append(token)
        return fake.renew_result

    async def fake_get_event(user: dict, event_id: str) -> dict:
        # record the token, then stop: the page redirects to the main page
        fake.page_tokens.append(user["token"])
        raise RuntimeError("no backend in this test")

    monkeypatch.setattr(UserAdapter, "login", fake_login)
    monkeypatch.setattr(UserAdapter, "renew_token", fake_renew_token)
    monkeypatch.setattr("result_service_gui.views.timing.get_event", fake_get_event)
    return fake


async def login(client: _TestClient, services: FakeServices, token: str) -> None:
    services.login_token = token
    resp = await client.post(
        "/login", data={"username": "tester", "password": "pw"}, allow_redirects=False
    )
    assert resp.status == 303


async def get_page(client: _TestClient):
    """Get a page that needs login; returns the response."""
    return await client.get(PAGE, allow_redirects=False)


def sent_to_login(resp) -> bool:
    return resp.status == 303 and resp.headers["Location"].startswith("/login")


# --- When to renew ------------------------------------------------------------


@pytest.mark.integration
def test_token_needs_renewal() -> None:
    now = time.time()

    def session(data: dict) -> Session:
        return Session(None, data={"session": data}, new=False)

    token = make_token({"exp": now + LIFETIME})
    assert not token_needs_renewal(session({"token": token, "token_received_at": now}))
    halfway = now - LIFETIME / 2
    token = make_token({"exp": halfway + LIFETIME})
    assert token_needs_renewal(session({"token": token, "token_received_at": halfway}))
    # session from before token_received_at was stored: renew once
    assert token_needs_renewal(session({"token": token}))
    # no exp: nothing to renew
    no_exp = make_token({"username": "a"})
    assert not token_needs_renewal(session({"token": no_exp, "token_received_at": 0}))


@pytest.mark.integration
@pytest.mark.parametrize(
    ("path", "skip"),
    [
        ("/ping", True),
        ("/ready", True),
        ("/login", True),
        ("/logout", True),
        ("/static/styles.css", True),
        ("/files/x.jpg", True),
        ("/", False),
        ("/timing", False),
        ("/loginx", False),
    ],
)
def test_skip_token_renewal(path: str, skip: bool) -> None:
    assert skip_token_renewal(path) is skip


# --- Middleware -----------------------------------------------------------------


@pytest.mark.integration
async def test_no_renewal_before_half_lifetime(
    client: _TestClient, services: FakeServices, clock: Clock
) -> None:
    old = token_at(time.time(), "old")
    await login(client, services, old)
    clock.offset = LIFETIME / 2 - 60
    resp = await get_page(client)
    assert not sent_to_login(resp)
    assert services.renewed == []
    assert services.page_tokens == [old]


@pytest.mark.integration
async def test_renewal_after_half_lifetime(
    client: _TestClient, services: FakeServices, clock: Clock
) -> None:
    old = token_at(time.time(), "old")
    await login(client, services, old)
    clock.offset = LIFETIME / 2 + 60
    new = token_at(time.time(), "new")
    services.renew_result = (200, new)

    resp = await get_page(client)
    assert not sent_to_login(resp)
    assert services.renewed == [old]
    # the page already uses the new token
    assert services.page_tokens == [new]

    # the new token is kept in the session, and is not renewed again yet
    await get_page(client)
    assert services.renewed == [old]
    assert services.page_tokens[-1] == new

    # an active user stays logged in after the first token has expired
    clock.offset = LIFETIME + 600
    resp = await get_page(client)
    assert not sent_to_login(resp)
    assert services.page_tokens[-1] == new


@pytest.mark.integration
async def test_renewal_refused_logs_out(
    client: _TestClient, services: FakeServices, clock: Clock
) -> None:
    await login(client, services, token_at(time.time(), "old"))
    clock.offset = LIFETIME / 2 + 60
    services.renew_result = (401, "")

    resp = await get_page(client)
    assert sent_to_login(resp)
    assert parse_qs(urlsplit(resp.headers["Location"]).query)["next"] == [PAGE]
    assert services.page_tokens == []

    # logged out: the next request goes to login without trying to renew
    resp = await get_page(client)
    assert sent_to_login(resp)
    assert len(services.renewed) == 1


@pytest.mark.integration
@pytest.mark.parametrize("status", [0, 500, 503])
async def test_renewal_error_keeps_token(
    client: _TestClient, services: FakeServices, clock: Clock, status: int
) -> None:
    old = token_at(time.time(), "old")
    await login(client, services, old)
    clock.offset = LIFETIME / 2 + 60
    services.renew_result = (status, "")

    resp = await get_page(client)
    assert not sent_to_login(resp)
    assert services.page_tokens == [old]
    assert len(services.renewed) == 1


@pytest.mark.integration
async def test_expired_token_is_not_renewed(
    client: _TestClient, services: FakeServices, clock: Clock
) -> None:
    """A session without activity still expires with the token."""
    await login(client, services, token_at(time.time(), "old"))
    clock.offset = LIFETIME + 1
    resp = await get_page(client)
    assert sent_to_login(resp)
    assert services.renewed == []


@pytest.mark.integration
@pytest.mark.parametrize("path", ["/ping", "/login"])
async def test_skipped_paths_do_not_renew(
    client: _TestClient, services: FakeServices, clock: Clock, path: str
) -> None:
    await login(client, services, token_at(time.time(), "old"))
    clock.offset = LIFETIME / 2 + 60
    resp = await client.get(path, allow_redirects=False)
    assert resp.status == 200
    assert services.renewed == []


# --- renew_token against a fake user-service ----------------------------------


@pytest.fixture
async def fake_user_service(aiohttp_server, monkeypatch: pytest.MonkeyPatch):
    """Run a fake user-service; set .status and .body for /token/renew."""
    from aiohttp import web

    class State:
        status = 200
        body: object = {"token": "new-token"}
        authorization: list[str] = []

    state = State()

    async def renew(request: web.Request) -> web.Response:
        state.authorization.append(request.headers.get("Authorization", ""))
        return web.json_response(state.body, status=state.status)

    app = web.Application()
    app.router.add_post("/token/renew", renew)
    server = await aiohttp_server(app)
    monkeypatch.setattr(
        "result_service_gui.adapters.user_adapter.USER_SERVICE_URL",
        str(server.make_url("")).rstrip("/"),
    )
    return state


@pytest.mark.integration
async def test_renew_token_ok(fake_user_service) -> None:
    assert await UserAdapter().renew_token("old") == (200, "new-token")
    assert fake_user_service.authorization == ["Bearer old"]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (401, {"detail": "Not authenticated"}, (401, "")),
        (500, {}, (500, "")),
        (200, {"no": "token"}, (0, "")),
        (200, ["token"], (0, "")),
        (200, {"token": 42}, (0, "")),
    ],
)
async def test_renew_token_errors(
    fake_user_service, status: int, body: object, expected: tuple
) -> None:
    fake_user_service.status = status
    fake_user_service.body = body
    assert await UserAdapter().renew_token("old") == expected


@pytest.mark.integration
async def test_renew_token_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "result_service_gui.adapters.user_adapter.USER_SERVICE_URL",
        "http://127.0.0.1:1",
    )
    assert await UserAdapter().renew_token("old") == (0, "")
