"""Cálculo puro da divisão BRL. Não cria cobranças nem transferências Stripe.

Valores em centavos, extraídos das condições NEGOCIADAS e persistidas na
campanha, nunca porcentagens fixas. Só executar repasses após verificar o
PaymentIntent e a confirmação do pagamento no Stripe.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PixSplit:
    gross_cents: int
    discount_cents: int
    paid_cents: int
    rrclub_gross_cents: int
    stripe_fee_cents: int
    rrclub_net_cents: int
    influencer_cents: int
    partner_cents: int


def calculate_pix_split(
    *,
    gross_cents: int,
    discount_cents: int,
    rrclub_cents: int,
    influencer_cents: int,
    stripe_fee_cents: int = 0,
    negotiated_partner_cents: int | None = None,
) -> PixSplit:
    """Calcula os valores SEM pagar. Todos os argumentos são inteiros em centavos.

    A comissão RRClub é bruta e assume a taxa Stripe. As comissões RRClub e
    influenciador devem vir do acordo específico da campanha. A Stripe pode
    cobrar taxas adicionais: conciliar o saldo efetivo antes de transferir.
    """
    inputs = {
        "gross_cents": gross_cents,
        "discount_cents": discount_cents,
        "rrclub_cents": rrclub_cents,
        "influencer_cents": influencer_cents,
        "stripe_fee_cents": stripe_fee_cents,
    }
    if negotiated_partner_cents is not None:
        inputs["negotiated_partner_cents"] = negotiated_partner_cents
    for name, value in inputs.items():
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} deve ser um inteiro não negativo em centavos")

    paid = gross_cents - discount_cents
    if gross_cents <= 0 or paid <= 0:
        raise ValueError("A venda e o valor final devem ser positivos")
    if rrclub_cents + influencer_cents > paid:
        raise ValueError("As comissões superam o valor efetivamente pago")
    if stripe_fee_cents > rrclub_cents:
        raise ValueError("A taxa Stripe supera a comissão bruta da RRClub")

    partner_cents = paid - rrclub_cents - influencer_cents
    if negotiated_partner_cents is not None and negotiated_partner_cents != partner_cents:
        raise ValueError("O repasse negociado ao parceiro não fecha com a divisão")

    return PixSplit(
        gross_cents=gross_cents,
        discount_cents=discount_cents,
        paid_cents=paid,
        rrclub_gross_cents=rrclub_cents,
        stripe_fee_cents=stripe_fee_cents,
        rrclub_net_cents=rrclub_cents - stripe_fee_cents,
        influencer_cents=influencer_cents,
        partner_cents=partner_cents,
    )
