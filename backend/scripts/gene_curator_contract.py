"""Pin and drift-check Gene Curator's curation export contract (#448).

    uv run python scripts/gene_curator_contract.py SOURCE --check           # no writes
    uv run python scripts/gene_curator_contract.py SOURCE --pin "gc@<sha>"  # rewrite snapshot

SOURCE is Gene Curator's /openapi.json, as a URL or a file. The snapshot holds
CurationExportPage and every schema it references. Fields Gene Curator adds within
export v1 are reported but pass (the importer ignores unknown fields); a pinned
schema or field that disappears or changes type is drift (exit 1).
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx

SNAPSHOT = Path(__file__).resolve().parents[1] / "contract" / "gene_curator_export.snapshot.json"
ROOT = "CurationExportPage"
PROSE = {"description", "title", "examples"}  # wording, not contract


def _load(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        response = httpx.get(source, timeout=30, follow_redirects=True)
        response.raise_for_status()
        return response.json()
    return json.loads(Path(source).read_text())


def extract(openapi: dict[str, Any]) -> dict[str, Any]:
    """CurationExportPage and the component schemas it references, transitively."""
    components = openapi["components"]["schemas"]
    found: dict[str, Any] = {}
    pending = [ROOT]
    while pending:
        name = pending.pop()
        if name in found:
            continue
        found[name] = components[name]
        pending += re.findall(r'"#/components/schemas/([^"]+)"', json.dumps(found[name]))
    return dict(sorted(found.items()))


def _contract(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _contract(v) for k, v in node.items() if k not in PROSE}
    if isinstance(node, list):
        return [_contract(v) for v in node]
    return node


def drift(pinned: dict[str, Any], current: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(breaking changes, additive changes) from the pinned to the current schemas."""
    breaking: list[str] = []
    added: list[str] = []
    for name, schema in pinned.items():
        if name not in current:
            breaking.append(f"{name}: schema removed")
            continue
        old, new = schema.get("properties", {}), current[name].get("properties", {})
        for field, spec in old.items():
            if field not in new:
                breaking.append(f"{name}.{field}: removed")
            elif _contract(spec) != _contract(new[field]):
                breaking.append(
                    f"{name}.{field}: changed {_contract(spec)} -> {_contract(new[field])}"
                )
        added += [f"{name}.{field}" for field in new if field not in old]
    added += [f"{name}: new schema" for name in current if name not in pinned]
    return breaking, added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", help="Gene Curator /openapi.json URL or file")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="compare only; never writes")
    mode.add_argument("--pin", metavar="LABEL", help="rewrite the snapshot, e.g. gc@<sha>")
    args = parser.parse_args()

    current = extract(_load(args.source))
    if args.pin:
        snapshot = {
            "$comment": f"Gene Curator export v1, pinned from {args.pin}",
            "schemas": current,
        }
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
        print(f"pinned {len(current)} schemas to {SNAPSHOT}")
        return 0

    pinned = json.loads(SNAPSHOT.read_text())
    breaking, added = drift(pinned["schemas"], current)
    for line in added:
        print(f"added (ok, ignored by the importer): {line}")
    for line in breaking:
        print(f"DRIFT: {line}", file=sys.stderr)
    print(f"{pinned['$comment']}: {'drift' if breaking else 'no breaking drift'}")
    return 1 if breaking else 0


if __name__ == "__main__":
    sys.exit(main())
