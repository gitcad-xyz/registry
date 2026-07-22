"""Registry machine gates (ADR-0010) — run on every PR, and locally.

Checks every published part and the index:

1. every ``parts/<name>/<version>/part.json`` parses as a PartManifest
2. directory name/version match the manifest exactly
3. all versions of one part share one stable part id
4. interface-semver holds between consecutive versions (check_release) —
   a moved port cannot enter the registry as a patch
5. ``index.json`` matches a fresh regeneration (run with ``--fix`` to update)

Immutability of already-published files is enforced by the workflow's git
diff (a published part.json is never edited — publish a new version).

Usage:  python scripts/validate.py [--fix]
Exit 0 = registry sound.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from gitcad.canonical import canonical_json
from gitcad.part import PartManifest, check_release
from gitcad.part.semver import Version

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "parts"
INDEX = ROOT / "index.json"


def main() -> int:
    fix = "--fix" in sys.argv
    problems: list[str] = []
    index: dict[str, dict] = {}

    for name_dir in sorted(p for p in PARTS.iterdir() if p.is_dir()):
        name = name_dir.name
        manifests: dict[str, PartManifest] = {}
        for ver_dir in sorted(p for p in name_dir.iterdir() if p.is_dir()):
            pj = ver_dir / "part.json"
            if not pj.exists():
                problems.append(f"{name}/{ver_dir.name}: missing part.json")
                continue
            try:
                m = PartManifest.loads(pj.read_text(encoding="utf-8"))
            except Exception as exc:
                problems.append(f"{name}/{ver_dir.name}: does not parse: {exc}")
                continue
            if m.name != name:
                problems.append(f"{name}/{ver_dir.name}: manifest name {m.name!r} != directory")
            if m.version != ver_dir.name:
                problems.append(f"{name}/{ver_dir.name}: manifest version {m.version!r} != directory")
            manifests[m.version] = m

        ids = {m.id for m in manifests.values()}
        if len(ids) > 1:
            problems.append(f"{name}: versions disagree on part id: {sorted(ids)}")

        for v, m in manifests.items():
            body = m.body or {}
            if body.get("kind") == "mpn-component":
                fp_dep = body.get("footprint", "")
                if fp_dep not in m.deps:
                    problems.append(f"{name}/{v}: mpn-component footprint not in deps")
                ds = body.get("datasheet")
                if ds is None:
                    print(f"  note: {name}/{v} has no datasheet anchor (draft tier)")
                else:
                    import re as _re
                    if "url" not in ds or not _re.fullmatch(r"[0-9a-f]{64}", ds.get("sha256", "")):
                        problems.append(f"{name}/{v}: malformed datasheet anchor")
                if not m.interface.ports:
                    problems.append(f"{name}/{v}: component has no ports")

        ordered = sorted(manifests, key=Version.parse)
        for old_v, new_v in zip(ordered, ordered[1:]):
            violations = check_release(old_v, new_v,
                                       manifests[old_v].interface,
                                       manifests[new_v].interface)
            for v in violations:
                problems.append(f"{name}: {old_v} -> {new_v}: {v}")

        if manifests:
            any_m = next(iter(manifests.values()))
            index[name] = {
                "id": any_m.id,
                "versions": {v: {"content": manifests[v].content_hash()} for v in ordered},
                "latest": ordered[-1],
                "domain": any_m.domain,
            }

    index_text = canonical_json({"schema": "gitcad/registry-index@1", "parts": index},
                                indent=2) + "\n"
    if fix:
        INDEX.write_text(index_text, newline="\n", encoding="utf-8")
        print("index.json written")
    elif not INDEX.exists() or INDEX.read_text(encoding="utf-8") != index_text:
        problems.append("index.json is stale — run: python scripts/validate.py --fix")

    if problems:
        print(f"REGISTRY INVALID ({len(problems)} problems):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"registry sound: {len(index)} parts, "
          f"{sum(len(e['versions']) for e in index.values())} published versions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
