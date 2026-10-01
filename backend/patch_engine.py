import os
import re

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse(diff: str) -> list[dict]:
    files, cur = [], None
    for line in diff.splitlines():
        if line.startswith("--- "):
            cur = {"old": line[4:].strip(), "new": None, "hunks": []}
        elif line.startswith("+++ ") and cur is not None:
            cur["new"] = line[4:].strip(); files.append(cur)
        elif HUNK.match(line) and cur is not None:
            m = HUNK.match(line)
            cur["hunks"].append({"start": int(m.group(1)), "lines": []})
        elif cur is not None and cur["hunks"] and line[:1] in ("+", "-", " ", "\\"):
            if not line.startswith("\\"):
                cur["hunks"][-1]["lines"].append(line)
        elif cur is not None and cur["hunks"] and line == "":
            cur["hunks"][-1]["lines"].append(" ")
    return files


def _rel(p: str, strip: int) -> str:
    parts = p.split("/")
    return "/".join(parts[strip:]) if len(parts) > strip else p


def _apply_hunks(src: list[str], hunks: list[dict]) -> list[str]:
    out, pos, offset = [], 0, 0
    for h in hunks:
        old = [l[1:] for l in h["lines"] if l[0] in (" ", "-")]
        new = [l[1:] for l in h["lines"] if l[0] in (" ", "+")]
        want = h["start"] - 1 + offset
        idx = None
        for cand in sorted(range(len(src) - len(old) + 1), key=lambda i: abs(i - want)):
            if cand >= pos and src[cand:cand + len(old)] == old:
                idx = cand; break
        if idx is None:
            raise ValueError(f"contexto do hunk @@ -{h['start']} @@ não encontrado no ficheiro atual")
        out.extend(src[pos:idx]); out.extend(new)
        pos = idx + len(old); offset += len(new) - len(old)
    out.extend(src[pos:])
    return out


def run(diff: str, root: str, strip: int = 1, write: bool = False, roots: list[str] | None = None) -> dict:
    files = parse(diff)
    if not files or not any(f["hunks"] for f in files):
        return {"ok": False, "erro": "diff sem ficheiros/hunks reconhecíveis"}
    results, touched = {}, []
    for f in files:
        name = f["new"] or f["old"]
        path, rel = None, _rel(name, strip)
        for base in (roots or [root]):
            for st in (strip, 0, 2):
                cand = os.path.join(base, _rel(name, st))
                if os.path.isfile(cand):
                    path, rel = cand, os.path.relpath(cand, root); break
            if path:
                break
        if not path:
            return {"ok": False, "erro": f"ficheiro {rel} não existe"}
        with open(path, encoding="utf-8", errors="ignore") as fh:
            src = fh.read().split("\n")
        try:
            results[path] = _apply_hunks(src, f["hunks"])
        except ValueError as e:
            return {"ok": False, "erro": f"{rel}: {e}"}
        touched.append(rel)
    if write:
        for path, lines in results.items():
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
    return {"ok": True, "ficheiros": touched}
