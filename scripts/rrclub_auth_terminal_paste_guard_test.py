#!/usr/bin/env python3
"""Offline regression for Emergent pasted-shell repair. No external dependencies."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name("rrclub_auth_terminal_paste_guard_20261022.py")
spec = importlib.util.spec_from_file_location("rrclub_auth_guard", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
CORRECT = (Path(__file__).resolve().parents[1] / "backend/routes_auth.py").read_text(encoding="utf-8")
CMD = (
    'cd /app && curl -fsSL --max-time 30 '
    '"https://raw.githubusercontent.com/faellt34/NOVORRCLUB/abc123/scripts/'
    'rrclub_p5_ativar_sem_apagar_20261021.py" -o /tmp/rrclub_p5_release.py '
    '&& python3 /tmp/rrclub_p5_release.py '
    '&& python3 -m compileall -q backend && echo "RRCLUB: PREPARACAO P5 CONCLUIDA"\n'
)


class AuthGuardTest(unittest.TestCase):
    def test_clean_file_is_untouched(self):
        result, state, count = guard.prepare(CORRECT)
        self.assertEqual(result, CORRECT)
        self.assertEqual(count, 0)

    def test_pasted_terminal_at_line_258_preserves_original_google_auth(self):
        lines = CORRECT.splitlines(keepends=True)
        # Existing file is ~209 lines; screenshot has terminal command at line 258.
        spoiled = "".join(lines) + ("\n" * max(0, 257-len(lines))) + CMD
        result, state, count = guard.prepare(spoiled)
        self.assertEqual(count, 1)
        self.assertIn(CORRECT, result)
        self.assertNotIn('curl -fsSL', result)
        self.assertIn('google_link', result)
        self.assertTrue(result.startswith(CORRECT))

    def test_pasted_terminal_first_line_repaired(self):
        result, _, count = guard.prepare(CMD + CORRECT)
        self.assertEqual(count, 1)
        self.assertEqual(result, CORRECT)

    def test_does_not_remove_unrelated_bad_python(self):
        with self.assertRaisesRegex(ValueError, 'não encontrei'):
            guard.prepare(CORRECT + "\nnot valid python !!!\n")

    def test_does_not_overwrite_missing_auth_routes(self):
        reduced = CORRECT.replace("async def google_link", "async def not_google_link")
        with self.assertRaisesRegex(ValueError, 'Autenticação incompleta'):
            guard.prepare(CMD + reduced)

    def test_does_not_remove_comment_or_string_data(self):
        self.assertFalse(guard.known_paste("# " + CMD))
        self.assertFalse(guard.known_paste("text = '" + CMD.strip() + "'\n"))


if __name__ == "__main__":
    unittest.main()
