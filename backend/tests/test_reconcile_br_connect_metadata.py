import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_br_connect_metadata.py"
spec = importlib.util.spec_from_file_location("reconcile_br_connect_metadata", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

P = module.EXPECTED[0]
I = module.EXPECTED[1]


def stripe_account(expected, metadata=None):
    return {
        "id": expected["stripe_id"], "country": "BR",
        "metadata": metadata or {}, "capabilities": {"transfers": "active"},
        "payouts_enabled": True, "settings": {"payouts": {"schedule": {"interval": "daily"}}},
    }


def local_record(expected):
    return {"id": expected["internal_id"], "pix_stripe_account_id": expected["stripe_id"],
            "currency": "brl", "status": "Ativo"}


class ReconcileMetadataTests(unittest.TestCase):
    def test_valid_pair(self):
        for e in module.EXPECTED:
            self.assertIsNone(module.check_local(local_record(e), e))
            self.assertIsNone(module.check_stripe(stripe_account(e), e))

    def test_wrong_production_link_rejected(self):
        e = P
        self.assertEqual(module.check_local({**local_record(e), "pix_stripe_account_id": "acct_wrong"}, e),
                         "ligacao_producao_diferente_ou_ausente")

    def test_owner_conflict_rejected(self):
        self.assertEqual(module.check_stripe(stripe_account(P, {"partner_id": "other-id"}), P),
                         "conflito_de_titularidade")

    def test_unauthorized_other_role_rejected(self):
        self.assertEqual(module.check_stripe(stripe_account(P, {"influencer_id": "if-other"}), P),
                         "conta_ja_associada_a_outro_papel")

    def test_payout_requirements_enforced(self):
        bad = stripe_account(I)
        bad["settings"]["payouts"]["schedule"]["interval"] = "manual"
        self.assertEqual(module.check_stripe(bad, I), "deposito_automatico_nao_diario")

    def test_no_id_guess(self):
        self.assertEqual(module.check_local(None, P), "cadastro_interno_nao_encontrado")


if __name__ == "__main__":
    unittest.main()
