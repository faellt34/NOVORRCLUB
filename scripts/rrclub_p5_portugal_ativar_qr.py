#!/usr/bin/env python3
"""Enable Portugal P5 QR in an Emergent workspace without altering financial transfer policy.

Selective 3-way merge with hashes and backup; .env changes only P5_ENABLED and
P5_EUR_ENABLED. No Stripe API calls, payouts, resets, deploy, or Pix edits.
"""
import ast
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
BASE = "7baea06b20ed5e23aec165017c8810ca91b65247"
TARGET = "fix/p5-portugal-mbway-loja-20261021"
REPO = "faellt34/NOVORRCLUB"
MANIFEST = [["frontend/src/pages/PartnerDashboard.jsx","8d015e3ff19c0c62896d017426f4d082dccdb43c","88b5e268a5641da96d61093382b4a8ba2698130f"],["frontend/src/components/P5FollowerPanel.jsx","1dfd5df44e99c7baffbf0fd9c5aff0db251507d0","a2d7c73fed116ec31dcdfeccf20b094263b9d812"],["frontend/src/components/P5FollowerPanel.test.jsx","779250ac628af0ee3cf272f98927978c9d64ba20","f78cbcac254cc5a106ce7969e4498228bb83d53c"],["frontend/src/lib/p5Scan.js",null,"59d9037dc7b639d10e8089c473f6bf35cefa7049"],["frontend/src/lib/p5Scan.test.js",null,"6014b643956d429e230f692e6eb3df350e2986ec"]]

def stop(message):
    raise RuntimeError(message)

def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def remote(ref, relative, expected):
    url = f"https://raw.githubusercontent.com/{REPO}/{ref}/{relative}"
    with urlopen(Request(url, headers={"User-Agent": "rrclub-p5-pt-safe-installer"}), timeout=30) as response:
        data = response.read(600_001)
    if len(data) > 600_000 or blob_sha(data) != expected:
        stop("Integridade GitHub não confirmada: " + relative)
    return data

def merged(relative, local_data, ancestor, target):
    if local_data == target:
        return target
    if local_data == ancestor:
        return target
    with tempfile.TemporaryDirectory(prefix="p5_pt_merge_") as tmp:
        files = [Path(tmp) / name for name in ("ours", "base", "target")]
        for path, data in zip(files, (local_data, ancestor, target)):
            path.write_bytes(data)
        result = subprocess.run(
            ["git", "merge-file", "-p", *map(str, files)], capture_output=True, timeout=30
        )
        if result.returncode != 0:
            stop("Conflito de personalização local em " + relative + "; nada aplicado")
        return result.stdout

def stage():
    required = ROOT / "backend/p5_checkout.py"
    if not required.is_file() or not (ROOT / "backend/pt_split.py").is_file():
        stop("P5 Portugal ainda não integrado no backend local")
    backend_code = required.read_text()
    server_code = (ROOT / "backend/server.py").read_text()
    if not all(word in backend_code for word in (
        'currency_enabled', 'recipients_ready', '"mb_way"', 'checkout_charge'
    )) or "p5_checkout.router" not in server_code:
        stop("Backend P5 Portugal diferente do esperado; não substituir ficheiros")
    staged = {}
    for name, old_sha, new_sha in MANIFEST:
        path = ROOT / name
        if path.is_symlink():
            stop("Ligação simbólica inesperada: " + name)
        target = remote(TARGET, name, new_sha)
        local = path.read_bytes() if path.is_file() else None
        if old_sha is None:
            if local is not None and local != target:
                stop("Ficheiro personalizado existente: " + name)
            updated = target
        else:
            if local is None:
                stop("Ficheiro existente em falta: " + name)
            ancestor = remote(BASE, name, old_sha)
            updated = merged(name, local, ancestor, target)
        if local != updated:
            staged[name] = updated
    for name, data in staged.items():
        if name.endswith(".py"):
            ast.parse(data.decode(), filename=name)
    js = [(name, data) for name, data in staged.items() if name.endswith((".js", ".jsx"))]
    if js:
        with tempfile.TemporaryDirectory(prefix="p5_pt_js_") as folder:
            files = []
            for i, (_, data) in enumerate(js):
                file = Path(folder) / f"{i}.js"
                file.write_bytes(data)
                files.append(str(file))
            parser = "const fs=require('fs'),p=require('@babel/parser');for(const f of process.argv.slice(1))p.parse(fs.readFileSync(f,'utf8'),{sourceType:'module',plugins:['jsx']});"
            checked = subprocess.run(
                ["node", "-e", parser, *files], cwd=ROOT / "frontend",
                capture_output=True, text=True, timeout=40
            )
            if checked.returncode:
                stop("Sintaxe do frontend falhou; nada aplicado: " + checked.stderr[-800:])
    return staged

def activate_env():
    path = ROOT / "backend/.env"
    if not path.is_file() or path.is_symlink():
        stop("backend/.env não encontrado; configure P5_ENABLED e P5_EUR_ENABLED no gestor de ambiente")
    data = path.read_bytes()
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    for key in ("P5_ENABLED", "P5_EUR_ENABLED"):
        positions = [i for i, line in enumerate(lines) if re.match(r"^\s*" + key + r"\s*=", line)]
        if len(positions) > 1:
            stop("Chave repetida em .env: " + key)
        if positions:
            index = positions[0]
            suffix = "\n" if lines[index].endswith("\n") else ""
            lines[index] = key + "=true" + suffix
        else:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(key + "=true\n")
    return "".join(lines).encode()

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".p5-pt-stage")
    try:
        tmp.write_bytes(data)
        if path.exists():
            tmp.chmod(path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)

def main():
    staged = stage()
    env_path = "backend/.env"
    env = activate_env()
    if (ROOT / env_path).read_bytes() != env:
        staged[env_path] = env
    print(f"Validado: {len(staged)} ficheiros para atualizar; conflito = 0.")
    print("Ativação P5 Portugal: QR/confirmar conta; sem modificar split, Pix, webhooks ou chaves Stripe.")
    for key in ("P5_ENABLED", "P5_EUR_ENABLED"):
        if os.environ.get(key, "true").strip().lower() == "false":
            print("ATENÇÃO: variável externa " + key + "=false pode sobrepor .env na publicação.")
    if "--check" in sys.argv:
        print("SOMENTE VERIFICAÇÃO. Nenhuma alteração efetuada.")
        return
    if "--apply" not in sys.argv:
        stop("Execute primeiro --check e depois --apply")
    backup = Path(tempfile.mkdtemp(prefix="rrclub_p5_pt_backup_"))
    backup.chmod(0o700)
    before = {}
    for name in staged:
        path = ROOT / name
        before[name] = path.read_bytes() if path.is_file() else None
        if path.is_file():
            dest = backup / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            if name == env_path:
                dest.chmod(0o600)
    try:
        for name, data in staged.items():
            atomic_write(ROOT / name, data)
    except Exception:
        for name, data in before.items():
            if data is None:
                (ROOT / name).unlink(missing_ok=True)
            else:
                atomic_write(ROOT / name, data)
        stop("Escrita falhou; ficheiros anteriores restaurados")
    print("RRCLUB P5 PORTUGAL: código e flags do QR preparados.")
    print("Backup:", backup)
    print("Sem deploy, cobrança, transferência financeira ou alteração de Pix.")
    print("Para pagar MB WAY live: confirmar previamente as duas contas Connect e as proteções do split.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("PARADO:", type(exc).__name__, str(exc))
        sys.exit(1)
