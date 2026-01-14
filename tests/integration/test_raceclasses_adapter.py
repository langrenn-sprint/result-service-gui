"""Integration test cases for raceclasses_adapter."""

import os
from http import HTTPStatus

from aioresponses import aioresponses
import pytest

from result_service_gui.services.raceclasses_adapter import RaceclassesAdapter


EVENTS_HOST_SERVER = os.getenv("EVENTS_HOST_SERVER", "localhost")
EVENTS_HOST_PORT = os.getenv("EVENTS_HOST_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENTS_HOST_SERVER}:{EVENTS_HOST_PORT}"


@pytest.mark.integration
async def test_get_raceclass_by_name() -> None:
    """Should return a raceclass when querying by name."""
    event_id = "test-event-id"
    raceclass_name = "M19-20"
    token = "test-token"

    mock_raceclass = {
        "id": "raceclass-1",
        "name": "M19-20",
        "event_id": event_id,
        "order": 1,
    }

    adapter = RaceclassesAdapter()

    with aioresponses() as m:
        m.get(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses?name={raceclass_name}",
            status=HTTPStatus.OK,
            payload=[mock_raceclass],
        )

        result = await adapter.get_raceclass_by_name(token, event_id, raceclass_name)

        assert result == mock_raceclass
        assert result["name"] == raceclass_name
        assert result["event_id"] == event_id


@pytest.mark.integration
async def test_get_raceclass_by_name_not_found() -> None:
    """Should return empty dict when raceclass not found."""
    event_id = "test-event-id"
    raceclass_name = "NonExistent"
    token = "test-token"

    adapter = RaceclassesAdapter()

    with aioresponses() as m:
        m.get(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses?name={raceclass_name}",
            status=HTTPStatus.OK,
            payload=[],
        )

        result = await adapter.get_raceclass_by_name(token, event_id, raceclass_name)

        assert result == {}


@pytest.mark.integration
async def test_get_raceclass_by_name_with_special_characters() -> None:
    """Should handle raceclass names with special characters."""
    event_id = "test-event-id"
    raceclass_name = "M 19-20 åå"
    token = "test-token"

    mock_raceclass = {
        "id": "raceclass-2",
        "name": "M 19-20 åå",
        "event_id": event_id,
        "order": 2,
    }

    adapter = RaceclassesAdapter()

    with aioresponses() as m:
        # URL encoding will be handled by urllib.parse.quote
        m.get(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses?name=M%2019-20%20%C3%A5%C3%A5",
            status=HTTPStatus.OK,
            payload=[mock_raceclass],
        )

        result = await adapter.get_raceclass_by_name(token, event_id, raceclass_name)

        assert result == mock_raceclass
        assert result["name"] == raceclass_name
