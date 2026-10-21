#!/usr/bin/env python3
"""Apply only the Paulo/Maraca Pix Connect status fix, preserving local edits.

Never touches .env, Stripe accounts, payouts, transfers, database, or deployments.
--check validates GitHub blobs and simulates safe merges before --apply.
"""
import argparse
import ast
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
REPO = "faellt34/NOVORRCLUB"
BASE = "91cd9c34aa69010aca2d84fb333c3eba8500cb67"
TARGET = "d1791ed6b2b8db65151e95ef13c9c8c66d65264e"
MANIFEST = [
    ("backend/routes_pix.py", "59c3da2be0d30bdc835264534a19e1592f89069c", "af8d74dc71e6bbc70911f39a483c6b14adf354ac"),
    ("frontend/src/components/PartnerOnboarding.jsx", "512c6b9e7e91fadb4786a17509d7ec6afdfdde61", "fe975c313384be47180a15405b0755cfe33aeed0"),
    ("frontend/src/pages/PartnerDashboard.jsx", "88b5e268a5641da96d61093382b4a8ba2698130f", "f77ea63c23290c49d90069800c49f6650723b3f2"),
    ("scripts/rrclub_diagnose_partner_pix.py", None, "f7402541dfbba847546f6ea55d5d9f6cc63f29ca"),
    ("backend/tests/test_pix_connect_pending_ui.py", None, "0f04247aa39787fd2668bdaa9a820148c0dd45ae"),
]


def github_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch(ref, name, expected):
    url = "https://raw.githubusercontent.com/" + REPO + "/" + ref + "/" + name
    with urlopen(Request(url, headers={"User-Agent": "RRClub-Paulo-Pix-Fix"}), timeout=30) as resp:
        data = resp.read(700001)
    if len(data) > 700000 or github_blob(data) != expected:
        raise RuntimeError("Falha de integridade GitHub: " + name)
    return data


def merge_safe(name, current, ancestor, target):
    if current == target:
        return target
    if current == ancestor:
        return target
    with tempfile.TemporaryDirectory(prefix="rrclub_paulo_merge_") as folder:
        paths = [Path(folder)/k for k in ("local", "base", "target")]
        for p, data in zip(paths, (current, ancestor, target)):
            p.write_bytes(data)
        result = subprocess.run(["git", "merge-file", "-p", *map(str, paths)],
                                capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError("CONFLITO em " + name + " — nenhum ficheiro alterado")
        return result.stdout


def validate_js(files):
    items = [(n, d) for n, d in files.items() if n.endswith((".js", ".jsx"))]
    if not items:
        return
    with tempfile.TemporaryDirectory(prefix="rrclub_paulo_validate_js_") as tmp:
        refs = []
        for i, (_, data) in enumerate(items):
            f = Path(tmp) / (str(i) + ".jsx")
            f.write_bytes(data)
            refs.append(str(f))
        js = ("const fs=require('fs'),parser=require('@babel/parser');"
              "for(const f of process.argv.slice(1))"
              "parser.parse(fs.readFileSync(f,'utf8'),"
              "{sourceType:'module',plugins:['jsx']});")
        checked = subprocess.run(["node", "-e", js, *refs],
                                 cwd=ROOT/"frontend", capture_output=True, text=True, timeout=45)
        if checked.returncode:
            raise RuntimeError("Falha na sintaxe React: " + checked.stderr[-500:])


def run(apply=False):
    if not (ROOT/"backend/routes_pix.py").is_file():
        raise RuntimeError("Abra o terminal na raiz /app da RRClub")
    updates = {}
    for name, oldsha, newsha in MANIFEST:
        file = ROOT/name
        if file.is_symlink():
            raise RuntimeError("Symlink não permitido: " + name)
        local = file.read_bytes() if file.is_file() else None
        target = fetch(TARGET, name, newsha)
        if oldsha:
            if local is None:
                raise RuntimeError("Ficheiro original em falta: " + name)
            ancestor = fetch(BASE, name, oldsha)
            output = merge_safe(name, local, ancestor, target)
        else:
            if local not in (None, target):
                raise RuntimeError("Ficheiro local com o mesmo nome: " + name)
            output = target
        if name.endswith(".py"):
            ast.parse(output.decode(), filename=name)
        if output != local:
            updates[name] = output
    validate_js(updates)
    print("Verificação concluída. Ficheiros a atualizar:", len(updates))
    if not apply:
        print("SOMENTE VERIFICAÇÃO: nada foi alterado.")
        return
    backup = Path(tempfile.mkdtemp(prefix="rrclub_paulo_pix_backup_"))
    original = {}
    for name in updates:
        file = ROOT/name
        original[name] = file.read_bytes() if file.exists() else None
        if file.exists():
            dest = backup/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)
    try:
        for name, data in updates.items():
            dest = ROOT/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name+".rrclub-stage")
            try:
                tmp.write_bytes(data)
                if dest.exists():
                    tmp.chmod(dest.stat().st_mode & 0o777)
                os.replace(tmp, dest)
            finally:
                tmp.unlink(missing_ok=True)
    except Exception:
        for name, prior in original.items():
            dest=ROOT/name
            if prior is None:
                dest.unlink(missing_ok=True)
            else:
                dest.write_bytes(prior)
        raise
    print("RRCLUB: correção de estado Pix Connect do Paulo preparada.")
    print("Backup:", backup)
    print("Nenhuma conta, associação financeira, Pix, Stripe ou deploy alterado.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    opt = parser.add_mutually_exclusive_group(required=True)
    opt.add_argument("--check", action="store_true")
    opt.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        run(args.apply)
    except Exception as exc:
        print("PARADO:", str(exc))
        sys.exit(1)
