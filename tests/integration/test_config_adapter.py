"""Integration test cases for reading and saving settings (#236).

Reading a setting must not write: only admin may save settings in
photo-service, so a write while reading gives other users 403. A setting that
is not saved for the event gives the default from global_settings.json.
Saving a setting that is not saved yet creates it with the new value.

aioresponses does not work with the aiohttp version used here, so the
adapter talks to a fake photo-service.
"""

import json
from pathlib import Path

import pytest
from aiohttp import web

from result_service_gui.adapters import ConfigAdapter

EVENT_ID = "e1"
DEFAULTS = json.loads(
    Path("result_service_gui/config/global_settings.json").read_text()
)


class FakePhotoService:
    """Settings in memory, answering like photo-service."""

    def __init__(self) -> None:
        self.settings: dict[tuple[str, str], str] = {}
        self.writes: list[tuple[str, dict]] = []

    async def get_config(self, request: web.Request) -> web.Response:
        key = (request.query["eventId"], request.query["key"])
        if key not in self.settings:
            return web.json_response({"detail": "not found"}, status=404)
        value = self.settings[key]
        return web.json_response({"event_id": key[0], "key": key[1], "value": value})

    async def create_config(self, request: web.Request) -> web.Response:
        body = await request.json()
        self.writes.append(("POST", body))
        self.settings[(body["event_id"], body["key"])] = body["value"]
        return web.Response(status=201, headers={"Location": "/config/c1"})

    async def update_config(self, request: web.Request) -> web.Response:
        body = await request.json()
        self.writes.append(("PUT", body))
        key = (body["event_id"], body["key"])
        if key not in self.settings:
            return web.json_response({"detail": "not found"}, status=404)
        self.settings[key] = body["value"]
        return web.Response(status=204)


@pytest.fixture
async def photo_service(aiohttp_server, monkeypatch: pytest.MonkeyPatch):
    fake = FakePhotoService()
    app = web.Application()
    app.router.add_get("/config", fake.get_config)
    app.router.add_post("/config", fake.create_config)
    app.router.add_put("/config", fake.update_config)
    server = await aiohttp_server(app)
    monkeypatch.setattr(
        "result_service_gui.adapters.config_adapter.PHOTO_SERVICE_URL",
        str(server.make_url("")).rstrip("/"),
    )
    return fake


# --- Reading ---------------------------------------------------------------------


@pytest.mark.integration
async def test_get_saved_setting(photo_service: FakePhotoService) -> None:
    photo_service.settings[(EVENT_ID, "RACE_DURATION_ESTIMATE")] = "123"
    assert await ConfigAdapter().get_config(
        "t", EVENT_ID, "RACE_DURATION_ESTIMATE"
    ) == ("123")
    assert photo_service.writes == []


@pytest.mark.integration
async def test_get_missing_setting_gives_default_without_saving(
    photo_service: FakePhotoService,
) -> None:
    """A setting that is not saved gives the default, and is not saved."""
    adapter = ConfigAdapter()
    assert (
        await adapter.get_config("t", EVENT_ID, "VIDEO_STORAGE_MODE")
        == (DEFAULTS["VIDEO_STORAGE_MODE"])
    )
    assert await adapter.get_config_int("t", EVENT_ID, "RACE_DURATION_ESTIMATE") == (
        int(DEFAULTS["RACE_DURATION_ESTIMATE"])
    )
    assert photo_service.writes == []
    assert photo_service.settings == {}


@pytest.mark.integration
async def test_get_unknown_setting(photo_service: FakePhotoService) -> None:
    with pytest.raises(web.HTTPBadRequest) as e:
        await ConfigAdapter().get_config("t", EVENT_ID, "NO_SUCH_SETTING")
    assert "NO_SUCH_SETTING not found" in e.value.reason
    assert photo_service.writes == []


# --- Saving ----------------------------------------------------------------------


@pytest.mark.integration
async def test_update_saved_setting(photo_service: FakePhotoService) -> None:
    photo_service.settings[(EVENT_ID, "INTEGRATION_SERVICE_START")] = "False"
    result = await ConfigAdapter().update_config(
        "t", EVENT_ID, "INTEGRATION_SERVICE_START", "True"
    )
    assert result == "204"
    assert photo_service.settings[(EVENT_ID, "INTEGRATION_SERVICE_START")] == "True"
    assert [method for method, _ in photo_service.writes] == ["PUT"]


@pytest.mark.integration
async def test_update_missing_setting_saves_the_new_value(
    photo_service: FakePhotoService,
) -> None:
    """The first save of a setting stores the new value, not the default."""
    new_value = f"not-the-default-{DEFAULTS['VIDEO_STORAGE_MODE']}"
    result = await ConfigAdapter().update_config(
        "t", EVENT_ID, "VIDEO_STORAGE_MODE", new_value
    )
    assert result == "201"
    assert photo_service.settings == {(EVENT_ID, "VIDEO_STORAGE_MODE"): new_value}
    assert await ConfigAdapter().get_config("t", EVENT_ID, "VIDEO_STORAGE_MODE") == (
        new_value
    )


@pytest.mark.integration
async def test_update_unknown_setting(photo_service: FakePhotoService) -> None:
    with pytest.raises(web.HTTPBadRequest) as e:
        await ConfigAdapter().update_config("t", EVENT_ID, "NO_SUCH_SETTING", "x")
    assert "NO_SUCH_SETTING not found" in e.value.reason
    assert [method for method, _ in photo_service.writes] == ["PUT"]
    assert photo_service.settings == {}
