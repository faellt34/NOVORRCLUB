#!/usr/bin/env python3
"""RRClub: repair ONLY accidental shell command lines inside routes_auth.py.

Reads no secrets; no DB, Stripe, deploy, git reset, pip install or server restart.
Preserves local Google login and auth functions; on any doubt, stops untouched.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
AUTH = ROOT / "backend/routes_auth.py"

REQUIRED = {"login", "me", "logout", "register", "google_link"}
SHELL_PREFIX = re.compile(
    r"^\s*(?:(?:cd\s+/app|cd\s+\S+)\s*&&\s*)?"
    r"(?:curl\s+|wget\s+|python3?\s+/tmp/rrclub_|"
    r"python3?\s+-m\s+compileall\b)"
)


def known_paste(line: str) -> bool:
    """A full standalone command, not merely a comment or a Python string."""
    stripped = line.lstrip()
    if stripped.startswith(("#", "'", '"', "print(", "return ")):
        return False
    if not SHELL_PREFIX.search(line):
        return False
    return (
        "raw.githubusercontent.com/faellt34/NOVORRCLUB/" in line
        and ".py" in line
        and any(x in line for x in ("rrclub_", "/tmp/rrclub_", "auth_prefix_guard"))
    )


def check_python(source: str) -> set[str]:
    tree = ast.parse(source, filename=str(AUTH))
    names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if not REQUIRED.issubset(names):
        raise ValueError("Autenticação incompleta: faltam " + ", ".join(sorted(REQUIRED - names)))
    if 'router = APIRouter(prefix="/auth")' not in source:
        raise ValueError("Router de autenticação não identificado")
    if "from core import" not in source:
        raise ValueError("Importações essenciais da autenticação não identificadas")
    return names


def prepare(source: str) -> tuple[str, str, int]:
    try:
        check_python(source)
        return source, "OK: já válido", 0
    except SyntaxError:
        pass
    lines = source.splitlines(keepends=True)
    bad = [i for i, line in enumerate(lines) if known_paste(line)]
    if not bad or len(bad) > 3:
        raise ValueError("Sintaxe inválida, mas não encontrei uma colagem de comando conhecida. Nada alterado.")
    clean = "".join(line for i, line in enumerate(lines) if i not in bad)
    try:
        check_python(clean)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(
            "A remoção da colagem NÃO basta para validar toda a autenticação. "
            "Não substituí o ficheiro. Detalhe: " + str(exc)[:220]
        ) from exc
    return clean, "COLAGEM DETETADA", len(bad)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repair", action="store_true", help="Apply only when 100% validated")
    args = p.parse_args()
    if not AUTH.is_file() or AUTH.is_symlink():
        raise ValueError("backend/routes_auth.py não é um ficheiro regular")
    source = AUTH.read_text(encoding="utf-8")
    target, result, count = prepare(source)
    print("RRCLUB AUTH —", result)
    print("Linhas de comando acidentais:", count)
    if target == source:
        print("Autenticação íntegra; nenhuma alteração.")
        return
    if not args.repair:
        print("Só verificação; execute --repair para aplicar.")
        return
    backup_dir = Path(tempfile.mkdtemp(prefix="rrclub_auth_backup_20261022_", dir="/tmp"))
    backup = backup_dir / AUTH.name
    shutil.copy2(AUTH, backup)
    staged = AUTH.with_name(AUTH.name + ".rrclub-guard-stage")
    old_bytes = AUTH.read_bytes()
    try:
        staged.write_text(target, encoding="utf-8")
        staged.chmod(AUTH.stat().st_mode & 0o777)
        check_python(staged.read_text(encoding="utf-8"))
        # Reject writing if someone changed the file after we read it.
        if AUTH.read_bytes() != old_bytes:
            raise RuntimeError("Ficheiro alterado durante a verificação; nada substituído.")
        os.replace(staged, AUTH)
        check_python(AUTH.read_text(encoding="utf-8"))
    finally:
        staged.unlink(missing_ok=True)
    print("APROVADO: removidas apenas", count, "linha(s) de comando do routes_auth.py")
    print("BACKUP:", backup)
    print("SHA256 anterior:", hashlib.sha256(old_bytes).hexdigest()[:12])
    print("SHA256 atual:", hashlib.sha256(AUTH.read_bytes()).hexdigest()[:12])
    print("SEM deploy, cobranças ou alterações Stripe.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("PARADO EM SEGURANÇA:", str(exc))
        sys.exit(1)
