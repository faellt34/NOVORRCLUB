import ast
from pathlib import Path
import unittest

SRC=(Path(__file__).resolve().parents[1]/"observability.py").read_text()
tree=ast.parse(SRC)
node=next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=="_expected_user_state")
scope={}
exec(compile(ast.Module(body=[node], type_ignores=[]), "<policy>", "exec"), scope)
f=scope["_expected_user_state"]

class ExpectedUserStates(unittest.TestCase):
    def test_normal_financial_pending_not_incident(self):
        self.assertTrue(f(409,"/api/p5/checkout"))
        self.assertTrue(f(422,"/api/partner/pix/connect/status"))
    def test_security_and_service_errors_remain_visible(self):
        self.assertFalse(f(400,"/api/stripe/webhook"))
        self.assertFalse(f(401,"/api/partner/pix/connect/status"))
        self.assertFalse(f(403,"/api/p5/checkout"))
        self.assertFalse(f(429,"/api/p5/checkout"))
        self.assertFalse(f(500,"/api/p5/checkout"))
        self.assertFalse(f(409,"/api/stripe/pix/webhook"))
    def test_metrics_not_removed(self):
        self.assertIn("db.request_metrics.insert_one",SRC)
        self.assertIn("log.exception",SRC)
        self.assertIn("await record",SRC)

if __name__=="__main__":
    unittest.main()
