"""RRClub clone never exposes destructive bulk-deletion actions."""
import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1")
os.environ.setdefault("DB_NAME", "clone_guard_test")

import routes_test


@pytest.mark.parametrize("method,body", [
    (routes_test.reset_all, {"confirm": "RESET-ALL"}),
    (routes_test.clear_all_tests, {"confirm": "LIMPAR"}),
])
def test_bulk_deletion_disabled_even_for_admin(method, body):
    with pytest.raises(HTTPException) as err:
        asyncio.run(method(body, {"id": "fake_admin", "role": "admin"}))
    assert err.value.status_code == 403
