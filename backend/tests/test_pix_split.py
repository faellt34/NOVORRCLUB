"""Testes da regra RRClub: taxas exclusivamente da plataforma."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pix_split import calculate_pix_split


def test_venda_100_desconto_5_split_10_5_80():
    result = calculate_pix_split(
        gross_cents=10000,
        discount_cents=500,
        rrclub_cents=1000,
        influencer_cents=500,
        stripe_fee_cents=200,
        negotiated_partner_cents=8000,
    )
    assert result.paid_cents == 9500
    assert result.partner_cents == 8000
    assert result.influencer_cents == 500
    assert result.rrclub_gross_cents == 1000
    assert result.rrclub_net_cents == 800
    assert result.partner_cents + result.influencer_cents + result.rrclub_gross_cents == result.paid_cents


@pytest.mark.parametrize("values", [
    dict(gross_cents=10000, discount_cents=11000, rrclub_cents=1000, influencer_cents=500),
    dict(gross_cents=10000, discount_cents=500, rrclub_cents=9000, influencer_cents=1000),
    dict(gross_cents=10000, discount_cents=500, rrclub_cents=1000, influencer_cents=500, stripe_fee_cents=1001),
    dict(gross_cents=10000, discount_cents=500, rrclub_cents=1000, influencer_cents=500, negotiated_partner_cents=7999),
    dict(gross_cents=10000, discount_cents=-1, rrclub_cents=1000, influencer_cents=500),
])
def test_bloqueia_divisao_invalida(values):
    with pytest.raises(ValueError):
        calculate_pix_split(**values)


def test_negociacao_variavel_sem_taxa():
    result = calculate_pix_split(gross_cents=4350, discount_cents=350,
                                 rrclub_cents=350, influencer_cents=150)
    assert result.paid_cents == 4000
    assert result.partner_cents == 3500
    assert result.rrclub_net_cents == 350
