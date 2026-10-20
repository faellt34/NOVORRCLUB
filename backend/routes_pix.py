"""BR-only Pix: original bill 5% discount, 80% partner, 5% creator, residual platform.
Platform bears processing costs. All provider calls use the separate Brazilian key.
"""
import asyncio
import os
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from urllib.parse import urlsplit

import stripe
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from core import db, NO_ID, now_iso, require_role
from partner_access import partner_record
from payments.pix.checks import platform_checks, configuration_checks, receiving_status, webhook_checks
from payments.stripe_normalize import stripe_payload

router = APIRouter()


class PixCheckoutIn(BaseModel):
    code: str
    amount: float = Field(ge=1, le=10000, allow_inf_nan=False)
    origin_url: str
    request_id: uuid.UUID


def pix_key():
    key=os.getenv('PIX_STRIPE_SECRET_KEY','')
    if not key or os.getenv('PIX_STRIPE_PLATFORM_COUNTRY')!='BR':
        raise HTTPException(503,'Configure a conta Stripe brasileira exclusiva do Pix')
    return key


def stripe_client():
    return stripe.StripeClient(pix_key(), http_client=stripe.RequestsClient(timeout=15), max_network_retries=0)


async def provider(operation,*args,**kwargs):
    client=stripe_client()
    fn=client.v1
    for part in operation.split('.'):
        fn=getattr(fn,part)
    options={}
    if 'idempotency_key' in kwargs:
        options['idempotency_key']=kwargs.pop('idempotency_key')
    try:
        result = await asyncio.wait_for(asyncio.to_thread(fn,*args,params=kwargs,options=options),timeout=30)
        return stripe_payload(result)
    except stripe.error.StripeError as exc:
        import logging
        code = str(getattr(exc, 'code', None) or '')[:48]
        status = getattr(exc, 'http_status', None)
        request_id = str(getattr(exc, 'request_id', None) or '')[:100]
        # Never log API keys, user details, raw provider response or request bodies.
        logging.getLogger(__name__).warning(
            "pix_stripe_api_error operation=%s status=%s code=%s request_id=%s",
            operation, status, code, request_id)
        if operation.startswith(('accounts.create', 'account_links.create')) and status in (400, 403):
            raise HTTPException(409,
                'Stripe Connect Brasil recusou a configuração; reveja os requisitos e responsabilidades no painel Stripe.') from exc
        raise HTTPException(502, 'Operação Pix pendente; repita com a mesma referência.') from exc
    except asyncio.TimeoutError as exc:
        import logging
        logging.getLogger(__name__).warning("pix_stripe_timeout operation=%s", operation)
        raise HTTPException(502, 'A Stripe demorou a responder; repita o mesmo pedido.') from exc


def availability_configuration():
    configuration={
        'api_key':bool(os.getenv('PIX_STRIPE_SECRET_KEY')),
        'platform_country_br':os.getenv('PIX_STRIPE_PLATFORM_COUNTRY')=='BR',
        'webhook':bool(os.getenv('PIX_STRIPE_WEBHOOK_SECRET')),
        'payment_method_configuration':os.getenv('PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION','').startswith('pmc_'),
        'allowed_origins':bool(os.getenv('PAYMENT_ALLOWED_ORIGINS',os.getenv('FRONTEND_URL',''))),
    }
    configured=all(configuration.values())
    enabled=os.getenv('PIX_ENABLED','false').lower()=='true'
    return {'configured':configured,'enabled':enabled,'accepting_new_payments':configured and enabled},configuration


@router.get('/public/pix/availability')
async def availability():
    return availability_configuration()[0]


@router.get('/admin/pix/readiness')
async def readiness(user: dict = Depends(require_role('admin'))):
    state,configuration=availability_configuration()
    return {**state,'configuration':configuration,'rules':{'discount_percent':5,'partner_percent':80,'influencer_percent':5,'platform_percent':10,'processing_costs':'platform'},'external_validation_required':True}


@router.get('/admin/pix/provider-readiness')
async def provider_readiness(user: dict = Depends(require_role('admin'))):
    """Explicit admin diagnostic: Stripe GETs only; never enables Pix or saves secrets."""
    state, configuration = availability_configuration()
    if not state['configured']:
        return {**state, 'provider_verified': False, 'checks': {}, 'missing_configuration':
                [key for key, value in configuration.items() if not value]}
    platform = await provider('accounts.retrieve_current')
    payment_config = await provider('payment_method_configurations.retrieve', os.environ['PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION'])
    checks = {**platform_checks(platform), **configuration_checks(payment_config)}
    endpoints = await provider('webhook_endpoints.list', limit=100)
    origins = [v.strip() for v in os.getenv('PAYMENT_ALLOWED_ORIGINS', os.getenv('FRONTEND_URL', '')).split(',') if v.strip()]
    checks['webhook_registered'] = any(webhook_checks(endpoints.get('data') or [], origin) for origin in origins)
    key = pix_key()
    expected_live = key.startswith(('sk_live_', 'rk_live_'))
    checks['configuration_mode_matches'] = payment_config.get('livemode') is expected_live
    return {**state, 'provider_verified': all(checks.values()), 'checks': checks,
            'platform_country': platform.get('country'), 'settlement_currency': platform.get('default_currency'),
            'livemode': expected_live, 'sandbox_validation_required': True,
            'note': 'Verificação de configuração; não comprova entrega de webhook nem liquidação dos repasses.'}


async def verify_accounts(partner, influencer):
    platform=await provider('accounts.retrieve_current')
    if not all(platform_checks(platform).values()):
        raise HTTPException(409,'Configure a plataforma brasileira com BRL, Pix, cobranças e depósitos bancários automáticos habilitados')
    config=await provider('payment_method_configurations.retrieve', os.environ['PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION'])
    if not all(configuration_checks(config).values()):
        raise HTTPException(409,'Configure um checkout ativo exclusivamente para Pix antes de cobrar')
    if config.get('livemode') is not pix_key().startswith(('sk_live_', 'rk_live_')):
        raise HTTPException(409,'A configuração Pix e a chave Stripe devem pertencer ao mesmo modo')
    destinations = [(entity or {}).get('pix_stripe_account_id') for entity in (partner, influencer)]
    if destinations[0] and destinations[0] == destinations[1]:
        raise HTTPException(409,'Parceiro e influencer precisam de contas de recebimento distintas')
    for entity in (partner,influencer):
        account=(entity or {}).get('pix_stripe_account_id')
        if not account:
            raise HTTPException(409,'Parceiro e influencer devem concluir recebimentos Stripe Connect Brasil')
        info=await provider('accounts.retrieve',account)
        if not receiving_status(info, entity)['receiving_ready']:
            raise HTTPException(409,'Destinatário brasileiro precisa de transferências e depósitos bancários automáticos habilitados')


def totals(amount, discount, commission):
    try:
        a, d, c = [Decimal(str(v)) for v in (amount, discount, commission)]
        if not all(v.is_finite() for v in (a, d, c)) or not 1 <= a <= 10000 or d != 5 or c != 5:
            raise ValueError()
        cents = lambda x: int(x.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        gross = cents(a * 100)
        net, fee = cents(gross * (100-d)/100), cents(gross*c/100)
        if net < 50 or fee > net:
            raise ValueError()
        return gross, net, fee
    except (ValueError, ArithmeticError):
        raise HTTPException(400, 'Valor, desconto ou comissão inválidos; mínimo Pix R$ 0,50 após desconto')


def trusted_origin(value):
    origin = value.rstrip('/')
    allowed = {v.strip().rstrip('/') for v in os.getenv('PAYMENT_ALLOWED_ORIGINS', os.getenv('FRONTEND_URL', '')).split(',') if v.strip()}
    parsed = urlsplit(origin)
    if origin not in allowed or parsed.scheme != 'https' or parsed.path or parsed.query or parsed.fragment:
        raise HTTPException(400, 'Origem de pagamento não autorizada')
    return origin


def public(tx):
    result = {k: tx.get(k) for k in ('request_id','session_id','checkout_url','status','payment_status','currency','coupon','amount','gross_amount','discount','redemption_id','refunded_amount','dispute_hold','split_status','partner_transfer_status','influencer_transfer_status','partner_amount','platform_amount','partner_transfer_id','influencer_transfer_id','reversal_status','manual_payout_blocked')}
    result['customer_url']=tx['origin']+'/c/'+tx['coupon']+'?pix_request_id='+tx['request_id']
    return result


class PixResumeIn(BaseModel):
    request_id: uuid.UUID


@router.post('/public/pix/checkout')
async def checkout(body: PixResumeIn):
    existing=await db.payment_transactions.find_one({'id':'pix-'+str(body.request_id),'kind':'pix_coupon'},NO_ID)
    if not existing:
        raise HTTPException(403,'O parceiro deve conferir a conta e gerar a cobrança Pix na loja')
    saved=PixCheckoutIn(request_id=body.request_id,code=existing['coupon'],amount=float(existing['input_amount']),origin_url=existing['origin'])
    return await _checkout(saved)


@router.post('/partner/pix/checkout')
async def partner_checkout(body: PixCheckoutIn, user: dict = Depends(require_role('partner'))):
    await partner_record(user, db)
    existing=await db.payment_transactions.find_one({'id':'pix-'+str(body.request_id),'kind':'pix_coupon'},NO_ID)
    if existing:
        owner=existing.get('partner_id')
    else:
        campaign=await db.campaigns.find_one({'cupom':body.code.strip().upper()},NO_ID)
        if not campaign:
            raise HTTPException(404,'Cupom inválido')
        owner=campaign.get('parceiro_id')
    if owner != user.get('partner_id'):
        raise HTTPException(403,'Campanha não pertence a este parceiro')
    return await _checkout(body, user.get('partner_id'))


async def _checkout(body: PixCheckoutIn, creating_partner=None):
    if not availability_configuration()[0]['accepting_new_payments']:
        raise HTTPException(503, 'Pix ainda não está ativado nesta instalação')
    origin = trusted_origin(body.origin_url)
    key, code = str(body.request_id), body.code.strip().upper()
    txid = 'pix-' + key
    existing = await db.payment_transactions.find_one({'id': txid}, NO_ID)
    if existing:
        if existing['coupon'] != code or existing['input_amount'] != str(body.amount) or existing['origin'] != origin:
            raise HTTPException(409, 'Pedido de pagamento já utilizado com outros dados')
        tx = existing
    else:
        if not creating_partner:
            raise HTTPException(403,'O parceiro deve gerar esta cobrança Pix')
        campaign = await db.campaigns.find_one({'cupom': code}, NO_ID)
        if not campaign or campaign.get('status') != 'Ativa':
            raise HTTPException(404, 'Cupom inválido ou inativo')
        if campaign.get('validade') and campaign['validade'] < datetime.now(timezone.utc).date().isoformat():
            raise HTTPException(409, 'Cupom fora da validade')
        if campaign.get('parceiro_id') != creating_partner:
            raise HTTPException(403,'Campanha não pertence a este parceiro')
        partner = await db.partners.find_one({'id': campaign.get('parceiro_id')}, NO_ID)
        if not partner or partner.get('currency') != 'brl' or campaign.get('currency', partner.get('currency')) != 'brl':
            raise HTTPException(409, 'Campanha e parceiro devem operar em reais')
        if not all(partner.get(k) for k in ('pix_stripe_account_id',)):
            raise HTTPException(409, 'Parceiro deve concluir a configuração Stripe Connect e recebimentos')
        gross, net, fee = totals(body.amount, campaign['desconto'], campaign['comissao'])
        inf = await db.influencers.find_one({'id': campaign.get('influencer_id')}, NO_ID) if campaign.get('influencer_id') else None
        await verify_accounts(partner,inf)
        partner_cents=int((Decimal(gross)*Decimal('0.80')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        platform_cents=net-partner_cents-fee
        tx = {'id': txid, 'request_id': key, 'session_id': 'pending-'+key, 'kind':'pix_coupon', 'currency':'brl', 'coupon':code,
              'input_amount':str(body.amount), 'origin':origin, 'gross_cents':gross, 'net_cents':net,'fee_cents':fee,
              'partner_cents':partner_cents,'influencer_cents':fee,'platform_cents':platform_cents,'partner_amount':partner_cents/100,'platform_amount':platform_cents/100,'influencer_destination':inf['pix_stripe_account_id'],'split_status':'pending','gross_amount':gross/100,'amount':net/100,'discount':(gross-net)/100,'commission':fee/100,'rate':0.05,'split_version':'br-fixed-5-80-5-10-v1','manual_payout_blocked':True,
              'campaign_id':campaign['id'],'campaign':campaign['nome'],'partner_id':partner['id'],'partner':partner.get('nome',''),
              'influencer_id':campaign.get('influencer_id'),'influencer':(inf or {}).get('nome','—'),'destination':partner['pix_stripe_account_id'],
              'payment_method_configuration':os.environ['PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION'],'status':'initiated','payment_status':'pending','created_at':now_iso(),'updated_at':now_iso()}
        try:
            await db.payment_transactions.insert_one(dict(tx))
        except DuplicateKeyError:
            return await _checkout(body, creating_partner)
    if tx.get('status')=='blocked_payment_configuration':
        raise HTTPException(409,'Configuração Pix inválida; o administrador deve corrigir antes de gerar nova cobrança')
    if tx.get('checkout_url'):
        return public(tx)
    if (datetime.now(timezone.utc)-datetime.fromisoformat(tx['created_at'])).total_seconds() > 23*3600:
        raise HTTPException(409, 'Pedido antigo sem confirmação; consulte o suporte antes de criar outra cobrança')
    try:
        session = await provider('checkout.sessions.create',
            idempotency_key=txid, mode='payment', payment_method_configuration=tx['payment_method_configuration'],
            line_items=[{'price_data':{'currency':'brl','unit_amount':tx['net_cents'],'product_data':{'name':tx['partner']+' · '+tx['campaign']}},'quantity':1}],
            payment_method_options={'pix': {'amount_includes_iof': 'always', 'expires_after_seconds': 600}},
            payment_intent_data={'transfer_group':txid,'metadata':{'kind':'pix_coupon','request_id':key}},
            metadata={'kind':'pix_coupon','request_id':key},
            success_url=origin+'/c/'+code+'?pix_request_id='+key,
            cancel_url=origin+'/c/'+code+'?cancel=1')
    except (stripe.error.StripeError, asyncio.TimeoutError):
        raise HTTPException(502, 'Não foi possível iniciar o Pix; tente novamente com o mesmo pedido')
    if list(session.get('payment_method_types') or []) != ['pix']:
        await provider('checkout.sessions.expire',session.id)
        await db.payment_transactions.update_one({'id':txid},{'$set':{'status':'blocked_payment_configuration'}})
        raise HTTPException(409,'A configuração Stripe deve oferecer exclusivamente Pix; cobrança bloqueada')
    update={'session_id':session.id,'checkout_url':session.url,'updated_at':now_iso()}
    await db.payment_transactions.update_one({'id':txid},{'$set':update})
    tx.update(update)
    return public(tx)


async def settle(tx, obj):
    metadata = obj.get('metadata') or {}
    if metadata.get('kind') != 'pix_coupon' or metadata.get('request_id') != tx['request_id']:
        raise HTTPException(409, 'Confirmação Pix não pertence a este pedido')
    if not tx['session_id'].startswith('pending-') and obj.get('id') != tx['session_id']:
        raise HTTPException(409, 'Sessão Pix não corresponde ao pedido')
    if obj.get('currency') != 'brl' or obj.get('amount_total') != tx['net_cents']:
        raise HTTPException(409, 'Confirmação Pix não corresponde ao valor ou moeda do pedido')
    if obj.get('payment_status') != 'paid':
        return
    recid = 'r-pix-'+tx['request_id']
    rec={k:tx[k] for k in ('coupon','campaign_id','campaign','partner_id','partner','influencer_id','influencer','currency','rate')}
    rec.update(id=recid,amount=tx['gross_amount'],discount=tx['discount'],commission=tx['commission'],date=now_iso(),staff='Pagamento Pix online',paid_online=True,payment_method='pix',automatic_split=True,idempotency_key=tx['id'])
    try:
        await db.redemptions.update_one({'idempotency_key':tx['id']},{'$setOnInsert':rec},upsert=True)
    except DuplicateKeyError:
        if not await db.redemptions.find_one({'idempotency_key':tx['id']},NO_ID):
            raise
    await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'manual_payout_blocked':True,'session_id':obj['id'],'redemption_id':recid,'payment_status':'paid','status':'completed','stripe_payment_intent_id':obj.get('payment_intent'),'updated_at':now_iso()}})
    await execute_split(tx,obj.get('payment_intent'))
    await enforce_dispute_hold(tx)
    if not tx.get('conversion_processed'):
        from routes_data import mark_converted
        await mark_converted(tx['campaign_id'],rec)
        await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'conversion_processed':True}})


async def refund(tx, charge):
    if charge.get('currency') != 'brl' or charge.get('amount') != tx['net_cents']:
        raise HTTPException(409, 'Reembolso Pix não corresponde à cobrança')
    cumulative = charge.get('amount_refunded',0)
    if not isinstance(cumulative,int) or not 0 <= cumulative <= tx['net_cents']:
        raise HTTPException(409,'Valor de reembolso inválido')
    # Retrieve latest provider cumulative total; delayed events must not undo newer refunds.
    await db.payment_transactions.find_one_and_update({'id':tx['id'],'$or':[{'refunded_cents':{'$lt':cumulative}},{'refunded_cents':{'$exists':False}}]}, {'$set':{'refunded_cents':cumulative,'refunded_amount':cumulative/100}})
    latest=await db.payment_transactions.find_one({'id':tx['id']},NO_ID)
    cumulative=max(cumulative,(latest or {}).get('refunded_cents',0))
    # Single negative ledger record per payment, cumulative, so repeated events never double-debit.
    cents=lambda v:int((Decimal(v)*cumulative/tx['net_cents']).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    adjustment={k:tx[k] for k in ('coupon','campaign_id','campaign','partner_id','partner','influencer_id','influencer','currency','rate')}
    adjustment.update(id='refund-'+tx['id'],idempotency_key='refund-'+tx['id'],amount=-cents(tx['gross_cents'])/100,discount=-cents(tx['gross_cents']-tx['net_cents'])/100,commission=-cents(tx['fee_cents'])/100,date=now_iso(),staff='Reembolso Pix',paid_online=True,payment_method='pix',automatic_split=True,is_refund=True)
    if (latest or {}).get('dispute_hold'):
        adjustment['commission']=0
        adjustment['dispute_hold']=True
    if cumulative:
        adjustment['refunded_cents']=cumulative
        try:
            await db.redemptions.update_one({'idempotency_key':adjustment['idempotency_key']},{'$setOnInsert':adjustment},upsert=True)
        except DuplicateKeyError:
            if not await db.redemptions.find_one({'idempotency_key':adjustment['idempotency_key']},NO_ID):
                raise
        await db.redemptions.update_one({'idempotency_key':adjustment['idempotency_key'],'refunded_cents':{'$lt':cumulative}},{'$set':adjustment})
        from realtime import emit
        emit('pagamento_atualizado', currency='brl', partner_id=tx['partner_id'], influencer_id=tx.get('influencer_id'), ref=tx['id'])
    await reverse_split(tx,cumulative)
    await enforce_dispute_hold(tx)


async def enforce_dispute_hold(tx):
    latest=await db.payment_transactions.find_one({'id':tx['id']},NO_ID)
    if latest and latest.get('dispute_hold'):
        for key in (tx['id'],'refund-'+tx['id']):
            await db.redemptions.update_one({'idempotency_key':key},{'$set':{'commission':0,'dispute_hold':True}})


async def transaction_for_intent(intent_id):
    if not intent_id:
        return None
    tx=await db.payment_transactions.find_one({'kind':'pix_coupon','stripe_payment_intent_id':intent_id},NO_ID)
    if tx:
        return tx
    intent=await provider('payment_intents.retrieve',intent_id)
    metadata=intent.get('metadata') or {}
    if metadata.get('kind')!='pix_coupon':
        return None
    tx=await db.payment_transactions.find_one({'kind':'pix_coupon','id':'pix-'+metadata.get('request_id','')},NO_ID)
    if not tx:
        raise HTTPException(503,'Pedido Pix ainda não conciliado; repetir evento')
    await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'stripe_payment_intent_id':intent_id}})
    return tx


async def handle_pix_event(event):
    obj=event['data']['object']; kind=event['type']
    metadata=obj.get('metadata') or {}
    if kind in ('charge.dispute.created','charge.dispute.updated','charge.dispute.closed'):
        tx=await transaction_for_intent(obj.get('payment_intent'))
        if not tx:
            return False
        # Never automatically release a held commission, including a closed dispute.
        await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'dispute_hold':True,'dispute_id':obj['id']}})
        await db.redemptions.update_one({'idempotency_key':tx['id']},{'$set':{'commission':0,'dispute_hold':True}})
        await db.redemptions.update_one({'idempotency_key':'refund-'+tx['id']},{'$set':{'commission':0,'dispute_hold':True}})
        from realtime import emit
        emit('pagamento_atualizado', currency='brl', partner_id=tx['partner_id'], influencer_id=tx.get('influencer_id'), ref=tx['id'])
        return True
    if kind == 'charge.refunded':
        tx=await transaction_for_intent(obj.get('payment_intent'))
        if not tx:
            if (obj.get('payment_method_details') or {}).get('type') == 'pix':
                raise HTTPException(503,'Pagamento Pix ainda não conciliado; repetir evento')
            return False
        await refund(tx,obj)
        return True
    if not kind.startswith('checkout.session.'):
        return False
    tx=await db.payment_transactions.find_one({'kind':'pix_coupon','session_id':obj['id']},NO_ID)
    if not tx and metadata.get('kind') == 'pix_coupon':
        tx=await db.payment_transactions.find_one({'id':'pix-'+metadata.get('request_id',''),'kind':'pix_coupon'},NO_ID)
        if not tx:
            raise HTTPException(503,'Pedido Pix ainda não disponível; repetir evento')
    if not tx:
        return False
    if kind in ('checkout.session.completed','checkout.session.async_payment_succeeded'):
        await settle(tx,obj)
    elif kind in ('checkout.session.expired','checkout.session.async_payment_failed'):
        state='expired' if kind.endswith('expired') else 'failed'
        await db.payment_transactions.update_one({'id':tx['id'],'payment_status':{'$ne':'paid'}},{'$set':{'status':state,'payment_status':state}})
    return True


@router.get('/payments/pix/status/{identifier}')
async def status(identifier: str):
    if identifier.startswith('cs_'):
        query={'kind':'pix_coupon','session_id':identifier}
    else:
        try: key=str(uuid.UUID(identifier))
        except ValueError: raise HTTPException(404,'Pagamento não encontrado')
        query={'kind':'pix_coupon','id':'pix-'+key}
    tx=await db.payment_transactions.find_one(query,NO_ID)
    if not tx: raise HTTPException(404,'Pagamento não encontrado')
    if tx.get('session_id','').startswith('cs_') and (tx.get('payment_status')!='paid' or not tx.get('conversion_processed') or tx.get('split_status')!='completed'):
        try:
            obj=await provider('checkout.sessions.retrieve',tx['session_id'])
            await settle(tx,obj)
        except stripe.error.StripeError:
            raise HTTPException(502,'Não foi possível confirmar o Pix; tente novamente')
        except HTTPException as error:
            # Settlement stores payment confirmation before attempting transfers.
            # A temporary transfer outage must not tell a paid customer to pay again.
            latest = await db.payment_transactions.find_one(query, NO_ID)
            if error.status_code not in (502, 503) or not latest or latest.get('payment_status') != 'paid':
                raise
            return public(latest)
        tx=await db.payment_transactions.find_one(query,NO_ID)
    return public(tx)


from fastapi import Depends
from core import require_role


@router.post('/partner/pix/connect/onboard')
async def connect_onboard(body: dict, user: dict = Depends(require_role('partner','influencer'))):
    origin=trusted_origin(body.get('origin_url',''))
    collection=db.influencers if user.get('role')=='influencer' else db.partners
    entity_id=user.get('influencer_id') if user.get('role')=='influencer' else user.get('partner_id')
    partner=await collection.find_one({'id':entity_id},NO_ID) if user.get('role')=='influencer' else await partner_record(user, db)
    if not partner or (user.get('role')!='influencer' and partner.get('currency')!='brl'):
        raise HTTPException(409,'Recebimentos Pix disponíveis apenas para parceiro em reais')
    platform=await provider('accounts.retrieve_current')
    if platform.get('country')!='BR':
        raise HTTPException(409,'Pix exige plataforma Stripe domiciliada no Brasil')
    try:
        account=partner.get('pix_stripe_account_id')
        if not account:
            created=await provider('accounts.create',idempotency_key='pix-connect-'+partner['id'],type='express',country='BR',email=user['email'],business_type=('individual' if user.get('role')=='influencer' else 'company'),capabilities={'card_payments':{'requested':True},'transfers':{'requested':True}},business_profile={'name':partner.get('nome',user['nome'])},metadata={'partner_id':partner['id']})
            account=created.id
            saved=await collection.update_one({'id':partner['id'],'pix_stripe_account_id':None},{'$set':{'pix_stripe_account_id':account,'pix_stripe_charges_enabled':False,'pix_stripe_payouts_enabled':False}})
            if saved is not None and not saved.matched_count:
                raise HTTPException(409,'A conta de recebimento mudou durante a configuração; atualize antes de continuar')
        info=await provider('accounts.retrieve',account)
        receiving_status(info, partner)
        link=await provider('account_links.create',account=account,refresh_url=origin+('/influencer/extrato' if user.get('role')=='influencer' else '/parceiro')+'?connect=refresh',return_url=origin+('/influencer/extrato' if user.get('role')=='influencer' else '/parceiro')+'?connect=return',type='account_onboarding')
    except stripe.error.StripeError:
        raise HTTPException(502,'Stripe Connect indisponível; confirme a habilitação de recebimentos no Brasil')
    return {'available':True,'url':link.url,'account_id':account}


@router.get('/partner/pix/connect/status')
async def connect_status(user: dict = Depends(require_role('partner','influencer'))):
    collection=db.influencers if user.get('role')=='influencer' else db.partners
    entity_id=user.get('influencer_id') if user.get('role')=='influencer' else user.get('partner_id')
    partner=await collection.find_one({'id':entity_id},NO_ID) if user.get('role')=='influencer' else await partner_record(user, db)
    if not partner or (user.get('role')!='influencer' and partner.get('currency')!='brl'):
        raise HTTPException(409,'Parceiro não opera em reais')
    account=partner.get('pix_stripe_account_id')
    if not account:
        return {'connected':False,'status_verified':True,'charges_enabled':False,'payouts_enabled':False,'transfers_enabled':False,'receiving_ready':False}
    try:
        info=await provider('accounts.retrieve',account)
    except stripe.error.StripeError:
        raise HTTPException(502,'Não foi possível verificar os recebimentos; tente novamente')
    result=receiving_status(info, partner)
    await collection.update_one({'id':partner['id'], 'pix_stripe_account_id':account},{'$set':{'pix_stripe_charges_enabled':result['charges_enabled'],'pix_stripe_payouts_enabled':result['payouts_enabled'],'pix_stripe_transfers_enabled':result['transfers_enabled'],'pix_stripe_status_synced_at':now_iso()}})
    return result


async def execute_split(tx, intent_id):
    latest=await db.payment_transactions.find_one({'id':tx['id']},NO_ID)
    if latest.get('dispute_hold') or latest.get('refunded_cents'):
        await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'split_status':'held'}})
        return
    intent=await provider('payment_intents.retrieve',intent_id)
    charge=intent.get('latest_charge')
    if not charge or intent.get('status')!='succeeded' or intent.get('currency')!='brl' or intent.get('amount_received')!=tx['net_cents']:
        raise HTTPException(503,'Cobrança Pix ainda não disponível para divisão')
    for recipient, destination, amount in (('partner',tx['destination'],tx['partner_cents']),('influencer',tx['influencer_destination'],tx['influencer_cents'])):
        latest=await db.payment_transactions.find_one({'id':tx['id']},NO_ID)
        if latest.get(recipient+'_transfer_id'): continue
        if latest.get('dispute_hold') or latest.get('refunded_cents'):
            await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'split_status':'held'}})
            return
        attempted=latest.get(recipient+'_transfer_started_at')
        if attempted and (datetime.now(timezone.utc)-datetime.fromisoformat(attempted)).total_seconds()>23*3600:
            raise HTTPException(409,'Divisão antiga pendente: conciliação manual necessária antes de repetir')
        if not attempted:
            await db.payment_transactions.update_one({'id':tx['id']},{'$set':{recipient+'_transfer_started_at':now_iso()}})
        await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'split_status':'pending',recipient+'_transfer_status':'pending'}})
        transfer=await provider('transfers.create',amount=amount,currency='brl',destination=destination,source_transaction=charge,transfer_group=tx['id'],metadata={'pix_request_id':tx['request_id'],'recipient':recipient},idempotency_key=tx['id']+'-'+recipient)
        await db.payment_transactions.update_one({'id':tx['id']},{'$set':{recipient+'_transfer_id':transfer['id'],recipient+'_transfer_status':'completed'}})
    await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'split_status':'completed'}})
    from realtime import emit
    emit('pagamento_atualizado',currency='brl',partner_id=tx['partner_id'],influencer_id=tx.get('influencer_id'),ref=tx['id'])


async def reverse_split(tx, cumulative):
    await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'reversal_status':'pending','manual_payout_blocked':True}})
    for recipient in ('partner','influencer'):
        latest=await db.payment_transactions.find_one({'id':tx['id']},NO_ID)
        transfer_id=latest.get(recipient+'_transfer_id')
        if not transfer_id: continue
        target=int((Decimal(tx[recipient+'_cents'])*cumulative/tx['net_cents']).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        current=await provider('transfers.retrieve',transfer_id)
        reversed_amount=current.get('amount_reversed',0)
        if target>reversed_amount:
            await provider('transfers.reversals.create',transfer_id,amount=target-reversed_amount,idempotency_key=tx['id']+'-'+recipient+'-refund-'+str(target))
        await db.payment_transactions.update_one({'id':tx['id']},{'$max':{recipient+'_reversed_cents':target}})
    await db.payment_transactions.update_one({'id':tx['id']},{'$set':{'reversal_status':'completed','manual_payout_blocked':True}})


@router.post('/stripe/pix/webhook')
async def pix_webhook(request: Request):
    secret=os.getenv('PIX_STRIPE_WEBHOOK_SECRET','')
    if not secret:
        raise HTTPException(503,'Webhook Pix não configurado')
    try:
        event=stripe.Webhook.construct_event(await request.body(),request.headers.get('stripe-signature',''),secret)
        # The real Stripe SDK returns a StripeObject, not a dict with .get().
        # Convert the already signature-verified payload before processing.
        obj=event['data']['object']
        if hasattr(obj,'to_dict'):
            event['data']['object']=obj.to_dict()
    except (stripe.error.SignatureVerificationError,ValueError):
        raise HTTPException(400,'Assinatura Pix inválida')
    await handle_pix_event(event)
    return {'received':True}
