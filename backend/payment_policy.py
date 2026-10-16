"""Currency-scoped reporting; legacy untagged records are EUR."""
from fastapi import HTTPException, Header


def reporting_currency(x_currency: str = Header(default="eur")):
    if x_currency not in ("eur", "brl"):
        raise HTTPException(400, "Moeda inválida")
    return x_currency


def currency_query(query, currency):
    condition = {"$or": [{"currency": "eur"}, {"currency": {"$exists": False}}]} if currency == "eur" else {"currency": "brl"}
    return {"$and": [query, condition]}
