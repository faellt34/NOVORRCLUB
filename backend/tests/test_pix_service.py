import asyncio
import os
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
os.environ.setdefault('MONGO_URL','mongodb://localhost:27017')
os.environ.setdefault('DB_NAME','rrclub_test')
os.environ.setdefault('JWT_SECRET','test-only-key-with-at-least-32-characters')
import routes_pix as pix

KEY='12345678-1234-4234-8234-123456789abc'
def run(c): return asyncio.run(c)
def matches(doc,q):
    for k,v in q.items():
        if k=='$or':
            if not any(matches(doc,x) for x in v): return False
        elif isinstance(v,dict):
            if '$lt' in v and not (k in doc and doc[k]<v['$lt']): return False
            if '$exists' in v and (k in doc)!=v['$exists']: return False
            if '$ne' in v and doc.get(k)==v['$ne']: return False
        elif doc.get(k)!=v: return False
    return True
class Collection:
    def __init__(self,items=()): self.items=deepcopy(list(items))
    async def find_one(self,q,*a): return next((deepcopy(d) for d in self.items if matches(d,q)),None)
    async def insert_one(self,d): self.items.append(deepcopy(d))
    async def update_one(self,q,u,upsert=False):
        item=next((d for d in self.items if matches(d,q)),None)
        if item is None and upsert:
            item={k:v for k,v in q.items() if not isinstance(v,dict)};self.items.append(item);item.update(deepcopy(u.get('$setOnInsert',{})))
        if item is not None:
            item.update(deepcopy(u.get('$set',{})))
            for key,value in u.get('$max',{}).items():item[key]=max(item.get(key,0),value)
    async def find_one_and_update(self,q,u):
        old=await self.find_one(q)
        await self.update_one(q,u)
        return old
@pytest.fixture
def env(monkeypatch):
    db=SimpleNamespace(campaigns=Collection([{'id':'c','cupom':'TEST','nome':'Camp','status':'Ativa','desconto':5,'comissao':5,'parceiro_id':'p','influencer_id':'i','currency':'brl'}]),partners=Collection([{'id':'p','nome':'Rest','currency':'brl','pix_stripe_account_id':'acct','pix_stripe_charges_enabled':True,'pix_stripe_payouts_enabled':True}]),influencers=Collection([{'id':'i','nome':'Creator','pix_stripe_account_id':'acct_inf'}]),payment_transactions=Collection(),redemptions=Collection())
    monkeypatch.setattr(pix,'db',db)
    monkeypatch.setenv('PIX_STRIPE_SECRET_KEY','sk_test_pix_br');monkeypatch.setenv('PIX_STRIPE_PLATFORM_COUNTRY','BR')
    monkeypatch.setenv('PIX_STRIPE_WEBHOOK_SECRET','whsec_test')
    monkeypatch.setenv('PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION','pmc_pix_only')
    client=MagicMock()
    monkeypatch.setattr(pix.stripe,'StripeClient',Mock(return_value=client))
    client.v1.accounts.retrieve_current.return_value={'country':'BR','default_currency':'brl','charges_enabled':True,'capabilities':{'pix_payments':'active'}}
    client.v1.payment_method_configurations.retrieve.return_value={'active':True,'livemode':False,'pix':{'available':True,'display_preference':{'value':'on'}}}
    client.v1.accounts.retrieve.return_value={'country':'BR','payouts_enabled':True,'capabilities':{'transfers':'active'}}
    client.v1.payment_intents.retrieve.return_value={'latest_charge':'ch_pix','status':'succeeded','currency':'brl','amount_received':9500}
    client.v1.transfers.create.side_effect=lambda **kw:{'id':'tr_'+kw['params']['destination']}
    client.v1.transfers.retrieve.return_value={'amount_reversed':0}
    client.v1.transfers.reversals.create.return_value={'id':'trr_pix'}
    monkeypatch.setenv('PIX_ENABLED','true');monkeypatch.setenv('PAYMENT_ALLOWED_ORIGINS','https://rrclub.online')
    class Session(dict):
        def __getattr__(self,name):return self[name]
    create=client.v1.checkout.sessions.create
    create.return_value=Session(id='cs_pix',url='https://checkout.stripe.com/pix',payment_method_types=['pix'])
    import routes_data
    converted=AsyncMock();monkeypatch.setattr(routes_data,'mark_converted',converted)
    return db,create,converted

def body(**kw):return pix.PixCheckoutIn(**dict(code='TEST',amount=100,origin_url='https://rrclub.online',request_id=KEY,**kw))
def paid():return {'id':'cs_pix','currency':'brl','amount_total':9500,'payment_status':'paid','payment_intent':'pi_pix','metadata':{'kind':'pix_coupon','request_id':KEY}}
def test_checkout_exact_and_retry(env):
    db,create,_=env
    first=run(pix.partner_checkout(body(),{'partner_id':'p'}));second=run(pix.partner_checkout(body(),{'partner_id':'p'}))
    assert first==second and len(db.payment_transactions.items)==1 and create.call_count==1
    args=create.call_args.kwargs['params']
    assert create.call_args.kwargs['options']['idempotency_key']=='pix-'+KEY
    assert 'payment_method_types' not in args
    assert args['payment_method_configuration']=='pmc_pix_only'
    assert args['line_items'][0]['price_data']['unit_amount']==9500
    assert 'application_fee_amount' not in args['payment_intent_data']
    assert 'transfer_data' not in args['payment_intent_data']
    assert args['payment_intent_data']['transfer_group']=='pix-'+KEY
    assert pix.stripe.StripeClient.call_args.args == ('sk_test_pix_br',)
    assert args['payment_method_options']['pix']['amount_includes_iof']=='always'
def test_timeout_reuses_preinserted_intent(env):
    db,create,_=env
    create.side_effect=pix.stripe.error.APIConnectionError('timeout')
    with pytest.raises(HTTPException):run(pix.partner_checkout(body(),{'partner_id':'p'}))
    assert len(db.payment_transactions.items)==1
    create.side_effect=None
    run(pix.partner_checkout(body(),{'partner_id':'p'}))
    assert create.call_args_list[0].kwargs['options']['idempotency_key']==create.call_args_list[1].kwargs['options']['idempotency_key']
def test_changed_request_rejected(env):
    run(pix.partner_checkout(body(),{'partner_id':'p'}))
    b=body();b.amount=101
    with pytest.raises(HTTPException) as e:run(pix.partner_checkout(b,{'partner_id':'p'}))
    assert e.value.status_code==409

def test_paid_snapshot_and_duplicate(env):
    db,_,converted=env;run(pix.partner_checkout(body(),{'partner_id':'p'}))
    db.campaigns.items[0]['influencer_id']='other'
    event={'type':'checkout.session.completed','data':{'object':paid()}}
    assert run(pix.handle_pix_event(event));assert run(pix.handle_pix_event(event))
    assert len(db.redemptions.items)==1
    assert db.redemptions.items[0]['influencer_id']=='i'
    assert converted.call_count==1
    assert db.payment_transactions.items[0]['payment_status']=='paid'
@pytest.mark.parametrize('field,value',[('currency','eur'),('amount_total',1)])
def test_mismatch_not_paid(env,field,value):
    db,_,_=env;run(pix.partner_checkout(body(),{'partner_id':'p'}));obj=paid();obj[field]=value
    with pytest.raises(HTTPException):run(pix.settle(db.payment_transactions.items[0],obj))
    assert not db.redemptions.items

def test_refund_partial_full_and_stale(env,monkeypatch):
    import realtime
    monkeypatch.setattr(realtime,'emit',Mock())
    db,_,_=env;run(pix.partner_checkout(body(),{'partner_id':'p'}));run(pix.settle(db.payment_transactions.items[0],paid()))
    tx=db.payment_transactions.items[0]
    run(pix.refund(tx,{'currency':'brl','amount':9500,'amount_refunded':4750}))
    assert db.redemptions.items[1]['amount']==-50
    assert db.redemptions.items[1]['commission']==-2.5
    for amount in (4750,4750,9500,4750):
        run(pix.refund(tx,{'currency':'brl','amount':9500,'amount_refunded':amount}))
    assert len(db.redemptions.items)==2
    refund=db.redemptions.items[1]
    assert refund['amount']==-100 and refund['discount']==-5 and refund['commission']==-5
    assert db.payment_transactions.items[0]['refunded_cents']==9500

def test_failed_conversion_retried(env):
    db,_,converted=env;run(pix.partner_checkout(body(),{'partner_id':'p'}));converted.side_effect=RuntimeError('db failure')
    with pytest.raises(RuntimeError):run(pix.settle(db.payment_transactions.items[0],paid()))
    converted.side_effect=None
    run(pix.settle(db.payment_transactions.items[0],paid()))
    assert len(db.redemptions.items)==1 and db.payment_transactions.items[0]['conversion_processed']
def test_non_pix_event_untouched(env):
    db,_,_=env
    assert run(pix.handle_pix_event({'type':'checkout.session.completed','data':{'object':{'id':'cs_card','metadata':{}}}})) is False
    assert not db.payment_transactions.items and not db.redemptions.items
@pytest.mark.parametrize('discount,fee',[(99.9,0),(100,1),(90,20)])
def test_invalid_net(discount,fee):
    with pytest.raises(HTTPException):pix.totals(1,discount,fee)
def test_disabled_no_provider_call(env,monkeypatch):
    monkeypatch.setenv('PIX_ENABLED','false')
    with pytest.raises(HTTPException):run(pix.partner_checkout(body(),{'partner_id':'p'}))
    env[1].assert_not_called()

def test_dispute_holds_commission_without_automatic_release(env,monkeypatch):
    import realtime
    monkeypatch.setattr(realtime,'emit',Mock())
    db,_,_=env;run(pix.partner_checkout(body(),{'partner_id':'p'}));run(pix.settle(db.payment_transactions.items[0],paid()))
    event={'type':'charge.dispute.created','data':{'object':{'id':'dp_pix','payment_intent':'pi_pix'}}}
    assert run(pix.handle_pix_event(event))
    assert db.redemptions.items[0]['commission']==0
    event['type']='charge.dispute.closed';event['data']['object']['status']='won'
    run(pix.handle_pix_event(event))
    assert db.payment_transactions.items[0]['dispute_hold'] is True
    run(pix.refund(db.payment_transactions.items[0],{'currency':'brl','amount':9500,'amount_refunded':9500}))
    assert sum(r['commission'] for r in db.redemptions.items)==0

def test_connect_wrong_currency_rejected(env):
    env[0].partners.items[0]['currency']='eur'
    with pytest.raises(HTTPException):run(pix.connect_onboard({'origin_url':'https://rrclub.online'},{'partner_id':'p','email':'p@test.com','nome':'P'}))


def test_public_cannot_create_checkout(env):
    with pytest.raises(HTTPException) as e: run(pix.checkout(body()))
    assert e.value.status_code==403
    assert not env[0].payment_transactions.items
    env[1].assert_not_called()

def test_other_partner_cannot_generate_or_resume(env):
    env[0].partners.items.append({'id':'other','currency':'brl','status':'Ativo'})
    with pytest.raises(HTTPException) as e:run(pix.partner_checkout(body(),{'partner_id':'other'}))
    assert e.value.status_code==403
    run(pix.partner_checkout(body(),{'partner_id':'p'}))
    with pytest.raises(HTTPException):run(pix.partner_checkout(body(),{'partner_id':'other'}))

def test_customer_can_resume_merchant_request(env):
    created=run(pix.partner_checkout(body(),{'partner_id':'p'}))
    result=run(pix.checkout(body()))
    assert result==created
    assert result['customer_url']=='https://rrclub.online/c/TEST?pix_request_id='+KEY
    assert env[1].call_count==1


def test_three_way_transfers_fixed_gross_split(env):
    db,_,_=env;run(pix.partner_checkout(body(),{'partner_id':'p'}));run(pix.settle(db.payment_transactions.items[0],paid()))
    calls=pix.stripe_client().v1.transfers.create.call_args_list
    assert [c.kwargs['params']['amount'] for c in calls]==[8000,500]
    assert all(c.kwargs['params']['source_transaction']=='ch_pix' for c in calls)
    assert db.payment_transactions.items[0]['platform_cents']==1000
    assert db.payment_transactions.items[0]['split_status']=='completed'

def test_split_resumes_after_second_transfer_failure(env):
    db,_,_=env;run(pix.partner_checkout(body(),{'partner_id':'p'}))
    pix.stripe_client().v1.transfers.create.side_effect=[{'id':'tr_partner'},pix.stripe.error.APIConnectionError('timeout')]
    with pytest.raises(HTTPException):run(pix.settle(db.payment_transactions.items[0],paid()))
    assert db.payment_transactions.items[0]['payment_status']=='paid'
    assert db.payment_transactions.items[0]['partner_transfer_id']=='tr_partner'
    pix.stripe_client().v1.transfers.create.side_effect=None;pix.stripe_client().v1.transfers.create.return_value={'id':'tr_inf'}
    run(pix.settle(db.payment_transactions.items[0],paid()))
    assert pix.stripe_client().v1.transfers.create.call_count==3
    assert db.payment_transactions.items[0]['split_status']=='completed'

def test_non_brazil_platform_blocks_checkout(env):
    pix.stripe_client().v1.accounts.retrieve_current.return_value={'country':'PT'}
    with pytest.raises(HTTPException):run(pix.partner_checkout(body(),{'partner_id':'p'}))
    env[1].assert_not_called()

def test_fixed_split_rejects_old_campaign_rates(env):
    env[0].campaigns.items[0]['desconto']=10
    with pytest.raises(HTTPException):run(pix.partner_checkout(body(),{'partner_id':'p'}))
    env[1].assert_not_called()


def test_refund_reversal_failure_blocks_manual_payout(env):
    db,_,_=env;run(pix.partner_checkout(body(),{'partner_id':'p'}));run(pix.settle(db.payment_transactions.items[0],paid()))
    pix.stripe_client().v1.transfers.reversals.create.side_effect=pix.stripe.error.APIConnectionError('timeout')
    with pytest.raises(HTTPException):run(pix.refund(db.payment_transactions.items[0],{'currency':'brl','amount':9500,'amount_refunded':4750}))
    assert db.payment_transactions.items[0]['reversal_status']=='pending'
    assert db.payment_transactions.items[0]['manual_payout_blocked'] is True

def test_no_portuguese_global_key_mutation(env,monkeypatch):
    monkeypatch.setattr(pix.stripe,'api_key','sk_test_portugal')
    run(pix.partner_checkout(body(),{'partner_id':'p'}))
    assert pix.stripe.api_key=='sk_test_portugal'


def test_dispute_before_session_confirmation_holds_split(env,monkeypatch):
    import realtime
    monkeypatch.setattr(realtime,'emit',Mock())
    db,_,_=env;run(pix.partner_checkout(body(),{'partner_id':'p'}))
    pix.stripe_client().v1.payment_intents.retrieve.return_value={'metadata':{'kind':'pix_coupon','request_id':KEY}}
    assert run(pix.handle_pix_event({'type':'charge.dispute.created','data':{'object':{'id':'dp_early','payment_intent':'pi_pix'}}}))
    run(pix.settle(db.payment_transactions.items[0],paid()))
    pix.stripe_client().v1.transfers.create.assert_not_called()
    assert db.payment_transactions.items[0]['split_status']=='held'
    assert db.redemptions.items[0]['commission']==0


def test_readiness_without_keys_is_safe_and_no_network(env,monkeypatch):
    monkeypatch.delenv('PIX_STRIPE_SECRET_KEY',raising=False)
    assert run(pix.availability())=={'configured':False,'enabled':True,'accepting_new_payments':False}
    report=run(pix.readiness({'role':'admin'}))
    assert report['configuration']['api_key'] is False
    assert report['rules']['partner_percent']==80
    pix.stripe.StripeClient.assert_not_called()

def test_missing_webhook_blocks_checkout_without_api(env,monkeypatch):
    monkeypatch.delenv('PIX_STRIPE_WEBHOOK_SECRET',raising=False)
    with pytest.raises(HTTPException):run(pix.partner_checkout(body(),{'partner_id':'p'}))
    pix.stripe.StripeClient.assert_not_called()
    assert not env[0].payment_transactions.items

def test_wrong_platform_blocks_onboarding_before_create(env):
    pix.stripe_client().v1.accounts.retrieve_current.return_value={'country':'PT'}
    with pytest.raises(HTTPException):run(pix.connect_onboard({'origin_url':'https://rrclub.online'},{'partner_id':'p','role':'partner','email':'test@test.com','nome':'P'}))
    pix.stripe_client().v1.accounts.create.assert_not_called()
    assert 'stripe_account_id' not in env[0].partners.items[0]

def test_non_pix_config_session_expired_before_delivery(env):
    env[1].return_value['payment_method_types']=['card','pix']
    with pytest.raises(HTTPException) as e:run(pix.partner_checkout(body(),{'partner_id':'p'}))
    assert e.value.status_code==409
    pix.stripe_client().v1.checkout.sessions.expire.assert_called_once()
    assert 'checkout_url' not in env[0].payment_transactions.items[0]

def test_fixed_split_rounded_cents_residual_platform(env):
    b=body();b.amount=35.35
    run(pix.partner_checkout(b,{'partner_id':'p'}))
    tx=env[0].payment_transactions.items[0]
    assert tx['gross_cents']==3535 and tx['net_cents']==3358
    assert tx['partner_cents']==2828 and tx['influencer_cents']==177
    assert tx['platform_cents']==353
    assert tx['net_cents']==tx['partner_cents']+tx['influencer_cents']+tx['platform_cents']

def test_brazil_onboarding_keeps_portugal_account_separate(env):
    db,_,_=env
    entity=db.influencers.items[0]
    entity.pop('pix_stripe_account_id')
    entity['stripe_account_id']='acct_portugal'
    class Account(dict):
        def __getattr__(self,k):return self[k]
    pix.stripe_client().v1.accounts.create.return_value=Account(id='acct_brazil')
    pix.stripe_client().v1.account_links.create.return_value=Account(url='https://connect.stripe.com/onboard')
    run(pix.connect_onboard({'origin_url':'https://rrclub.online'},{'role':'influencer','influencer_id':'i','email':'i@test.com','nome':'I'}))
    assert entity['stripe_account_id']=='acct_portugal'
    assert entity['pix_stripe_account_id']=='acct_brazil'
    assert pix.stripe_client().v1.accounts.create.call_args.kwargs['params']['business_type']=='individual'
