"""Copiloto: isolamento do parceiro e distinção entre registo e pagamento."""
import unittest

from diretor_parceiros import summarize_partner_transactions, growth_suggestions


def tx(partner_id="p1", **kw):
    data = {
        "partner_id": partner_id, "kind": "pix_coupon", "currency": "brl",
        "split_version": "br-fixed-5-80-5-10-v1", "payment_status": "paid",
        "gross_cents": 10000, "net_cents": 9500,
        "partner_cents": 8000, "influencer_cents": 500, "platform_cents": 1000,
        "split_status": "completed", "partner_transfer_id": "tr_p", "influencer_transfer_id": "tr_i",
        "campaign_id": "camp1", "campaign": "Inverno na Paraíba",
    }
    data.update(kw)
    return data


class PartnerGrowthTests(unittest.TestCase):
    def test_only_authenticated_partner(self):
        result = summarize_partner_transactions([tx(), tx("p2")], "p1", "brl")
        self.assertEqual(result["pagamentos_p5"], 1)
        self.assertEqual(result["valores"]["cobrado"], 95.0)

    def test_no_cross_currency(self):
        result = summarize_partner_transactions([tx(currency="eur")], "p1", "brl")
        self.assertEqual(result["pagamentos_p5"], 0)

    def test_legacy_simulation_and_refund_not_paid(self):
        recs = [tx(kind="coupon_pay"), tx(is_test=True), tx(refunded_cents=300), tx(payment_status="pending")]
        result = summarize_partner_transactions(recs, "p1", "brl")
        self.assertEqual(result["pagamentos_p5"], 0)
        self.assertEqual(result["em_disputa_ou_por_conciliar"], 1)

    def test_partner_due_from_snapshot(self):
        result = summarize_partner_transactions([tx()], "p1", "brl")
        self.assertEqual(result["valores"]["parceiro"], 80.0)
        self.assertEqual(result["valores"]["rrclub"], 10.0)
        self.assertEqual(result["valores"]["influenciador"], 5.0)
        self.assertEqual(result["ticket_medio_cobrado"], 95.0)

    def test_no_fabricated_roi(self):
        report = summarize_partner_transactions([], "p1", "brl")
        ideas = growth_suggestions(report, 3, 2)
        self.assertTrue(any("checkout" in x["passo"].lower() for x in ideas))
        self.assertTrue(all("ROI" not in x["motivo"] for x in ideas))


if __name__ == "__main__":
    unittest.main()
