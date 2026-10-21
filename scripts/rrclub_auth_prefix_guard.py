#!/usr/bin/env python3
"""Recover ONLY accidental JSON/terminal text pasted before routes_auth.py imports.

No Git reset, no financial changes, no deployment, no remote calls.
This cannot repair arbitrary source changes; on ambiguity, it stops.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
FILE = ROOT / "backend/routes_auth.py"
ANCHOR = "from datetime import datetime, timezone, timedelta"
STANDARD_START = "import re\n" + ANCHOR
EXPECTED_NEXT = "from typing import Optional, Literal"

def repair_candidate(data: str):
    # Valid source must be preserved byte-for-byte, including legitimate local changes.
    try:
        ast.parse(data, filename=str(FILE))
        return data, "already_valid"
    except SyntaxError:
        pass
    anchor_at = data.find(ANCHOR)
    if not (0 <= anchor_at <= 1024):
        raise RuntimeError("Nao consigo identificar o inicio seguro dos imports. Corrigir manualmente.")
    prefix = data[:anchor_at]
    # Require positive evidence of accidental API output before touching any file.
    if not any(marker in prefix for marker in ('Robson Club API', '"status":"ok"', "'status':'ok'")):
        raise RuntimeError("Sintaxe invalida, mas nao corresponde ao texto JSON observado. Parar.")
    suffix = data[anchor_at:]
    if EXPECTED_NEXT not in suffix[:280]:
        raise RuntimeError("Bloco de imports alterado. Nao reescrever automaticamente.")
    proposed = "import re\n" + suffix
    try:
        tree = ast.parse(proposed, filename=str(FILE))
    except SyntaxError as exc:
        raise RuntimeError("Ainda existem erros de sintaxe alem do cabecalho: " + str(exc)) from exc
    if "router = APIRouter(prefix=\"/auth\")" not in proposed:
        raise RuntimeError("Rotas de autenticacao ausentes; nao substituir.")
    functions = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if not {"login", "me", "logout"}.issubset(functions):
        raise RuntimeError("Funcoes essenciais de autenticacao ausentes; nao substituir.")
    return proposed, "corrupted_json_prefix"

def main():
    p = argparse.ArgumentParser()
    opts = p.add_mutually_exclusive_group(required=True)
    opts.add_argument("--check", action="store_true")
    opts.add_argument("--repair", action="store_true")
    args = p.parse_args()
    if not FILE.is_file() or FILE.is_symlink():
        raise RuntimeError("Ficheiro regular backend/routes_auth.py nao encontrado.")
    raw = FILE.read_bytes()
    source = raw.decode("utf-8")
    target, state = repair_candidate(source)
    print("routes_auth.py:", state)
    if target == source:
        print("Nenhuma alteracao necessaria.")
        return
    print("JSON indevido detectado no cabecalho; restante ficheiro preservado.")
    if args.check:
        print("SOMENTE VERIFICACAO: executar --repair para corrigir.")
        return
    folder = Path(tempfile.mkdtemp(prefix="rrclub_auth_backup_"))
    backup = folder / "routes_auth.py"
    shutil.copy2(FILE, backup)
    staged = FILE.with_name("routes_auth.py.rrclub-stage")
    try:
        staged.write_text(target, encoding="utf-8")
        staged.chmod(FILE.stat().st_mode & 0o777)
        os.replace(staged, FILE)
    finally:
        staged.unlink(missing_ok=True)
    print("CORRIGIDO: apenas cabecalho acidental do routes_auth.py")
    print("Backup:", backup)
    print("SHA256 antes:", hashlib.sha256(raw).hexdigest())
    print("SHA256 depois:", hashlib.sha256(FILE.read_bytes()).hexdigest())
    print("Fazer compileall/backend e build/frontend antes de deploy.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("PARADO:", exc)
        sys.exit(1)
