"""Shared test configuration.

Auth is a process-wide cached singleton (``get_settings`` is ``lru_cache``d and
read once at import time in several modules). Individual test files used to set
``ENABLE_AUTH`` at module scope and, in a couple of cases, *pop* it during
teardown. Because pytest imports every test module up front and the settings
cache is shared, that teardown leaked auth state into later files and caused
order-dependent 401 failures.

This autouse fixture makes the whole suite deterministic: before every test we
force ``enable_auth=false`` and clear the settings cache, so each test starts
from the same known-good state regardless of collection or execution order.
Tests that specifically exercise auth construct their own tokens and do not rely
on the gate being enabled.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def _force_auth_disabled():
    """Guarantee a clean, auth-disabled settings cache for every test."""
    from config import get_settings

    previous = os.environ.get("ENABLE_AUTH")
    os.environ["ENABLE_AUTH"] = "false"
    get_settings.cache_clear()

    yield

    if previous is None:
        os.environ.pop("ENABLE_AUTH", None)
    else:
        os.environ["ENABLE_AUTH"] = previous
    get_settings.cache_clear()
