"""Contrato financeiro: P5 aprovado e Pix cobrado usam os mesmos centavos.

Executar no ambiente backend:
    python -m unittest discover -s tests -p 'test_pix_p5_rounding.py'
"""
import unittest
from decimal import Decimal

from p5_rules import quote_minor
from routes_pix import totals


class PixP5RoundingContract(unittest.TestCase):
    def test_known_half_cent_boundaries(self):
        # Old Pix formula rounded 95% directly and charged one cent more.
        self.assertEqual(totals(Decimal("1.10"), 5, 5), (110, 104, 6))
        self.assertEqual(totals(Decimal("1.30"), 5, 5), (130, 123, 7))

    def test_pix_matches_p5_for_every_cent_from_1_to_50_reais(self):
        for gross_minor in range(100, 5001):
            amount = Decimal(gross_minor) / 100
            p5 = quote_minor(amount, 5, 5, "brl")
            pix_gross, pix_net, pix_creator = totals(amount, 5, 5)
            with self.subTest(gross_minor=gross_minor):
                self.assertEqual(pix_gross, p5["gross_minor"])
                self.assertEqual(pix_net, p5["net_minor"])
                self.assertGreaterEqual(pix_creator, 0)
                self.assertLessEqual(pix_creator, pix_net)

    def test_upper_bound(self):
        gross, net, fee = totals(Decimal("10000"), 5, 5)
        self.assertEqual((gross, net, fee), (1000000, 950000, 50000))


if __name__ == "__main__":
    unittest.main()
