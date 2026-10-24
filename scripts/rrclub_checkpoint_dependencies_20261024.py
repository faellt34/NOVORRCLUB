#!/usr/bin/env python3
"""RRClub: checkpoint safely referenced, untracked runtime modules. No deployment or Stripe calls."""
import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/app")
FRONT = ROOT / "frontend"
EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".json"}

def git(*args):
    p = subprocess.run(["git", "--no-pager", *args], cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError("Git: " + p.stderr[-350:])
    return p.stdout

def gitfiles(*args):
    p = subprocess.run(["git", *args, "-z"], cwd=ROOT, capture_output=True)
    if p.returncode:
        raise RuntimeError("Falha ao listar arquivos Git")
    return [x.decode("utf-8", "surrogateescape") for x in p.stdout.split(b"\0") if x]

def runtime(name):
    p = Path(name)
    return (name.startswith(("backend/", "frontend/src/"))
            and p.suffix in EXTS and "/tests/" not in name and ".test." not in p.name
            and not any(x.lower() in {"secrets", "credentials", "private", "keys", "backups", "node_modules"} for x in p.parts)
            and not p.name.startswith(".") and p.name != "package-lock.json")

def imports(target, source, sourcepath):
    f = Path(target)
    if f.suffix == ".py":
        stem = re.escape(f.stem)
        return bool(re.search(r"(?m)^\s*(?:from\s+" + stem + r"\s+import\b|import\s+" + stem + r"(?:\s|,|\.|$))", source))
    refs = re.findall(r"""(?:\bfrom\s*|\bimport\s*\(\s*|\brequire\s*\(\s*|\bimport\s*)['"]([^'"]+)['"]""", source)
    for ref in refs:
        if ref.startswith("@/"):
            base = Path("frontend/src") / ref[2:]
        elif ref.startswith("."):
            base = Path(os.path.normpath(str(Path(sourcepath).parent / ref)))
        else:
            continue
        possibles = {str(base)}
        possibles |= {str(base) + x for x in (".js", ".jsx", ".ts", ".tsx", ".css", ".json")}
        possibles |= {str(base / ("index" + x)) for x in (".js", ".jsx", ".ts", ".tsx")}
        if target in possibles:
            return True
    return False

def main():
    print("=== RRCLUB | CONSOLIDAR DEPENDENCIAS P5 ===", flush=True)
    if not (ROOT / ".git").is_dir():
        raise RuntimeError("Repositorio Git nao encontrado em /app")
    if git("diff", "--cached", "--name-only").strip():
        raise RuntimeError("Ha arquivos em stage; preservar antes de prosseguir.")
    pending = gitfiles("ls-files", "--others", "--exclude-standard")
    operational = sorted(n for n in pending if runtime(n))
    tracked = gitfiles("ls-files")
    sources = []
    for name in tracked + operational:
        p = ROOT / name
        if runtime(name) and p.is_file() and not p.is_symlink():
            try:
                sources.append((name, p.read_text(encoding="utf-8")))
            except (UnicodeError, OSError):
                pass
    required, deferred = [], []
    for filename in operational:
        refs = [n for n, content in sources if n != filename and imports(filename, content, n)]
        (required if refs else deferred).append(filename)
        print(("IMPORTADO: " if refs else "PRESERVADO SEM REFERENCIA: ") + filename, flush=True)
    print("Arquivos operacionais fora do Git:", len(operational))
    print("Dependencias identificadas:", len(required))
    print("Arquivos para revisao futura:", len(deferred))
    if not required:
        print("Nenhuma dependencia nova identificada; nada alterado.")
        return
    for name in required:
        p = ROOT / name
        if not p.is_file() or p.is_symlink():
            raise RuntimeError("Arquivo especial nao permitido: " + name)
        data = p.read_bytes()
        if len(data) > 500000 or b"\0" in data:
            raise RuntimeError("Arquivo grande/binario: " + name)
        if re.search(rb"(?i)(?:sk_live_|rk_live_|whsec_)[A-Za-z0-9]{12,}", data):
            raise RuntimeError("Possivel segredo Stripe: " + name)
        if p.suffix == ".py":
            ast.parse(data.decode("utf-8"), filename=name)
    if any(x.startswith("frontend/src/") for x in required):
        npm = shutil.which("npm")
        if not npm or not (FRONT / "node_modules/.bin/craco").is_file():
            raise RuntimeError("Dependencias frontend ausentes: build nao pode ser validado.")
        print("Validando build frontend, sem criar pagamentos...", flush=True)
        r = subprocess.run([npm, "run", "build"], cwd=FRONT,
                           env={**os.environ, "CI": "true"},
                           capture_output=True, text=True, timeout=300)
        if r.returncode:
            print((r.stdout + r.stderr)[-3500:])
            raise RuntimeError("Build frontend falhou; arquivos preservados.")
        print("Build frontend: OK", flush=True)
    try:
        git("add", "--", *required)
        git("diff", "--cached", "--check")
        git("-c", "user.name=faellt34", "-c",
            "user.email=329758697+faellt34@users.noreply.github.com",
            "commit", "-m", "fix(P5): incluir dependencias operacionais utilizadas")
    except Exception:
        subprocess.run(["git", "restore", "--staged", "--", *required],
                       cwd=ROOT, capture_output=True)
        raise
    print("=== CHECKPOINT DAS DEPENDENCIAS CONCLUIDO ===")
    print(git("log", "-1", "--format=%h | %s").strip())
    print("Arquivos incluidos:", len(required))
    print("Arquivos preservados sem alteracao:", len(pending) - len(required))
    print("Nenhum push, deploy, pagamento, repasse ou segredo executado.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("BLOQUEADO:", str(e))
        print("Nao publique a nova versao ate resolver este bloqueio.")
        sys.exit(1)
