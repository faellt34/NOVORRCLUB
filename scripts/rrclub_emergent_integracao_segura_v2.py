#!/usr/bin/env python3
"""RRClub Emergent: pinned patch PR #7/#8, safe merge, quick checks.

Does not deploy, edit databases, invoke Stripe, or make live payments.
Keeps local code on merge conflicts. Rolls back edited source files on validation error.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPOSITORY = 'https://github.com/faellt34/NOVORRCLUB.git'
TARGET_REF = 'integracao-google-rrclub-20261019'
TARGET_SHA = '408e161d882a9e6389ef88e905ce792de298225c'
BASE_SHA = '986f8400a4b1b419f8bae15d108a07df17c56858'
FILES = [
    'backend/finance_evidence.py',
    'backend/payout_attribution.py',
    'backend/routes_finance.py',
    'backend/routes_ops.py',
    'backend/routes_payments.py',
    'backend/routes_data.py',
    'backend/server.py',
    'backend/tests/test_finance_evidence.py',
    'backend/tests/test_payout_attribution.py',
    'frontend/src/components/FinanceReconciliationPanel.jsx',
    'frontend/src/components/FinanceReconciliationPanel.test.jsx',
    'frontend/src/pages/AdminDashboard.jsx',
    'frontend/src/pages/AdminPayouts.jsx',
    'frontend/src/pages/PartnerDashboard.jsx',
]
PREVIOUS_AUDIT = {
    'backend/finance_evidence.py': 'def transfer_evidence(',
    'backend/routes_finance.py': '"/admin/finance/reconciliation"',
    'frontend/src/components/FinanceReconciliationPanel.jsx': 'function FinanceReconciliationPanel(',
}


def run(args, cwd, timeout=120, env=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, env=env)


def good(args, cwd, label, timeout=120, env=None):
    result = run(args, cwd, timeout, env)
    if result.returncode:
        raise RuntimeError(f'{label}: {(result.stderr or result.stdout)[-1600:]}')
    return result.stdout


def read_revision(root, rev, path):
    result = run(['git', 'show', f'{rev}:{path}'], root)
    return result.stdout if result.returncode == 0 else None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_server(current):
    new = current
    if 'import routes_finance' not in new:
        match = re.search(r'^import routes_payments\s*$', new, re.M)
        if not match:
            raise ValueError('server.py: local de importação de rotas não identificado')
        new = new[:match.end()] + '\nimport routes_finance' + new[match.end():]
    if 'routes_finance.router' not in new:
        if new.count('routes_payments.router') != 1:
            raise ValueError('server.py: lista de routers não identificada')
        new = new.replace('routes_payments.router',
                          'routes_payments.router, routes_finance.router', 1)
    return new


def patch_payouts(current):
    new = current
    if 'import FinanceReconciliationPanel' not in new:
        new = ('import FinanceReconciliationPanel from '
               '"../components/FinanceReconciliationPanel";\n' + new)
    component = '<FinanceReconciliationPanel />'
    visibility = '{reportCurrency() === "eur" && <FinanceReconciliationPanel />}'
    if component not in new:
        match = re.search(r'\breturn\s*\(\s*<div\b[^>]*>', new)
        if not match:
            raise ValueError('AdminPayouts: ponto de inserção não identificado')
        new = new[:match.end()] + '\n      ' + visibility + new[match.end():]
    elif visibility not in new:
        new = new.replace(component, visibility, 1)
    guard = ('if (reportCurrency() === "eur" && '
             '(r.status !== "Pendente" || !r.attribution_verified))')
    if guard not in new:
        marker = 'const markPaid = async (r) => {'
        if new.count(marker) != 1:
            raise ValueError('AdminPayouts: não encontrei botão de registo de pagamento')
        block = ('\n    ' + guard + ' {\n'
                 '      toast.error("Comissão sem conciliação financeira; '
                 'confirma beneficiário e pagamento antes de registar.");\n'
                 '      return;\n'
                 '    }')
        new = new.replace(marker, marker + block, 1)
    return new


def reconcile(root, scratch, relpath, current, ancestor, target):
    if current == target:
        return current, 'já atualizado'
    if relpath == 'backend/server.py' and current is not None:
        return patch_server(current), 'rotas originais preservadas'
    if relpath == 'frontend/src/pages/AdminPayouts.jsx' and current is not None \
            and 'FinanceReconciliationPanel' in current:
        return patch_payouts(current), 'painel personalizado preservado'
    if current is None:
        if ancestor is not None:
            raise ValueError(f'{relpath}: ficheiro removido no Emergent')
        return target, 'novo ficheiro'
    if ancestor is None:
        if relpath in PREVIOUS_AUDIT and PREVIOUS_AUDIT[relpath] in current:
            return target, 'substituir auditoria antiga com backup'
        raise ValueError(f'{relpath}: ficheiro local não corresponde à base conhecida')
    if current == ancestor:
        return target, 'alteração direta'
    folder = scratch / 'merge' / relpath.replace('/', '__')
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in (('LOCAL', current), ('BASE', ancestor), ('NOVO', target)):
        (folder / name).write_text(text, encoding='utf-8')
    result = run(['git', 'merge-file', '-p', str(folder / 'LOCAL'),
                  str(folder / 'BASE'), str(folder / 'NOVO')], root)
    if result.returncode:
        (folder / 'CONFLITO.txt').write_text(result.stdout, encoding='utf-8')
        raise ValueError(f'{relpath}: conflito de merge (ficheiro original preservado)')
    return result.stdout, 'merge limpo preservando alterações locais'


def main():
    root = Path('/app') if Path('/app/backend/server.py').exists() else Path.cwd()
    git_root = good(['git', 'rev-parse', '--show-toplevel'], root,
                    'Encontrar repositório').strip()
    root = Path(git_root).resolve()
    for expected in ('backend/server.py', 'backend/routes_pix.py',
                     'frontend/package.json'):
        if not (root / expected).is_file():
            raise RuntimeError(f'Não é o projeto RRClub: {expected}')
    root_pix = root / 'backend/routes_pix.py'
    pix_hash = digest(root_pix)
    scratch = Path(tempfile.mkdtemp(prefix='rrclub_integracao_v2_'))
    print('RRCLUB V2 | integração sem deploy nem operações bancárias', flush=True)
    print('Backup de código:', scratch, flush=True)
    print('1/4 Consultar commit verificado...', flush=True)
    good(['git', 'fetch', '--quiet', '--no-tags', REPOSITORY, TARGET_SHA],
         root, 'Consultar GitHub', timeout=180)
    got = good(['git', 'rev-parse', 'FETCH_HEAD'], root, 'Confirmar commit').strip()
    if got != TARGET_SHA:
        raise RuntimeError('A branch GitHub mudou: NÃO aplicar atualização inesperada')
    if run(['git', 'cat-file', '-e', BASE_SHA + '^{commit}'], root).returncode:
        good(['git', 'fetch', '--quiet', '--no-tags', REPOSITORY, BASE_SHA],
             root, 'Ler base histórica', timeout=180)
    print('2/4 Comparar TODOS os ficheiros antes de escrever...', flush=True)
    changes = {}
    errors = []
    for relpath in FILES:
        dest = root / relpath
        current = dest.read_text('utf-8') if dest.is_file() else None
        ancestor = read_revision(root, BASE_SHA, relpath)
        target = read_revision(root, TARGET_SHA, relpath)
        if target is None:
            errors.append(relpath + ': ausente na versão corrigida')
            continue
        try:
            merged, note = reconcile(root, scratch, relpath, current, ancestor, target)
            if merged != current:
                changes[relpath] = merged
                print('  PREPARADO:', relpath, '-', note, flush=True)
            else:
                print('  OK:', relpath, flush=True)
        except (ValueError, UnicodeError) as error:
            errors.append(str(error))
    if errors:
        print('NÃO APLICADO: existem conflitos; nenhum ficheiro original foi modificado')
        for error in errors:
            print(' •', error)
        print('Comparações:', scratch)
        return 2
    print('3/4 Criar backups e aplicar patch...', flush=True)
    originals = {}
    for relpath in changes:
        dest = root / relpath
        originals[relpath] = dest.read_bytes() if dest.exists() else None
        if dest.exists():
            copy = scratch / 'backup' / relpath
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, copy)
    applied = []
    try:
        for relpath, contents in changes.items():
            dest = root / relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = dest.with_name(dest.name + '.rrclub-v2-pending')
            temp.write_text(contents, encoding='utf-8')
            os.replace(temp, dest)
            applied.append(relpath)
        if digest(root_pix) != pix_hash:
            raise RuntimeError('Proteção Pix: ficheiro Pix foi alterado')
        server = (root / 'backend/server.py').read_text('utf-8')
        payout = (root / 'frontend/src/pages/AdminPayouts.jsx').read_text('utf-8')
        if not all(t in server for t in ('routes_pix.router', 'routes_finance.router')):
            raise RuntimeError('Proteção rotas: Pix e auditoria têm de estar registados')
        if 'FinanceReconciliationPanel' not in payout:
            raise RuntimeError('Proteção do ecrã: auditoria ausente')
        print('4/4 Testes rápidos SEM Jest em modo watch...', flush=True)
        env = os.environ.copy()
        env['PYTHONPATH'] = str(root / 'backend')
        env['CI'] = 'true'
        env['WATCHMAN_DISABLE'] = '1'
        for args in (
            [sys.executable, '-m', 'compileall', '-q', 'backend'],
            [sys.executable, '-m', 'unittest', 'discover', '-s', 'backend/tests',
             '-p', 'test_finance_evidence.py', '-v'],
            [sys.executable, '-m', 'unittest', 'discover', '-s', 'backend/tests',
             '-p', 'test_payout_attribution.py', '-v'],
        ):
            good(args, root, 'Teste Python: ' + ' '.join(args), 90, env)
            print('  APROVADO:', args[-2] if '-p' in args else 'sintaxe Python', flush=True)
        # Babel parses React JSX without starting CRA/Jest/webpack's expensive watch processes.
        script = (
            "const fs=require('fs'), p=require('@babel/parser');"
            "for(const f of process.argv.slice(1)){"
            "p.parse(fs.readFileSync(f,'utf8'),{sourceType:'module',plugins:['jsx']});"
            "console.log('JSX OK:',f)}"
        )
        jsx_files = [str(root / rel) for rel in FILES if rel.endswith('.jsx')]
        good(['node', '-e', script, *jsx_files], root / 'frontend',
             'Verificar sintaxe JSX', 45, env)
        print('  APROVADO: sintaxe JSX sem modo watch', flush=True)
        if digest(root_pix) != pix_hash:
            raise RuntimeError('Proteção Pix: alteração inesperada')
    except Exception:
        print('Falha na validação: a restaurar ficheiros originais...', flush=True)
        for relpath in reversed(applied):
            dest = root / relpath
            contents = originals[relpath]
            if contents is None:
                dest.unlink(missing_ok=True)
            else:
                dest.write_bytes(contents)
        print('ORIGINAIS RESTAURADOS. Backup:', scratch, flush=True)
        raise
    print('\n===============================================')
    print('CODIGO INTEGRADO E VERIFICACOES RAPIDAS APROVADAS')
    print('===============================================')
    print('Ficheiros modificados:', len(changes))
    print('Pix Brasil: original intacto')
    print('Backup:', scratch)
    print('Teste JSX: passou; Jest e build local NÃO executados por lentidão anterior.')
    print('Testes completos da versão GitHub: aprovados previamente no CI.')
    print('DEPLOY: NÃO EFETUADO. PAGAMENTOS: NENHUNS.')
    print('Próximo passo: inspeção no preview e testes funcionais antes de publicar.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired as exc:
        print('PARADO COM SEGURANÇA: tempo esgotado em', exc.cmd)
        sys.exit(1)
    except Exception as exc:
        print('PARADO COM SEGURANÇA:', str(exc)[:1200])
        sys.exit(1)