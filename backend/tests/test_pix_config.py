"""Run: PYTHONPATH=backend python3 -m unittest backend.tests.test_pix_config"""
import unittest
from pix_config import configuration_status


class PixConfigTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "PIX_ENABLED": "true",
            "PIX_STRIPE_SECRET_KEY": "sk_test_brazil-example",
            "STRIPE_SECRET_KEY": "sk_test_portugal-example",
            "PIX_STRIPE_PLATFORM_COUNTRY": "BR",
            "PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION": "pmc_sample",
            "PIX_STRIPE_WEBHOOK_SECRET": "whsec_sample",
            "PAYMENT_ALLOWED_ORIGINS": "https://rrclub.online",
        }

    def test_valid_local_configuration(self):
        state, checks = configuration_status(self.env)
        self.assertTrue(state["accepting_new_payments"])
        self.assertTrue(all(checks.values()))

    def test_missing_key_fails_closed(self):
        for k in ("PIX_STRIPE_SECRET_KEY", "PIX_STRIPE_WEBHOOK_SECRET",
                  "PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION"):
            with self.subTest(k=k):
                env = dict(self.env, **{k: ""})
                self.assertFalse(configuration_status(env)[0]["accepting_new_payments"])

    def test_brazil_key_must_differ_from_portugal(self):
        env = dict(self.env, STRIPE_SECRET_KEY=self.env["PIX_STRIPE_SECRET_KEY"])
        state, checks = configuration_status(env)
        self.assertFalse(state["configured"])
        self.assertFalse(checks["separate_brazil_key"])

    def test_rejects_http_origin_and_invalid_country(self):
        env = dict(self.env, PAYMENT_ALLOWED_ORIGINS="http://rrclub.online")
        self.assertFalse(configuration_status(env)[0]["configured"])
        env = dict(self.env, PIX_STRIPE_PLATFORM_COUNTRY="PT")
        self.assertFalse(configuration_status(env)[0]["configured"])

    def test_disabled_does_not_claim_accepting(self):
        env = dict(self.env, PIX_ENABLED="false")
        state, _ = configuration_status(env)
        self.assertTrue(state["configured"])
        self.assertFalse(state["accepting_new_payments"])

    def test_bad_key_prefix(self):
        env = dict(self.env, PIX_STRIPE_SECRET_KEY="pk_live_public")
        self.assertFalse(configuration_status(env)[0]["configured"])


if __name__ == "__main__":
    unittest.main()
