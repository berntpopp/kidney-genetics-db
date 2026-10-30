"""Simulate #438 (GenCC kidney filter) and the HPO root change before touching KGDB code."""

import csv
import json
import collections
from pathlib import Path

D = Path(__file__).parent
KW = ['kidney', 'renal', 'nephro', 'glomerul', 'tubulopathy', 'tubulointerstitial', 'renotubular',
      'polycystic', 'alport', 'nephritis', 'cystic kidney', 'ciliopathy', 'complement', 'cakut',
      'focal segmental', 'steroid resistant', 'nephrotic', 'proteinuria', 'hematuria']
MISSING48 = set("""BSND SMARCAL1 CLCNKB SALL1 TSC2 GLA ALMS1 TSC1 COQ2 HPSE2 SLC12A3 DHCR7 AHI1 GLI3 AGXT
CHD7 SLC34A3 WDR35 GRHPR APRT CYP24A1 IFT122 LRIG2 DYNC2H1 FAH XDH DYNC2I1 ACTG2 SCNN1B RMND1 HPRT1
CHRM3 KMT2D PDSS2 TP53RK SLC7A7 SLC3A1 SLC7A9 ANOS1 LAGE3 TCTN2 KDM6A GPC3 ROBO2 CFHR1 SLC2A2 ENPP1
LCAT""".split())
CLASSES_OK = {"Definitive", "Strong", "Moderate", "Supportive", "Limited"}

# --- HPO is_a graph -> descendants
g = json.load(open(D / "hp.json"))["graphs"][0]
children = collections.defaultdict(set)
for e in g["edges"]:
    if e["pred"] == "is_a":
        children[e["obj"].rsplit("/", 1)[-1].replace("_", ":")].add(e["sub"].rsplit("/", 1)[-1].replace("_", ":"))
names = {n["id"].rsplit("/", 1)[-1].replace("_", ":"): n.get("lbl", "") for n in g["nodes"]}


def desc(root):
    out, stack = set(), [root]
    while stack:
        t = stack.pop()
        if t not in out:
            out.add(t)
            stack += children.get(t, ())
    return out


UPPER, URINARY, KIDNEY = desc("HP:0010935"), desc("HP:0000079"), desc("HP:0000077")
print(f"HPO terms: upper {len(UPPER)}, urinary {len(URINARY)}, kidney {len(KIDNEY)}")

# --- HPO source: gene -> terms (genes_to_phenotype)
gene_terms = collections.defaultdict(set)
for row in csv.DictReader(open(D / "g2p.txt"), delimiter="\t"):
    gene_terms[row["gene_symbol"]].add(row["hpo_id"])
up_genes = {gname for gname, ts in gene_terms.items() if ts & UPPER}
ur_genes = {gname for gname, ts in gene_terms.items() if ts & URINARY}
new = ur_genes - up_genes
print(f"\nHPO genes: upper-tract root {len(up_genes)}, whole urinary root {len(ur_genes)}, +{len(new)} new")
term_hits = collections.Counter(t for gname in new for t in gene_terms[gname] & URINARY)
print("terms bringing the new genes:", [(t, names.get(t), c) for t, c in term_hits.most_common(10)])
print("new genes that are in the 48 list:", sorted(new & MISSING48))

# --- disease -> HPO terms (phenotype.hpoa, aspect P, not NOT)
dis_terms = collections.defaultdict(set)
for line in open(D / "phenotype.hpoa"):
    if line.startswith("#") or line.startswith("database_id"):
        continue
    f = line.rstrip("\n").split("\t")
    if len(f) > 10 and f[10] == "P" and f[2] != "NOT":
        dis_terms[f[0]].add(f[3])

# --- GenCC: map MONDO -> OMIM/ORPHA via original curies seen in GenCC itself
rows = list(csv.DictReader(open(D / "gencc.xlsx_or_tsv"), delimiter="\t"))
mondo_x = collections.defaultdict(set)
for r in rows:
    o = r["disease_original_curie"]
    if o.startswith(("OMIM:", "Orphanet:", "ORPHA:")):
        mondo_x[r["disease_curie"]].add(o.replace("Orphanet:", "ORPHA:"))


def kw(r):
    t = " ".join(r[k] for k in ("disease_title", "disease_original_title", "submitted_as_disease_name")).lower()
    return any(k in t.replace("adrenal", " ") for k in KW)


def hpo_rule(r, branch):
    ids = mondo_x.get(r["disease_curie"], set()) | {r["disease_original_curie"].replace("Orphanet:", "ORPHA:")}
    return any(dis_terms.get(i, set()) & branch for i in ids)


rules = {
    "keyword (current)": kw,
    "keyword OR HPO kidney": lambda r: kw(r) or hpo_rule(r, KIDNEY),
    "keyword OR HPO urinary": lambda r: kw(r) or hpo_rule(r, URINARY),
}
print()
base = None
for name, rule in rules.items():
    genes = {r["gene_symbol"] for r in rows if r["classification_title"] in CLASSES_OK and rule(r)}
    base = base or genes
    print(f"{name:24} genes {len(genes):5} | recovers {len(genes & MISSING48):2}/48 | +{len(genes - base)} vs current")
    if genes - base:
        print("   missed of 48:", sorted(MISSING48 - genes))
        print("   sample new genes:", sorted(genes - base)[:40])

# --- tighter rules (round 2)
panel = {l.split("|")[0] for l in open(D / "kgdb_sources.tsv") if {"PanelApp", "DiagnosticPanels"} & set(l.strip().split("|")[1].split(","))}


def n_kidney(r):
    ids = mondo_x.get(r["disease_curie"], set()) | {r["disease_original_curie"].replace("Orphanet:", "ORPHA:")}
    return max((len(dis_terms.get(i, set()) & KIDNEY) for i in ids), default=0)


tight = {
    "kw OR (HPO kidney AND panel gene)": lambda r: kw(r) or (n_kidney(r) >= 1 and r["gene_symbol"] in panel),
    "kw OR >=3 kidney HPO terms": lambda r: kw(r) or n_kidney(r) >= 3,
    "kw OR (>=2 kidney terms AND panel)": lambda r: kw(r) or (n_kidney(r) >= 2 and r["gene_symbol"] in panel),
}
print("\n-- tighter #438 rules")
for name, rule in tight.items():
    genes = {r["gene_symbol"] for r in rows if r["classification_title"] in CLASSES_OK and rule(r)}
    print(f"{name:36} genes {len(genes):5} | recovers {len(genes & MISSING48):2}/48 | +{len(genes - base)} | missed {sorted(MISSING48 - genes)}")
    if name.startswith("kw OR (HPO kidney AND panel"):
        extra = sorted(genes - base - MISSING48)
        print("   extra beyond the 48 (sample):", extra[:60])

# --- HPO lower urinary tract: which children carry genes
print("\n-- lower urinary tract children of HP:0010936")
for c in sorted(children["HP:0010936"]):
    sub = desc(c)
    n = sum(1 for gname, ts in gene_terms.items() if ts & sub)
    print(f"  {c} {names.get(c)}: {n} genes")
