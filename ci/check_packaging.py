"""Check the built wheel, not the source (bricks#25).

Two defects this makes impossible to miss:
  * a module-scope third-party import in src/ that the wheel's Requires-Dist
    does not declare (a fresh install crashes on import);
  * a Requires-Dist entry with no upper bound (one unbounded release upstream
    breaks every fresh install). Names in ci/unbounded_ok.txt are exempt.

Usage: python ci/check_packaging.py [--json] [--dist dist] [--src src] [--unbounded-ok ci/unbounded_ok.txt]
Exit 0: ok. Exit 1: problems (each names the package and the fix). Exit 2: no wheel to read.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import zipfile
from email.parser import Parser
from pathlib import Path

from packaging.requirements import Requirement


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _module_scope_imports(tree: ast.Module) -> set[str]:
    """Dotted names imported at module scope (also inside module-level if/try/with, never in def/class)."""
    found: set[str] = set()

    def walk(stmts: list[ast.stmt]) -> None:
        for node in stmts:
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    found.add(node.module)
            elif isinstance(node, (ast.If, ast.Try, ast.With)):
                for field in ("body", "orelse", "finalbody"):
                    walk(getattr(node, field, []))
                for handler in getattr(node, "handlers", []):
                    walk(handler.body)

    walk(tree.body)
    return found


def _third_party_imports(src: Path) -> dict[str, str]:
    """Map import name -> first file that imports it, for non-stdlib, non-local modules."""
    local = {p.name for p in src.iterdir() if p.is_dir() or p.suffix == ".py"} | {p.stem for p in src.glob("*.py")}
    out: dict[str, str] = {}
    for path in sorted(src.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for dotted in _module_scope_imports(tree):
            top = dotted.split(".")[0]
            if top in sys.stdlib_module_names or top in local or top == "__future__":
                continue
            out.setdefault(dotted, path.as_posix())
    return out


def _requires_dist(wheel: Path) -> list[Requirement]:
    with zipfile.ZipFile(wheel) as zf:
        member = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        meta = Parser().parsestr(zf.read(member).decode("utf-8"))
    return [Requirement(line) for line in meta.get_all("Requires-Dist") or []]


def _has_upper_bound(req: Requirement) -> bool:
    return any(spec.operator in ("<", "<=", "==", "~=") for spec in req.specifier)


def _allowed(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    names = (line.split("#")[0].strip() for line in path.read_text(encoding="utf-8").splitlines())
    return {_norm(n) for n in names if n}


def check(dist: Path, src: Path, unbounded_ok: Path) -> list[str]:
    wheels = sorted(dist.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError(f"no wheel in {dist}/; run: python -m build")
    reqs = [r for r in _requires_dist(wheels[-1]) if not (r.marker and "extra" in str(r.marker))]
    declared = {_norm(r.name) for r in reqs}
    problems: list[str] = []
    for dotted, where in sorted(_third_party_imports(src).items()):
        parts = dotted.split(".")
        candidates = {_norm(parts[0]), _norm(".".join(parts[:2]))}
        if not candidates & declared:
            problems.append(
                f"{parts[0]}: imported at module scope in {where} but not in Requires-Dist; "
                f"add it to `dependencies` in pyproject.toml"
            )
    ok = _allowed(unbounded_ok)
    for req in reqs:
        if not _has_upper_bound(req) and _norm(req.name) not in ok:
            problems.append(
                f"{req.name}: no upper bound in `{req}`; add one in `dependencies` in pyproject.toml "
                f"(e.g. <next major), or list it in {unbounded_ok.as_posix()} with a # reason"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="print one JSON document")
    ap.add_argument("--dist", type=Path, default=Path("dist"))
    ap.add_argument("--src", type=Path, default=Path("src"))
    ap.add_argument("--unbounded-ok", type=Path, default=Path("ci/unbounded_ok.txt"))
    args = ap.parse_args(argv)
    try:
        problems = check(args.dist, args.src, args.unbounded_ok)
    except FileNotFoundError as exc:
        if args.json:
            print(json.dumps({"ok": False, "problems": [str(exc)]}))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems}))
    elif problems:
        print("\n".join(f"FAIL {p}" for p in problems))
    else:
        print("packaging ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
