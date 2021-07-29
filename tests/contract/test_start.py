"""Contract test cases for start."""
from typing import Any

import pytest
import requests


@pytest.mark.contract
def test_start(http_service: Any) -> None:
    """Should return status 200 and html."""
    url = f"{http_service}/start"
    response = requests.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"

    assert len(response.text) > 0
