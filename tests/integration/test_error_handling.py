"""Integration test cases for error handling in the views (#240).

Only a missing or expired login (401) sends the user to the login page. Other
errors send the user to the main page with an understandable message, and the
user is still logged in. If the main page itself fails, an error page is
shown. An event without organiser does not break the pages.
"""

import ast
from http import HTTPStatus
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient as _TestClient
from yarl import URL

from result_service_gui.adapters import EventsAdapter
from result_service_gui.views.utils import (
    LOGIN_AGAIN,
    UNEXPECTED_ERROR,
    error_text,
    is_login_error,
    raise_error,
)

from .test_config_access import EVENT, EVENT_ID, fakes, login, photo_service

__all__ = ["fakes", "photo_service"]  # fixtures used by the tests below

PAGE = f"/start?event_id={EVENT_ID}"


def location(resp) -> tuple[str, dict]:
    url = URL(resp.headers["Location"])
    return url.path, dict(url.query)


@pytest.fixture
def get_event(monkeypatch: pytest.MonkeyPatch):
    """Let get_event on the start page raise the error set in .error."""

    class State:
        error: Exception | None = None

    state = State()

    async def fake_get_event(user: dict, event_id: str) -> dict:
        if state.error:
            raise state.error
        return EVENT

    monkeypatch.setattr("result_service_gui.views.start.get_event", fake_get_event)
    return state


# --- error_text and is_login_error ---------------------------------------------------


@pytest.mark.integration
def test_error_text() -> None:
    # Our own messages and messages from the backend services are shown:
    assert error_text(Exception("Klassen mangler resultater")) == (
        "Det har oppstått en feil: Klassen mangler resultater"
    )
    assert error_text(web.HTTPBadRequest(reason="Error - 404: Not found.")) == (
        "Det har oppstått en feil: Error - 404: Not found."
    )
    # Programming errors are not shown to the user:
    assert error_text(TypeError("'NoneType' object is not subscriptable")) == (
        UNEXPECTED_ERROR
    )
    assert error_text(KeyError("event_id")) == UNEXPECTED_ERROR


@pytest.mark.integration
def test_is_login_error() -> None:
    assert is_login_error(web.HTTPBadRequest(reason="401 Unathorized - get_event"))
    assert is_login_error(Exception("401 Unathorized - get_races"))
    assert is_login_error(Exception("Login expired: <ClientResponse 401>"))
    assert not is_login_error(Exception("Klassen mangler resultater"))
    assert not is_login_error(TypeError("x"))
    assert not is_login_error(web.HTTPBadRequest(reason="Error - 404: race 401"))


@pytest.mark.integration
def test_raise_error_lets_redirects_through() -> None:
    redirect = web.HTTPSeeOther(location="/login?informasjon=Logg+inn")

    class View:
        request = None

    with pytest.raises(web.HTTPSeeOther) as e:
        raise_error(View(), redirect)  # type: ignore[arg-type]
    assert e.value is redirect


# --- A page that fails -------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    ("error", "message"),
    [
        (TypeError("'NoneType' object is not subscriptable"), UNEXPECTED_ERROR),
        (
            Exception("Klassen mangler resultater"),
            "Det har oppstått en feil: Klassen mangler resultater",
        ),
        (
            web.HTTPBadRequest(reason="Error - 404: Race not found."),
            "Det har oppstått en feil: Error - 404: Race not found.",
        ),
    ],
)
async def test_error_sends_to_main_page_with_message(
    client: _TestClient, fakes, get_event, error: Exception, message: str
) -> None:
    """Not to the login page: the user is still logged in."""
    await login(client, "admin")
    get_event.error = error
    resp = await client.get(PAGE, allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    assert location(resp) == ("/", {"informasjon": message})

    # Still logged in:
    resp = await client.get(f"/config?event_id={EVENT_ID}", allow_redirects=False)
    assert resp.status == HTTPStatus.OK


@pytest.mark.integration
@pytest.mark.parametrize(
    "error",
    [
        web.HTTPBadRequest(reason="401 Unathorized - get_event"),
        Exception("Login expired: <ClientResponse 401>"),
    ],
)
async def test_expired_login_sends_to_login_page(
    client: _TestClient, fakes, get_event, error: Exception
) -> None:
    await login(client, "admin")
    get_event.error = error
    resp = await client.get(PAGE, allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    path, query = location(resp)
    assert path == "/login"
    assert query == {"informasjon": LOGIN_AGAIN, "next": PAGE}


# --- The main page -----------------------------------------------------------------------


@pytest.mark.integration
async def test_main_page_error_shows_error_page(
    client: _TestClient, fakes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other pages send errors to the main page, so it does not redirect."""

    async def fail(*_) -> list:
        raise TypeError("'NoneType' object is not subscriptable")

    monkeypatch.setattr(EventsAdapter, "get_all_events", fail)
    await login(client, "admin")
    resp = await client.get("/", allow_redirects=False)
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    text = await resp.text()
    assert UNEXPECTED_ERROR in text
    assert 'href="/logout"' in text


@pytest.mark.integration
async def test_main_page_expired_login_sends_to_login_page(
    client: _TestClient, fakes, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail(*_) -> list:
        raise Exception("401 Unathorized - get_all_events")  # noqa: TRY002

    monkeypatch.setattr(EventsAdapter, "get_all_events", fail)
    await login(client, "admin")
    resp = await client.get("/", allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    assert location(resp)[0] == "/login"


# --- Event without organiser ---------------------------------------------------------------


@pytest.mark.integration
async def test_event_without_organiser(
    client: _TestClient, fakes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """organiser is optional in event-service; the page uses the neutral style."""

    async def event_without_organiser(*_) -> dict:
        return {**EVENT, "organiser": None}

    monkeypatch.setattr(
        "result_service_gui.views.config.get_event", event_without_organiser
    )
    await login(client, "admin")
    resp = await client.get(f"/config?event_id={EVENT_ID}", allow_redirects=False)
    assert resp.status == HTTPStatus.OK
    assert "styles_whitelabel.css" in await resp.text()


# --- Redirects are raised, not returned ------------------------------------------------------


@pytest.mark.integration
def test_no_returned_http_exceptions_in_views() -> None:
    """HTTP exceptions must be raised: returning them is deprecated in aiohttp."""
    returned = [
        f"{path.name}:{node.lineno}"
        for path in sorted(Path("result_service_gui/views").glob("*.py"))
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Call)
        and ast.unparse(node.value.func).startswith("web.HTTP")
    ]
    assert returned == []


# --- Registering results (resultat_edit_new POST) -----------------------------------------


@pytest.fixture
def result_form(monkeypatch: pytest.MonkeyPatch):
    """Let get_event in resultat_edit_new raise the error set in .error."""

    class State:
        error: Exception = TypeError("'NoneType' object is not subscriptable")

    state = State()

    async def fake_get_event(*_) -> dict:
        raise state.error

    monkeypatch.setattr(
        "result_service_gui.views.resultat_edit_new.get_event", fake_get_event
    )
    return state


RESULT_FORM = {
    "event_id": EVENT_ID,
    "klasse": "G11",
    "runde": "Q",
    "race_id": "r1",
    "update_result": "1",
}


@pytest.mark.integration
async def test_result_error_stays_on_the_page(
    client: _TestClient, fakes, result_form
) -> None:
    """Before, any error sent the user to the login page."""
    await login(client, "result-admin")
    resp = await client.post(
        "/resultat_edit_new", data=RESULT_FORM, allow_redirects=False
    )
    assert resp.status == HTTPStatus.SEE_OTHER
    path, query = location(resp)
    assert path == "/resultat_edit_new"
    assert query["event_id"] == EVENT_ID
    assert query["informasjon"] == UNEXPECTED_ERROR


@pytest.mark.integration
async def test_result_expired_login_sends_to_login_page(
    client: _TestClient, fakes, result_form
) -> None:
    result_form.error = web.HTTPBadRequest(reason="401 Unathorized - get_event")
    await login(client, "result-admin")
    resp = await client.post(
        "/resultat_edit_new", data=RESULT_FORM, allow_redirects=False
    )
    assert resp.status == HTTPStatus.SEE_OTHER
    assert location(resp)[0] == "/login"
