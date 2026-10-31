"""Score curator/judge JSONs with the alpha draft rules and compare to a ClinGen answer key.

usage: python3 -I score_draft.py <round_dir> --it 8   (expects <round_dir>/out and <round_dir>/judge,
and key/answer_key.json next to this file; --it 4..7 reproduce earlier draft iterations)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ORDER = ["no_known", "limited", "moderate", "strong", "definitive"]
CG = {"Definitive": "definitive", "Strong": "strong", "Moderate": "moderate", "Limited": "limited",
      "No Known Disease Relationship": "no_known", "Disputed": "disputed", "Refuted": "refuted"}
CAT = {"probands": (1, 10), "segregation": (1, 3), "cohort": (2, 4), "models": (2, 4), "functional": (1, 2)}


IT = 5  # rule iteration; set via --it
HOUSE = True  # local rule: Moderate+ needs >=4 genetic points


def pts(row, default):
    if not str(row.get("pmid") or "").strip():
        return 0.0
    p = row.get("points", default)
    p = float(p) if isinstance(p, (int, float)) else default
    # it5: compound-het with unknown phase scores 0.5 (it4 rows zeroed only for phase are lifted too)
    if IT >= 5 and row.get("phase") == "unknown" and "/" in str(row.get("variant") or ""):
        if p == 0 and row.get("variant_source") != "not_given" and not row.get("duplicate_of") and row.get("af_checked") is not False:
            p = 0.5
        p = min(p, 0.5)
    return p


NULL = ("null", "lof", "nonsense", "frameshift", "splice_canonical", "canonical splice", "start_loss", "whole_gene_deletion")


EXP_PMIDS = set()  # PMIDs scored as experimental evidence in the current gene (it8: count once)


def allele_pts(a):
    """SOP v12 case-level default: null 1.5; other variant 0.1, +0.4 with functional support."""
    cls = str(a.get("class") or a.get("variant_class") or "").lower()
    if any(t in cls for t in NULL):
        # it8: null not expected to trigger NMD (last exon / last 50 bp of penultimate exon) is downgraded
        return 1.0 if IT >= 8 and a.get("nmd_expected") is False else 1.5
    if a.get("functional_support") is not True:
        return 0.1
    if IT >= 8:
        # it8: upgrade needs a quoted variant-specific result, and the experiment may not also score as experimental evidence
        if not str(a.get("functional_quote") or "").strip():
            return 0.1
        if a.get("also_scored_as_experimental") is True:
            return 0.1  # the same experiment may score once: as allele upgrade OR experimental row
    return 0.5


def proband7(r, moi):
    if not str(r.get("pmid") or "").strip():
        return 0.0
    if isinstance(r.get("points"), (int, float)) and r["points"] == 0:
        return 0.0  # explicit exclusion (not_given, AF, duplicate, wrong entity)
    alleles = r.get("alleles") or [{"class": r.get("variant_class")}]
    biallelic = moi in ("AR", "SD") and (len(alleles) >= 2 or "hom" in str(r.get("zygosity")).lower())
    if biallelic and len(alleles) == 1:
        alleles = alleles * 2  # homozygous
    p = sum(allele_pts(a) for a in alleles[:2]) if biallelic else allele_pts(alleles[0])
    homozygous = biallelic and len({json.dumps(a, sort_keys=True) for a in alleles[:2]}) == 1
    if IT >= 8 and homozygous and r.get("consanguinity") == "yes":
        p = min(p, 2.0)  # it8: homozygous genotype in a consanguineous family (SOP: consider downgrading; ClinGen's modal 3 -> 2)
    if r.get("de_novo") == "confirmed":
        p += 0.5
    if biallelic and r.get("phase") == "unknown" and len({json.dumps(a, sort_keys=True) for a in alleles[:2]}) > 1:
        p *= 0.5  # local rule: compound het, phase unknown, half points (SOP would not score it)
    return min(p, 3.0)


def score7(ev, moi):
    """Iteration 7: SOP-v12-style per-allele case points, SOP experimental categories, no house rule."""
    gen = ev.get("genetic") or {}
    EXP_PMIDS.clear()
    EXP_PMIDS.update(str(r.get("pmid")) for r in (ev.get("experimental") or {}).get("functional") or [])
    by = defaultdict(float)
    for r in gen.get("probands") or []:
        k = " ".join(str(r.get("variant") or id(r)).lower().split()) + "|" + " ".join(str(r.get("population") or "").lower().split())
        by[k] += proband7(r, moi)
    g = min(sum(min(x, 3.0) for x in by.values()), 12)  # recurrent variant within a population: once, max 3
    g += min(sum(pts(r, 1) for r in gen.get("segregation") or []), 3)
    g += min(sum(pts(r, 2) for r in gen.get("cohort") or []), 6)
    g = min(g, 12)
    ex = ev.get("experimental") or {}
    fn = alt = 0.0
    for r in ex.get("functional") or []:
        st = str(r.get("subtype") or "")
        if st in ("patient_cells", "non_patient_cells"):
            alt += pts(r, 1.0 if st == "patient_cells" else 0.5)
        elif st == "rescue":
            pass  # counted with models below
        else:
            fn += pts(r, 0.5)
    mod = sum(pts(r, 2) for r in ex.get("models") or []) + sum(pts(r, 2) for r in ex.get("functional") or [] if r.get("subtype") == "rescue")
    e = min(min(fn, 2) + min(alt, 2) + min(mod, 4), 6)
    total = g + e
    imp = {c.get("impact") for c in ev.get("contradictory_evidence") or []}
    if "refuted" in imp:
        return g, e, total, "refuted"
    if "disputed" in imp:
        return g, e, total, "disputed"
    if g == 0:
        return g, e, total, "no_known"
    if total >= 11.5:
        return g, e, total, "definitive" if ev.get("replicated_over_time") else "strong"
    if total >= 6.5:
        return g, e, total, "moderate"
    return g, e, total, "limited"


def score(ev, moi):
    if IT >= 7:
        return score7(ev, moi)
    sec = {}
    for s, cats in (("genetic", ("probands", "segregation", "cohort")), ("experimental", ("models", "functional"))):
        tot = 0.0
        for c in cats:
            rows = (ev.get(s) or {}).get(c) or []
            if c == "probands":
                # recurrent variant / genotype cap 2. ponytail: AR keyed on whole genotype string, not per allele
                by = defaultdict(float)
                for r in rows:
                    k = " ".join(str(r.get("variant") or id(r)).lower().split())
                    if IT >= 5:
                        k += "|" + " ".join(str(r.get("population") or "").lower().split())
                    by[k] += pts(r, 1)
                v = sum(min(x, 2) for x in by.values())
            else:
                v = sum(pts(r, CAT[c][0]) for r in rows)
            tot += min(v, CAT[c][1])
        sec[s] = min(tot, 12 if s == "genetic" else 6)
    g, e = sec["genetic"], sec["experimental"]
    total = min(g + e, 18)
    impacts = {c.get("impact") for c in ev.get("contradictory_evidence") or []}
    if "refuted" in impacts:
        cls = "refuted"
    elif "disputed" in impacts:
        cls = "disputed"
    elif total >= 12:
        cls = "definitive" if ev.get("replicated_over_time") else "strong"
    elif total >= 7:
        cls = "moderate"
    elif total > 0:
        cls = "limited"
    else:
        cls = "no_known"
    if HOUSE and cls in ("moderate", "strong", "definitive") and g < 4:
        cls = "limited"
    if IT >= 5 and g == 0 and cls not in ("disputed", "refuted"):
        cls = "no_known"
    return g, e, total, cls


def dist(a, b):
    if a in ORDER and b in ORDER:
        return abs(ORDER.index(a) - ORDER.index(b))
    return 0 if a == b else 9


def main(rd):
    rd = Path(rd)
    key = {k["gene"]: k for k in json.load(open(Path(__file__).parent / "key/answer_key.json"))}
    res = []
    for g, k in sorted(key.items()):
        row = {"gene": g, "split": k["split"], "clingen": CG[k["clingen"]]}
        for kind in ("out", "judge"):
            f = rd / kind / f"{g}.json"
            if not f.exists():
                continue
            d = json.load(open(f))
            ev = d.get("corrected_evidence") if kind == "judge" else d.get("evidence")
            if not ev:
                continue
            gs, es, t, c = score(ev, k["moi"])
            eff = d.get("effort") or {}
            secs = (eff.get("finished_at") or 0) - (eff.get("started_at") or 0)
            row[kind] = {"g": gs, "e": es, "t": t, "cls": c, "own": d.get("curator_classification") or d.get("judge_classification"),
                         "secs": secs if 0 < secs < 7200 else None,
                         "calls": (eff.get("mcp_calls") or 0) + (eff.get("shell_calls") or 0) or eff.get("tool_calls"),
                         "wasted": eff.get("wasted_calls"), "blind": d.get("blind_incident"),
                         "exp": d.get("experience")}
        res.append(row)
    json.dump(res, open(rd / f"scores_it{IT}.json", "w"), indent=1)
    print(f"{'gene':10}{'split':8}{'ClinGen':11}{'cur':11}{'pts':>6}{'judge':11}{'pts':>6}{'own':>11}{'sec':>6}{'calls':>6}")
    for r in res:
        o, j = r.get("out", {}), r.get("judge", {})
        mark = lambda x: ("✓" if x.get("cls") == r["clingen"] else "~" if dist(x.get("cls"), r["clingen"]) == 1 else "✗") if x else " "
        print(f"{r['gene']:10}{r['split']:8}{r['clingen']:11}{mark(o)}{str(o.get('cls')):10}{o.get('t', 0):6.1f}"
              f"{mark(j)}{str(j.get('cls')):10}{j.get('t', 0):6.1f}{str(o.get('own')):>11}{str(o.get('secs')):>6}{str(o.get('calls')):>6}")
    for split in ("dev", "holdout", "all"):
        sub = [r for r in res if split == "all" or r["split"] == split]
        for kind in ("out", "judge", "own"):
            src = "out" if kind == "own" else kind
            have = [r for r in sub if src in r]
            if not have:
                continue
            c = (lambda r: r[src]["own"]) if kind == "own" else (lambda r: r[src]["cls"])
            ex = sum(c(r) == r["clingen"] for r in have)
            w1 = sum(dist(c(r), r["clingen"]) <= 1 for r in have)
            print(f"{split:8}{kind:6} exact {ex}/{len(have)} ({100*ex/len(have):.0f}%)  within-1 {w1}/{len(have)}")
    for kind in ("out", "judge"):
        secs = [r[kind]["secs"] for r in res if kind in r and r[kind]["secs"]]
        calls = [r[kind]["calls"] for r in res if kind in r and r[kind]["calls"]]
        if secs:
            print(f"{kind}: median {sorted(secs)[len(secs)//2]}s/gene, median {sorted(calls)[len(calls)//2] if calls else '?'} calls/gene, n={len(secs)}")
        blind = [r["gene"] for r in res if kind in r and r[kind]["blind"]]
        print(f"{kind}: blind incidents {blind}")


if __name__ == "__main__":
    if "--it" in sys.argv:
        IT = int(sys.argv.pop(sys.argv.index("--it") + 1)); sys.argv.remove("--it")
    assert IT >= 7 or score({"genetic": {"probands": [{"variant": "x", "pmid": 1}] * 5}}, "AD")[0] == 2  # recurrent cap
    assert IT >= 7 or score({"genetic": {"probands": [{"variant": str(i), "pmid": 1} for i in range(3)]},
                  "experimental": {"models": [{"pmid": 1}] * 3}}, "AR")[3] == "limited"  # genetic<4 rule
    assert IT < 5 or IT >= 7 or score({"genetic": {"probands": [{"variant": "a / b", "phase": "unknown", "pmid": 1}]}}, "AR")[0] == 0.5
    assert IT < 5 or IT >= 7 or score({"experimental": {"models": [{"pmid": 1}]}}, "AR")[3] == "no_known"
    main(sys.argv[1])
