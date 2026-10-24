#!/usr/bin/env python3
"""Apply RRClub BR Pix configuration patch. No secrets, payment or deploy."""
from pathlib import Path
import ast
import os
import sys
import urllib.request
import tempfile
import shutil
import subprocess

root = Path('/app')
sha = 'c9616ce037f429c15765480e0b6684c534073862'
base = f'https://raw.githubusercontent.com/faellt34/NOVORRCLUB/{sha}/'
route = root / 'backend/routes_pix.py'
server = root / 'backend/server.py'
if not route.is_file() or not server.is_file():
    raise SystemExit('BLOQUEADO: routes_pix.py ou server.py ausente. Nada alterado.')

original = {route: route.read_text(encoding='utf-8'), server: server.read_text(encoding='utf-8')}
updated = {}
for rel in ('backend/pix_config.py', 'backend/tests/test_pix_config.py', 'docs/PIX_BR_CONFIG.md'):
    target = root / rel
    try:
        with urllib.request.urlopen(base + rel, timeout=20) as response:
            content = response.read().decode('utf-8')
    except Exception as exc:
        raise SystemExit('BLOQUEADO: falha a consultar versao fixada no GitHub: ' + type(exc).__name__)
    if target.exists() and target.read_text(encoding='utf-8') != content:
        raise SystemExit('BLOQUEADO: ficheiro local personalizado: ' + rel)
    original[target] = target.read_text(encoding='utf-8') if target.exists() else None
    updated[target] = content

s = original[route]
anchor = 'from payments.pix.checks import platform_checks, configuration_checks, receiving_status, webhook_checks'
new_import = 'from pix_config import configuration_status, pix_payment_method_configuration'
if new_import not in s:
    if 'from pix_config import configuration_status' in s:
        s = s.replace('from pix_config import configuration_status', new_import, 1)
    elif s.count(anchor) == 1:
        s = s.replace(anchor, anchor + '\n' + new_import, 1)
    else:
        raise SystemExit('BLOQUEADO: import Pix inesperado.')

old_key = """def pix_key():
    key=os.getenv('PIX_STRIPE_SECRET_KEY','')
    if not key or os.getenv('PIX_STRIPE_PLATFORM_COUNTRY')!='BR':
        raise HTTPException(503,'Configure a conta Stripe brasileira exclusiva do Pix')
    return key"""
new_key = """def pix_key():
    key=os.getenv('PIX_STRIPE_SECRET_KEY','')
    _, checks = configuration_status()
    if not all(checks[k] for k in ('api_key', 'platform_country_br', 'separate_brazil_key')):
        raise HTTPException(503,'Configure uma chave Stripe exclusiva da plataforma Brasil')
    return key"""
if new_key not in s:
    if s.count(old_key) != 1:
        raise SystemExit('BLOQUEADO: funcao pix_key foi personalizada.')
    s = s.replace(old_key, new_key, 1)

start = s.find('def availability_configuration():\n')
end = s.find("\n\n@router.get('/public/pix/availability')", start)
if start < 0 or end < 0:
    raise SystemExit('BLOQUEADO: availability_configuration nao encontrada.')
section = s[start:end]
if 'return configuration_status()' not in section:
    if not ('configuration={' in section and 'accepting_new_payments' in section and len(section) < 1700):
        raise SystemExit('BLOQUEADO: availability_configuration personalizada.')
    s = s[:start] + 'def availability_configuration():\n    return configuration_status()' + s[end:]

old_pmc = "os.environ['PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION']"
if old_pmc not in s and 'pix_payment_method_configuration()' not in s:
    raise SystemExit('BLOQUEADO: lookup de configuracao Pix nao identificado.')
s = s.replace(old_pmc, 'pix_payment_method_configuration()')
updated[route] = s

s = original[server]
if 'from pix_config import configuration_status' not in s:
    if s.count('import routes_pix\n') != 1:
        raise SystemExit('BLOQUEADO: server.py diferente.')
    s = s.replace('import routes_pix\n', 'import routes_pix\nfrom pix_config import configuration_status\n', 1)
if 'pix_state, pix_checks = configuration_status()' not in s:
    marker = '@app.on_event("startup")\nasync def on_startup():\n'
    if s.count(marker) != 1:
        raise SystemExit('BLOQUEADO: startup de server.py diferente.')
    warning = """@app.on_event("startup")
async def on_startup():
    pix_state, pix_checks = configuration_status()
    if not pix_state["configured"]:
        logging.getLogger(__name__).warning(
            "PIX Brasil indisponivel neste ambiente; verificacoes ausentes: %s",
            ", ".join(k for k, valid in pix_checks.items() if not valid)
        )
    elif not pix_state["enabled"]:
        logging.getLogger(__name__).info("PIX Brasil configurado mas desativado")
"""
    s = s.replace(marker, warning, 1)
updated[server] = s

for target, contents in updated.items():
    if target.suffix == '.py':
        try:
            ast.parse(contents, filename=str(target))
        except SyntaxError:
            raise SystemExit('BLOQUEADO: sintaxe invalida em ' + str(target))

changed = {path: contents for path, contents in updated.items() if original[path] != contents}
if not changed:
    print('PIX BRASIL: codigo central ja aplicado. Nada duplicado.')
    sys.exit(0)

backup = Path(tempfile.mkdtemp(prefix='rrclub_pix_br_backup_'))
for idx, target in enumerate(changed):
    if original[target] is not None:
        shutil.copy2(target, backup / (str(idx) + '_' + target.name))
try:
    for target, contents in changed.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding='utf-8')
    env = dict(os.environ, PYTHONPATH=str(root / 'backend'))
    result = subprocess.run(
        [sys.executable, '-m', 'unittest', 'discover',
         '-s', str(root / 'backend/tests'), '-p', 'test_pix_config.py', '-v'],
        cwd=root, env=env, text=True, capture_output=True, timeout=60
    )
    print(result.stdout[-3000:])
    print(result.stderr[-4000:])
    if result.returncode:
        raise RuntimeError('testes unitarios falharam')
except Exception as exc:
    for target in changed:
        if original[target] is None:
            target.unlink(missing_ok=True)
        else:
            target.write_text(original[target], encoding='utf-8')
    raise SystemExit('BLOQUEADO: alteracoes revertidas: ' + str(exc))

print('PIX BRASIL: CODIGO CENTRAL APLICADO E TESTES PASSARAM')
print('Ficheiros alterados:', ', '.join(str(p.relative_to(root)) for p in changed))
print('Backups:', backup)
print('Nenhum segredo, pagamento, transferencia ou deploy executado.')
print('A chave Stripe BR e o webhook secret continuam a depender do ambiente.')
