"""Hermetic safety tests for the local-only auth prefix repair guard."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rrclub_auth_prefix_guard", HERE / "rrclub_auth_prefix_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

SOURCE = (
    "import re\n"
    "from datetime import datetime, timezone, timedelta\n"
    "from typing import Optional, Literal\n"
    "from fastapi import APIRouter\n"
    "router = APIRouter(prefix=\"/auth\")\n"
    "async def login(): pass\n"
    "async def me(): pass\n"
    "async def logout(): pass\n"
)

class AuthPrefixGuardTests(unittest.TestCase):
    def test_good_file_unchanged(self):
        self.assertEqual(guard.repair_candidate(SOURCE), (SOURCE, "already_valid"))

    def test_mangled_json_prefix_only(self):
        broken = 'status":"ok"}{"message":"Robson Club API","status":"ok"}' + SOURCE[len("import re\n"):]
        recovered, status = guard.repair_candidate(broken)
        self.assertEqual(status, "corrupted_json_prefix")
        self.assertEqual(recovered, SOURCE)

    def test_unrelated_invalid_python_is_not_replaced(self):
        with self.assertRaises(RuntimeError):
            guard.repair_candidate("BROKEN HEADER\n" + SOURCE)

    def test_missing_auth_function_refuses_autorepair(self):
        broken = '{"message":"Robson Club API","status":"ok"}' + SOURCE[len("import re\n"):].replace("async def logout(): pass\n", "")
        with self.assertRaises(RuntimeError):
            guard.repair_candidate(broken)

if __name__ == "__main__":
    unittest.main()
