#!/usr/bin/env python3
"""Apply RRClub P5 Portugal MB WAY fix to an Emergent checkout with backup.

Only backend/p5_checkout.py may change. This is never a Stripe charge or deploy.
The local version is merged safely; on conflict/syntax failure nothing is saved.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
FILE = Path("backend/p5_checkout.py")
REPO = "faellt34/NOVORRCLUB"
BASE_COMMIT = "031498cff26cdaf61ad27982c6e80231783addec"
TARGET_COMMIT = "3f25892ee6b39b8a5f21534267f2cb2b04214fa7"
BASE_SHA = "ecbb368892ff33ac9f69acf53736847f7a31c98a"
TARGET_SHA = "89134b00a49b199b0f02b7b7f60c1549b2b0711a"


def blob_sha(contents):
    return hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\0" + contents).hexdigest()


def from_repo(commit, expected):
    url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{FILE}"
    with urlopen(Request(url, headers={"User-Agent": "RRClub-P5-MBWAY-Verified"}), timeout=30) as response:
        contents = response.read(110001)
    if len(contents) > 110000 or blob_sha(contents) != expected:
        raise RuntimeError("Código remoto não corresponde à versão validada no GitHub")
    return contents


def prepare(local):
    previous = from_repo(BASE_COMMIT, BASE_SHA)
    corrected = from_repo(TARGET_COMMIT, TARGET_SHA)
    if local == corrected:
        return local
    if local == previous:
        return corrected
    with tempfile.TemporaryDirectory(prefix="rrclub_pt_mbway_merge_") as directory:
        paths = [Path(directory) / x for x in ("local", "base", "target")]
        for p, content in zip(paths, [local, previous, corrected]):
            p.write_bytes(content)
        merge = subprocess.run(
            ["git", "merge-file", "-p", *map(str, paths)],
            capture_output=True, timeout=30
        )
        if merge.returncode:
            raise RuntimeError("Conflito com personalizações locais: nada alterado")
        result = merge.stdout
    if b'<<<<<<<' in result or b'>>>>>>>' in result:
        raise RuntimeError("Marcadores de conflito detectados; parar")
    return result


def main():
    arg = argparse.ArgumentParser()
    option = arg.add_mutually_exclusive_group(required=True)
    option.add_argument("--check", action="store_true")
    option.add_argument("--apply", action="store_true")
    args = arg.parse_args()
    path = ROOT / FILE
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("backend/p5_checkout.py não encontrado no projeto /app")
    current = path.read_bytes()
    corrected = prepare(current)
    # No payment keys or split eligibility are modified by this patch.
    source = corrected.decode("utf-8")
    compile(source, str(path), "exec")
    if 'payment_method_types=["card", "mb_way"]' not in source:
        raise RuntimeError("MB WAY ausente no checkout a aplicar")
    if 'idempotency_key="p5-" + rec["id"] + "-card"' in source:
        raise RuntimeError("Fallback antigo para cartão ainda existe")
    if current == corrected:
        print("P5 Portugal MB WAY: já corrigido, 0 ficheiros alterados.")
        return
    print("P5 Portugal MB WAY: sintaxe e integridade validadas.")
    if args.check:
        print("SOMENTE VERIFICAÇÃO. Usar --apply para atualizar um ficheiro.")
        return
    backup_dir = Path(tempfile.mkdtemp(prefix="rrclub_pt_mbway_backup_"))
    backup = backup_dir / "p5_checkout.py"
    shutil.copy2(path, backup)
    temp = path.with_name(".p5_checkout.py.stage")
    try:
        temp.write_bytes(corrected)
        temp.chmod(path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    print("CORRIGIDO: P5 MB WAY não muda para cartão sem aviso.")
    print("Backup:", backup)
    print("Nenhum deploy, pagamento, Pix, split ou conta Stripe alterado.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("PARADO:", error)
        sys.exit(1)
