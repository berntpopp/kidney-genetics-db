#!/usr/bin/env python3
"""Evaluate HPO clinical-group rules against PanelApp kidney panels (#338). Read-only.

Reproduces the validation table of
.planning/specs/2026-10-26-hpo-clinical-groups-v2.md with the production
classifier (app.pipeline.sources.annotations.hpo) on a local copy of the pinned
HPO release. Information content comes from the genes_to_phenotype.txt disease
corpus, as in production.

Reference TSV columns: symbol, stored primary, PanelApp green panels ("|"),
level, NCBI gene ID. A prediction is correct when the primary is one of the
gene's panel groups.

Usage:
    cd backend && uv run python scripts/evaluate_hpo_clinical_groups.py \\
        HPO_DIR REFERENCE_TSV config/datasources.yaml
"""

import argparse
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.sources.annotations.hpo import (  # noqa: E402
    CLINICAL_GROUP_PRIORITY,
    SECONDARY_GROUP_RATIO,
    ClinicalGroupClassifier,
    HPOAnnotationSource,
    load_hpo_parents,
)

# v1 signature terms (datasources.yaml before #338), exact match, score matched/5
V1_SIGNATURES = {
    "complement": ["HP:0000093", "HP:0000100", "HP:0001970", "HP:0000796", "HP:0003259"],
    "cakut": ["HP:0000107", "HP:0000085", "HP:0000089", "HP:0000072", "HP:0000126"],
    "glomerulopathy": ["HP:0000097", "HP:0003774", "HP:0000123", "HP:0000099", "HP:0030888"],
    "cyst_cilio": ["HP:0005562", "HP:0000107", "HP:0001737", "HP:0000092", "HP:0000003"],
    "tubulopathy": ["HP:0003127", "HP:0002900", "HP:0002148", "HP:0000114", "HP:0004918"],
    "nephrolithiasis": ["HP:0000787", "HP:0000121", "HP:0000791", "HP:0008672", "HP:0004724"],
}
RENAL_NEOPLASM = "HP:0009726"

# PanelApp green panels -> clinical group (silver standard)
PANELS = {
    "cakut": ["Congenital anomalies of the kidney and urinary tract (CAKUT)", "CAKUT"],
    "cyst_cilio": [
        "Cystic renal disease",
        "Renal Cystic Disease_SuperPanel",
        "Renal ciliopathies",
        "Renal Ciliopathies and Nephronophthisis",
        "Cystic kidney disease",
        "Renal Macrocystic Disease",
    ],
    "tubulopathy": [
        "Renal Tubulopathies and related disorders",
        "Renal tubulopathies",
        "Monogenic nephrogenic diabetes insipidus",
    ],
    "glomerulopathy": [
        "Renal Glomerular Disease_SuperPanel",
        "Proteinuria",
        "Proteinuric renal disease",
        "Haematuria_Alport",
    ],
    "complement": ["Membranoproliferative glomerulonephritis including C3 glomerulopathy"],
    "nephrolithiasis": ["Nephrocalcinosis or nephrolithiasis"],
    "neoplasia": [
        "Kidney Cancer",
        "Renal cancer pertinent cancer susceptibility",
        "Inherited renal cancer",
    ],
}
KEY_GENES = ["HNF1B", "VHL", "FH", "PALB2", "FANCA", "TSC2", "CFH", "COL4A5", "PKD1", "WT1"]


def _pick(scores: dict[str, float]) -> str | None:
    best = max(scores.values())
    return next(k for k in CLINICAL_GROUP_PRIORITY if scores[k] == best) if best > 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("hpo_dir", type=Path, help="dir with genes_to_phenotype.txt and hp.json")
    parser.add_argument("reference", type=Path, help="reference TSV (see module docstring)")
    parser.add_argument("datasources", type=Path, help="backend/config/datasources.yaml")
    args = parser.parse_args()

    hpo = yaml.safe_load(args.datasources.read_text())["datasources"]["HPO"]
    roots = {k: v["root_terms"] for k, v in hpo["clinical_groups"].items()}
    bulk = HPOAnnotationSource.parse_bulk_file(
        HPOAnnotationSource.__new__(HPOAnnotationSource),
        args.hpo_dir / "genes_to_phenotype.txt",
    )
    parents = load_hpo_parents(args.hpo_dir / "hp.json")
    corpus: dict[str, set[str]] = {}
    for gene in bulk.values():
        for disease, terms in gene["disease_terms"].items():
            corpus.setdefault(disease, set()).update(terms)

    def classifier(groups: dict[str, list[str]], use_ic: bool) -> ClinicalGroupClassifier:
        c = ClinicalGroupClassifier(parents, groups, hpo["hpo_release"])
        c.fit_information_content(corpus.values())
        if not use_ic:
            c.ic = dict.fromkeys(c.ic, 1.0)
        return c

    def disease_terms(symbol: str, use_freq: bool) -> dict[str, dict[str, float]]:
        dt = bulk.get(symbol, {}).get("disease_terms", {})
        return dt if use_freq else {d: dict.fromkeys(t, 1.0) for d, t in dt.items()}

    def gene_terms(symbol: str) -> set[str]:
        return set().union(*disease_terms(symbol, True).values())

    v2 = classifier(roots, use_ic=True)
    v2_flat = classifier(roots, use_ic=False)
    v1_roots = classifier({**V1_SIGNATURES, "neoplasia": [RENAL_NEOPLASM]}, use_ic=True)

    def v1(symbol: str, neoplasia: bool) -> str | None:
        terms = gene_terms(symbol)
        scores = {k: len(terms & set(v)) / len(v) for k, v in V1_SIGNATURES.items()}
        under = sum(1 for t in terms if RENAL_NEOPLASM in v2.ancestors(t))
        scores["neoplasia"] = min(under, 5) / 5 if neoplasia else 0.0
        return _pick(scores)

    rules: dict[str, Callable[[str], str | None]] = {
        "v1 (current)": lambda s: v1(s, False),
        "v1 + neoplasia, same scale": lambda s: v1(s, True),
        "v2 roots, count only": lambda s: v2_flat.classify(disease_terms(s, False))["primary"],
        "v2 roots, IC only": lambda s: v2.classify(disease_terms(s, False))["primary"],
        "v2 roots, frequency only": lambda s: v2_flat.classify(disease_terms(s, True))["primary"],
        "v2 roots, frequency x IC (this spec)": lambda s: v2.classify(disease_terms(s, True))[
            "primary"
        ],
        "v1 terms, frequency x IC": lambda s: v1_roots.classify(disease_terms(s, True))["primary"],
    }

    panel_group = {p: k for k, ps in PANELS.items() for p in ps}
    genes = []
    for line in args.reference.read_text().splitlines():
        symbol, _stored, panels, _level, _ncbi = line.split("\t")
        genes.append((symbol, {panel_group[p] for p in panels.split("|") if p in panel_group}))
    reference = [(s, ref) for s, ref in genes if ref]

    print(f"HPO release {hpo['hpo_release']}: {len(corpus)} diseases (IC corpus)")
    print(f"Genes: {len(genes)}; with a PanelApp group: {len(reference)}")
    print(f"Reference sizes: {dict(Counter(k for _, ref in reference for k in ref))}\n")
    print("| Rule | Top-1 in panel groups | Macro-F1 |\n|---|---|---|")
    for name, rule in rules.items():
        pred = {s: rule(s) for s, _ in reference}
        hits = sum(pred[s] in ref for s, ref in reference)
        f1 = []
        for group in PANELS:
            tp = sum(pred[s] == group and group in ref for s, ref in reference)
            fp = sum(pred[s] == group and group not in ref for s, ref in reference)
            fn = sum(group in ref and pred[s] not in ref for s, ref in reference)
            f1.append(round(2 * tp / (2 * tp + fp + fn), 2) if tp else 0.0)
        print(f"| {name} | {hits / len(reference):.1%} | {sum(f1) / len(f1):.2f} |")

    multi = [(s, ref) for s, ref in reference if len(ref) >= 2]
    recovered = extra = labels = 0
    for symbol, ref in multi:
        result = v2.classify(disease_terms(symbol, True))
        predicted = {result["primary"], *result["secondary"]} - {None}
        recovered += len(predicted & ref)
        extra += len(predicted - ref)
        labels += len(ref)
    print(
        f"\nSecondary groups (>= {SECONDARY_GROUP_RATIO} x primary evidence), {len(multi)} genes"
        f" with >= 2 panel groups: {recovered}/{labels} panel labels recovered, {extra} extra"
    )
    print("\n| Gene | Primary | Secondary | Evidence share of primary |\n|---|---|---|---|")
    for symbol in KEY_GENES:
        result = v2.classify(disease_terms(symbol, True))
        ev = result["evidence"]
        top = ev[result["primary"]] if result["primary"] else 1.0
        shares = ", ".join(
            f"{k} {v / top:.2f}" for k, v in sorted(ev.items(), key=lambda kv: -kv[1]) if v > 0
        )
        print(f"| {symbol} | {result['primary']} | {', '.join(result['secondary'])} | {shares} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
