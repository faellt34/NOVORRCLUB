"""Regras de segurança da própria suite de testes e do aplicador do Diretor."""
import ast
from pathlib import Path
import unittest


BACKEND = Path(__file__).resolve().parents[1]


class DirectorTestSafety(unittest.TestCase):
    def test_integrations_are_opt_in_and_local_only(self):
        source = (BACKEND / "tests" / "test_iter27_diretor.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("RRCLUB_RUN_DIRECTOR_INTEGRATION_TESTS", source)
        self.assertIn("RRCLUB_DIRECTOR_INTEGRATION_BASE_URL", source)
        self.assertIn('parsed.hostname not in ("localhost", "127.0.0.1", "::1")', source)
        self.assertNotIn("requests.delete(", source)
        self.assertNotIn('ADMIN = (', source)
        self.assertNotIn('PARTNER = (', source)

    def test_patch_validator_uses_allowlisted_unit_tests(self):
        source = (BACKEND / "routes_diretor.py").read_text(encoding="utf-8")
        ast.parse(source)
        verify_body = source.split("def _verify(files: list) -> dict:", 1)[1].split("@router.post", 1)[0]
        self.assertIn('"-m", "unittest"', verify_body)
        self.assertIn("tests.test_diretor_estrategia", verify_body)
        self.assertNotIn('"-m", "pytest"', verify_body)


if __name__ == "__main__":
    unittest.main()
