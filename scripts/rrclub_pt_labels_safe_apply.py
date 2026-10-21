#!/usr/bin/env python3
"""RRClub: show PT-01/PT-02 labels without changing transfers or Stripe accounts."""
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
REPOSITORY = "faellt34/NOVORRCLUB"
BASE = "eac62c635f108cf7e54ba876208016eb3b49fb18"
TARGET = "bb997ecb38086f9fa512c06c58c00bf091436aee"
FILES = [
    ("backend/pt_split.py",
     "dc88657f8fa96206f6ea1e540de3a68812685f6a",
     "4a88121cf9b2d204911e2379c7a7269bf322c78a"),
    ("frontend/src/components/PortugalSplitPanel.jsx",
     "79e8d3adbb57cdb33cafd1ffcb197a734399cf90",
     "5dac24dea03110f6dcb738054683e5a9313f7028"),
    ("scripts/rrclub_pt_live_eligibility_audit.py",
     "16e47491528abdd6654ce4a621b549cb04e45b35",
     "2cc210df7feed9842ae6df4cfe14f6b17191c955"),
    ("backend/tests/test_pt_connect_aliases.py", None,
     "ba4586499ca7908f26f873f209b1e1336fdbb32f"),
]

def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def fetch(ref, filename, expected):
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{ref}/{filename}"
    with urlopen(Request(url, headers={"User-Agent": "RRClub-safe-pt-labels"}), timeout=30) as response:
        data = response.read(700001)
    if len(data) > 700000 or blob_sha(data) != expected:
        raise RuntimeError(f"Integridade GitHub nao validada: {filename}")
    return data

def merge(name, current, ancestor, desired):
    if current == desired:
        return current
    if current == ancestor:
        return desired
    with tempfile.TemporaryDirectory(prefix="rrclub_merge_") as directory:
        files = [Path(directory) / f for f in ("current", "base", "target")]
        for file, data in zip(files, (current, ancestor, desired)):
            file.write_bytes(data)
        process = subprocess.run(
            ["git", "merge-file", "-p", *map(str, files)], capture_output=True, timeout=30
        )
        if process.returncode:
            raise RuntimeError("Conflito com trabalho local, nenhum ficheiro alterado: " + name)
        return process.stdout

def run(apply):
    if not (ROOT / "backend/server.py").is_file():
        raise RuntimeError("Nao encontrei /app/backend/server.py")
    changes = {}
    for filename, oldsha, newsha in FILES:
        local = ROOT / filename
        if local.is_symlink():
            raise RuntimeError("Symlink inesperado: " + filename)
        current = local.read_bytes() if local.is_file() else None
        desired = fetch(TARGET, filename, newsha)
        if oldsha:
            if current is None and filename.startswith("backend/"):
                raise RuntimeError("Ficheiro backend em falta: " + filename)
            if current is None:
                result = desired
            else:
                ancestor = fetch(BASE, filename, oldsha)
                result = merge(filename, current, ancestor, desired)
        else:
            if current is not None and current != desired:
                raise RuntimeError("Novo ficheiro conflita com personalizacao: " + filename)
            result = desired
        if filename.endswith(".py"):
            ast.parse(result.decode(), filename=filename)
        if current != result:
            changes[filename] = result
    print(f"PT-01/PT-02: {len(changes)} ficheiros preparados, sem conflitos.")
    if not apply:
        print("SOMENTE VERIFICACAO: sem modificacoes.")
        return
    folder = Path(tempfile.mkdtemp(prefix="rrclub_pt_labels_backup_"))
    original = {}
    for filename in changes:
        path = ROOT / filename
        original[filename] = path.read_bytes() if path.is_file() else None
        if path.is_file():
            out = folder / filename
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, out)
    try:
        for filename, data in changes.items():
            path = ROOT / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".pt-label-stage")
            tmp.write_bytes(data)
            if path.exists():
                tmp.chmod(path.stat().st_mode & 0o777)
            os.replace(tmp, path)
    except Exception:
        for filename, data in original.items():
            path = ROOT / filename
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        raise
    print("RRCLUB: etiquetas PT-01/PT-02 e diagnostico de contexto aplicados.")
    print("Backup:", folder)
    print("Sem .env, Pix, Stripe, split, pagamentos, movimentos ou deploy alterados.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    try:
        run(args.apply)
    except Exception as exc:
        print("PARADO:", str(exc))
        sys.exit(1)
