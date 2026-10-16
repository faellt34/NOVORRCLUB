import os
import pytest
from fastapi import HTTPException
os.environ.setdefault('MONGO_URL','mongodb://localhost:27017')
os.environ.setdefault('DB_NAME','rrclub_test')
from payment_policy import currency_query, reporting_currency
from routes_data import totals


def test_reporting_currency_filters_legacy_eur():
    assert currency_query({'partner_id':'p'},'brl') == {'$and':[{'partner_id':'p'},{'currency':'brl'}]}
    assert currency_query({},'eur')['$and'][1]['$or'][1] == {'currency':{'$exists':False}}
    with pytest.raises(HTTPException): reporting_currency('usd')


def test_partial_refund_reduces_money_without_creating_another_sale():
    records=[{'amount':100,'discount':5,'commission':5},{'amount':-50,'discount':-2.5,'commission':-2.5,'is_refund':True}]
    assert totals(records)=={'count':1,'revenue':50,'discounts':2.5,'commission':2.5,'ticket':50}


def test_disputed_commission_is_not_payable():
    assert totals([{'amount':100,'discount':5,'commission':5,'dispute_hold':True}])['commission']==0
