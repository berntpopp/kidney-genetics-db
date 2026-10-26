"""The broken POST /api/staging/normalization/test endpoint is gone (#368)."""

import pytest

from app.main import app


@pytest.mark.unit
def test_normalization_test_route_is_removed():
    assert "/api/staging/normalization/test" not in app.openapi()["paths"]
