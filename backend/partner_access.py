"""Explicit account-to-business access; never infer ownership from an email."""
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def partner_record(user, database):
    pid = user.get('partner_id')
    if not isinstance(pid, str) or not pid.strip():
        logger.warning('partner_association_missing user_id=%s', user.get('id'))
        raise HTTPException(400, 'A sua conta não está ligada a um estabelecimento. Contacte o administrador.')
    partner = await database.partners.find_one({'id': pid}, {'_id': 0})
    if not partner:
        logger.warning('partner_association_dangling user_id=%s partner_id=%s', user.get('id'), pid)
        raise HTTPException(409, 'O estabelecimento associado à sua conta não foi encontrado. Contacte o administrador.')
    if partner.get('user_id') and partner['user_id'] != user.get('id'):
        logger.warning('partner_association_conflict user_id=%s partner_id=%s', user.get('id'), pid)
        raise HTTPException(403, 'A associação da sua conta ao estabelecimento precisa de verificação pelo administrador.')
    if partner.get('status') in ('Pendente', 'Suspenso'):
        raise HTTPException(403, 'O estabelecimento está suspenso ou aguarda aprovação da equipa.')
    return partner


def normalized_iban(value):
    import re
    iban = re.sub(r'\s+', '', value).upper()
    if not re.fullmatch(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', iban):
        raise HTTPException(400, 'IBAN inválido.')
    digits = ''.join(str(ord(char) - 55) if char.isalpha() else char for char in iban[4:] + iban[:4])
    if int(digits) % 97 != 1:
        raise HTTPException(400, 'IBAN inválido. Verifique os dígitos do número da conta.')
    return iban
