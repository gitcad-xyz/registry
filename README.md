# gitcad registry

The public parts registry for [gitcad](https://gitcad.xyz) — versioned,
content-addressed part definitions with machine-enforced compatibility.

**The registry is a git repo on purpose.** gitcad's thesis is git as the
substrate; a registry is versioned, auditable, content-addressed data — which
is exactly what git is. Same model as Homebrew's formulas or the crates.io
index. Every submission runs the machine gates in CI; every published version
is immutable forever; interface-semver (a moved port can never ship as a
patch) is enforced at publish time, mechanically.

## Layout

```
parts/<name>/<version>/part.json   # one immutable manifest per published version
index.json                         # generated: name -> id, versions, content hashes
```

## Using parts

```python
from gitcad.part import Workspace, resolve

ws = Workspace.from_git("https://github.com/gitcad-xyz/registry")
lock = resolve(my_assembly_manifest, ws)   # pin by content hash, forever
```

## Publishing a part

1. Fork, add `parts/<name>/<version>/part.json` (a gitcad `PartManifest`,
   canonical text — new files only; published versions are immutable).
2. Run `python scripts/validate.py --fix` (updates `index.json`).
3. Open a PR. CI runs the gates: manifest parse, name/version/id consistency,
   **interface-semver against the previous version**, index freshness,
   immutability. Green + review = merged = published.

A GitHub account is currently required to submit ([ADR-0012] — an accountless
relay is designed and staged; this repo is its backend either way).

## Trust tiers (ADR-0010)

`draft` → `verified` → `reviewed` → `proven`. v1: everything merged is
effectively `draft`+`reviewed` (machine gates + human review). Attestation
records land with the verification tooling.

## License

Part **data** in `parts/` is [CC0-1.0](LICENSE) — public domain dedication,
maximally reusable (ADR-0010). Scripts are Apache-2.0 (same as gitcad).

[ADR-0012]: https://github.com/gitcad-xyz/gitcad/blob/main/docs/adr/0012-accountless-contribution.md
