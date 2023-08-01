"""Contract test cases for start."""
import logging
from typing import Any

from aiohttp import ClientSession
import pytest


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_events(http_service: Any) -> None:
    """Contract test for get events."""
    url = f"{http_service}"

    session = ClientSession()
    async with session.get(url) as response:
        text = await response.text()
        data = await response.json()
    await session.close()
    logging.info(text)
    logging.info(data)
    assert response.status == 200
    assert text == "OK"
