#!/usr/bin/env python3
"""Selective P5 repair + read-only diagnostic; does not deploy or change .env."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path('/app') if Path('/app/backend/server.py').is_file() else Path.cwd()
BASE = '4714666895934b492437f142eb54352b2cabb44d'
TARGET = '1dc0dcb1c14e864c82b60d7716de01e783d47ab1'
MANIFEST = [['backend/p5_checkout.py', 'd967a54165bb5476df6da01e37e585a662d4214d', 'ecbb368892ff33ac9f69acf53736847f7a31c98a'], ['backend/payments/pix/checks.py', '9f88edc645b951ce5f185119319856b800d1c525', '3ff3e056bd0f0202164f228bf598eeab51bbf109'], ['backend/routes_payments.py', '24591d817baf51c017ce199d9436422c25b45cdd', '8ca948de1c61558e60b045c1bfd14dee98b7f85d'], ['backend/routes_pix.py', 'dfcaec04768e51721f71a7445899c17525bcbaf7', '59c3da2be0d30bdc835264534a19e1592f89069c'], ['backend/tests/test_pix_readiness.py', '6afd198ec6c2211a6ec61a9e4ec06256347c9f91', '5507fabe2f45dbf4396946908f3820b453dcf53f'], ['backend/tests/test_pix_service.py', '115477bc99d9febdb76bbb5edb09714b235c10f4', '411ce3a8bb9939ce1c95e7d1f5c9f9e8494e442d'], ['frontend/src/components/P5FollowerPanel.jsx', '69351af99ad6ba8ba7d4574af3220b51e9b12abf', '1dfd5df44e99c7baffbf0fd9c5aff0db251507d0'], ['frontend/src/components/P5FollowerPanel.test.jsx', '33c2549e8f2f68af6c7d835fb416efe20eda210f', '779250ac628af0ee3cf272f98927978c9d64ba20'], ['frontend/src/components/StripeStatusCard.jsx', 'e608142ecb54195e015b676a546a6663f8f44352', '364d35b32b4e6121cd61009a989aa7539882c54e'], ['frontend/src/pages/PublicCoupon.jsx', '154a1f0bf4a9c42f8528ebf267fb4429a4563261', 'c4bbf8be4262278b3b072565924d7f7df7da6c4c'], ['docs/CORRECOES_E_MEMORIA/20261021_QR_PIX_FLUXO.md', None, 'c847dc4965698c5af0ec7ed119c2274b5783f639'], ['frontend/src/lib/saveQr.js', None, '67401fa4c11bd059272938610e06259ad2518a90'], ['frontend/src/lib/saveQr.test.js', None, 'f093390500e1e042444e0f62dc75c04d4e9fe082'], ['scripts/rrclub_p5_campaign_diagnostic.py', None, 'd57fae658f0b2b39edd127200e450f48a0a12909']]


def git_hash(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def remote(ref, path, expected):
    url = f'https://raw.githubusercontent.com/faellt34/NOVORRCLUB/{ref}/{path}'
    with urlopen(Request(url, headers={'User-Agent': 'rrclub-selective-repair'}), timeout=30) as response:
        data = response.read(400000)
    if git_hash(data) != expected:
        raise RuntimeError('Conteúdo remoto inesperado: ' + path)
    return data


def merged(path, ours, base, target):
    if ours == target:
        return ours
    if ours == base:
        return target
    with tempfile.TemporaryDirectory(prefix='rrclub-merge-') as folder:
        files = [Path(folder) / name for name in ('ours', 'base', 'target')]
        for file, data in zip(files, (ours, base, target)):
            file.write_bytes(data)
        result = subprocess.run(['git', 'merge-file', '-p', *map(str, files)],
                                capture_output=True, timeout=20)
        if result.returncode:
            raise RuntimeError('Conflito local em ' + path + '; nenhum ficheiro alterado.')
        return result.stdout


def stage():
    if not (ROOT / 'backend/p5_checkout.py').is_file():
        raise RuntimeError('Workspace P5 não identificado.')
    result = {}
    for path, base_hash, target_hash in MANIFEST:
        local = ROOT / path
        if local.is_symlink():
            raise RuntimeError('Ligação simbólica inesperada: ' + path)
        target = remote(TARGET, path, target_hash)
        ours = local.read_bytes() if local.is_file() else None
        if ours == target:
            continue
        if base_hash is None:
            if ours is not None:
                raise RuntimeError('Ficheiro novo já personalizado: ' + path)
            new = target
        else:
            if ours is None:
                raise RuntimeError('Ficheiro local ausente: ' + path)
            new = merged(path, ours, remote(BASE, path, base_hash), target)
        if new != ours:
            result[path] = new
    for path, data in result.items():
        if path.endswith('.py'):
            ast.parse(data.decode(), filename=path)
    js = [(path, data) for path, data in result.items() if path.endswith(('.js', '.jsx'))]
    if js:
        with tempfile.TemporaryDirectory(prefix='rrclub-js-') as folder:
            files = []
            for number, (_, data) in enumerate(js):
                file = Path(folder) / f'{number}.js'
                file.write_bytes(data)
                files.append(str(file))
            code = "const fs=require('fs'),p=require('@babel/parser');for(const f of process.argv.slice(1))p.parse(fs.readFileSync(f,'utf8'),{sourceType:'module',plugins:['jsx']});"
            parsed = subprocess.run(['node', '-e', code, *files], cwd=ROOT/'frontend',
                                    capture_output=True, timeout=30)
            if parsed.returncode:
                raise RuntimeError('Validação JavaScript falhou; nenhum ficheiro alterado.')
    return result


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.rrclub-stage')
    try:
        tmp.write_bytes(data)
        if path.exists():
            tmp.chmod(path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def main():
    staged = stage()
    print('Sintaxe e merge seletivo aprovados:', len(staged), 'ficheiros.')
    if '--check' in sys.argv:
        print('Verificação concluída; nenhum ficheiro alterado.')
        return
    backup = Path(tempfile.mkdtemp(prefix='rrclub_qr_pix_backup_'))
    originals = {}
    for name in staged:
        path = ROOT / name
        originals[name] = path.read_bytes() if path.is_file() else None
        if path.is_file():
            dest = backup / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
    try:
        for name, data in staged.items():
            write(ROOT / name, data)
    except Exception:
        for name, data in originals.items():
            path = ROOT / name
            if data is None:
                path.unlink(missing_ok=True)
            else:
                write(path, data)
        raise RuntimeError('Falha ao guardar; originais restaurados.')
    print('APLICADO — QR P5, associação por tipo e diagnóstico financeiro.')
    print('Backup:', backup)
    print('Sem alterações a .env, contas Stripe, pagamentos ou transferências. Ainda sem deploy.')
    print('DIAGNÓSTICO DE LEITURA DA CAMPANHA SHEYSO-7182:')
    result = subprocess.run([sys.executable, str(ROOT/'scripts/rrclub_p5_campaign_diagnostic.py'),
                             'SHEYSO-7182'], cwd=ROOT, capture_output=True, text=True, timeout=90)
    if result.returncode:
        print('Consulta indisponível. Código aplicado; é necessário verificar a base antes do teste financeiro.')
    else:
        print(result.stdout)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('PARADO:', str(error))
        sys.exit(1)
