"""Variant-position statistics: P/LP ClinVar missense (cases) vs gnomAD missense (controls).

Port of the reviewed frontend engine (frontend/src/utils/stats/{core,variantSet,analyses}.ts):
Fisher exact (conditional MLE OR, exact CI), BH, a min-p FWER sliding-window scan, and 3D
clustering/hotspots on a full-length AlphaFold model. Permutations shuffle case/control labels
over fixed variant positions, vectorised in batches with numpy; deterministic for a seed.
"""

import math
import re
from collections.abc import Iterator
from typing import Any

import numpy as np
from scipy.sparse.csgraph import connected_components
from scipy.spatial.distance import cdist
from scipy.special import gammaln
from scipy.stats import hypergeom

STATS_VERSION = 1  # bump when results change, to invalidate cached results
TOO_FEW = 3
DEFAULT_SEED = 20261031
ALPHA = 0.05
PLDDT_MIN = 70
MAX_MISMATCH = 0.1
CASE = ("pathogenic", "likely_pathogenic")
BENIGN = ("benign", "likely_benign")
NO_MODEL = "No full-length AlphaFold model for this protein, so no 3D statistics."
NEED_REFRESH = "Statistics need a ClinVar data refresh."
TOO_FEW_MSG = "Too few P/LP missense variants for a meaningful test."

AA = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q", "Glu": "E",
    "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F",
    "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V", "Sec": "U",
    "Pyl": "O",
}  # fmt: skip
# One substitution only: p.Ser148Trp (not Ter, =, fs, del, ext or ranges)
MISSENSE_HGVS = re.compile(r"^p\.\(?([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)?$")


# --- primitives -------------------------------------------------------------------------------


def _lchoose(n: Any, r: Any) -> Any:
    return gammaln(n + 1) - gammaln(r + 1) - gammaln(n - r + 1)


def hyper_upper(k: int, big_k: int, n_total: int, n: int) -> float:
    """P(X >= k), X ~ Hypergeometric(population n_total, big_k successes, n draws)."""
    return float(min(1.0, hypergeom.sf(k - 1, n_total, big_k, n)))


def _hyper_table(max_n: int, big_k: int, n_total: int) -> np.ndarray:
    """table[n, k] = hyper_upper(k, big_k, n_total, n) for n <= max_n, k <= big_k."""
    n = np.arange(max_n + 1)[:, None]
    k = np.arange(big_k + 1)[None, :]
    return np.asarray(np.minimum(1.0, hypergeom.sf(k - 1, n_total, big_k, n)))


def _solve_log_or(g: Any, target: float, increasing: bool) -> float:
    """Solve g(log psi) = target by bisection on log psi (exact roots, ruling R4)."""
    lo, hi = -60.0, 60.0
    for _ in range(200):
        if hi - lo <= 1e-13:
            break
        mid = (lo + hi) / 2
        if (g(mid) < target) == increasing:
            lo = mid
        else:
            hi = mid
    return math.exp((lo + hi) / 2)


def fisher_exact(a: int, b: int, c: int, d: int) -> dict[str, float]:
    """Two-sided Fisher exact test on [[a,b],[c,d]]; OR = conditional MLE, exact 95% CI."""
    m, n, k = a + c, b + d, a + b
    s_lo, s_hi = max(0, k - n), min(k, m)
    x = np.arange(s_lo, s_hi + 1)
    base = _lchoose(m, x) + _lchoose(n, k - x)

    def pmf(log_psi: float) -> np.ndarray:
        lw = base + x * log_psi
        w = np.exp(lw - lw.max())
        return np.asarray(w / w.sum())

    p0 = pmf(0.0)
    cut = p0[a - s_lo] * (1 + 1e-7)  # R's relative tolerance on the observed pmf
    p = min(1.0, float(p0[p0 <= cut].sum()))
    mean = lambda lp: float((pmf(lp) * x).sum())  # noqa: E731
    upper = lambda lp: float(pmf(lp)[x >= a].sum())  # noqa: E731
    lower = lambda lp: float(pmf(lp)[x <= a].sum())  # noqa: E731
    odds = 0.0 if a == s_lo else math.inf if a == s_hi else _solve_log_or(mean, a, True)
    lo = 0.0 if a == s_lo else _solve_log_or(upper, 0.025, True)
    hi = math.inf if a == s_hi else _solve_log_or(lower, 0.025, False)
    return {"p": p, "or": odds, "lo": lo, "hi": hi}


def bh_adjust(p: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values in the original order (R p.adjust "BH")."""
    arr = np.asarray(p, dtype=float)
    if not np.isfinite(arr).all():
        raise ValueError("bh_adjust: non-finite p-value")
    n = len(arr)
    order = np.argsort(-arr, kind="stable")
    adj = np.minimum.accumulate(np.minimum(1.0, arr[order] * n / (n - np.arange(n))))
    out = np.empty(n)
    out[order] = adj
    return [float(v) for v in out]


def _permutations(seed: int, n: int, k: int, b: int, width: int) -> Iterator[np.ndarray]:
    """b uniform random k-subsets of range(n) (the permuted cases), in (rows, k) batches."""
    rng = np.random.default_rng(seed)
    batch = max(1, 2_000_000 // max(n, width, 1))
    for done in range(0, b, batch):
        rows = min(batch, b - done)
        yield np.argpartition(rng.random((rows, n)), k - 1, axis=1)[:, :k]


def _row_counts(sel: np.ndarray, bins: np.ndarray, width: int) -> np.ndarray:
    """Per permutation row, how many selected variants fall in each bin (0..width-1)."""
    rows = sel.shape[0]
    flat = bins[sel] + (np.arange(rows) * width)[:, None]
    return np.bincount(flat.ravel(), minlength=rows * width).reshape(rows, width)


def _adjust_by_min_p(p: np.ndarray, sorted_min: np.ndarray) -> np.ndarray:
    """Family-wise adjusted p: (#{perm min-p <= p} + 1) / (B + 1)."""
    hits = np.searchsorted(sorted_min, p * (1 + 1e-12), side="right")
    return np.asarray((hits + 1) / (len(sorted_min) + 1))


# --- variant set and regions ------------------------------------------------------------------


def build_variant_set(
    sequence: str,
    clinvar: list[dict[str, Any]] | None,
    gnomad: list[dict[str, Any]],
    min_stars: int,
) -> dict[str, Any]:
    """Cases (P/LP), benign (B/LB) and gnomAD controls as residue lists, ref-AA checked."""
    cases: list[int] = []
    controls: list[int] = []
    benign: list[int] = []
    dropped = {"clinvar": 0, "gnomad": 0}
    checked = {"clinvar": 0, "gnomad": 0}

    def matches(ref: str, residue: int) -> bool:
        return 1 <= residue <= len(sequence) and AA.get(ref) == sequence[residue - 1]

    def total(c: dict[str, int] | None) -> int:
        return sum(v for star, v in (c or {}).items() if int(star) >= min_stars)

    for row in clinvar or []:
        counts = row.get("counts") or {}
        n_case = [total(counts.get(c)) for c in CASE]
        n_benign = [total(counts.get(c)) for c in BENIGN]
        n = sum(n_case) + sum(n_benign)
        if n == 0:
            continue
        checked["clinvar"] += n
        residue = int(row["residue"])
        if not matches(row.get("ref", ""), residue):
            dropped["clinvar"] += n
            continue
        cases += [residue] * sum(n_case)
        benign += [residue] * sum(n_benign)

    def passes(call: dict[str, Any] | None) -> bool:
        return bool(call) and call["ac"] > 0 and not call["filters"]  # type: ignore[index]

    for v in gnomad:
        if v.get("consequence") != "missense_variant" or not (
            passes(v.get("exome")) or passes(v.get("genome"))
        ):
            continue
        checked["gnomad"] += 1
        m = MISSENSE_HGVS.match(v.get("hgvsp") or "")
        # Not a true substitution (unparseable, synonymous, Ter, unknown alt): count, never lose.
        if not m or m[1] == m[3] or m[3] == "Ter" or m[3] not in AA:
            dropped["gnomad"] += 1
            continue
        residue = int(m[2])
        if not matches(m[1], residue):
            dropped["gnomad"] += 1
            continue
        controls.append(residue)

    withheld: str | None = None
    if clinvar is None:
        withheld = NEED_REFRESH
    else:
        for name, key in (("ClinVar", "clinvar"), ("gnomAD", "gnomad")):
            if checked[key] > 0 and dropped[key] / checked[key] > MAX_MISMATCH:
                pct = f"{100 * dropped[key] / checked[key]:.1f}"
                withheld = (
                    f"Statistics withheld: {pct}% of {name} missense variants do not match "
                    "the UniProt sequence (likely a transcript mismatch)."
                )
                break
    return {
        "length": len(sequence),
        "cases": cases,
        "controls": controls,
        "benign": benign,
        "dropped": dropped,
        "checked": checked,
        "withheld": withheld,
    }


def protein_regions(features: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """UniProt domains/regions: no whole-chain feature, valid ranges, deduplicated, by start."""
    seen: set[str] = set()
    out = []
    for f in features or []:
        start, end = f.get("start"), f.get("end")
        if f.get("type") == "Chain" or not isinstance(start, int) or not isinstance(end, int):
            continue
        key = f"{start}-{end}"
        if start > end or key in seen:
            continue
        seen.add(key)
        label = f.get("description") or f.get("type") or "Region"
        out.append({"key": key, "label": label, "type": f.get("type") or "Region",
                    "start": start, "end": end})  # fmt: skip
    return sorted(out, key=lambda r: (r["start"], r["end"]))


def _in_range(arr: list[int], start: int, end: int) -> int:
    return sum(1 for r in arr if start <= r <= end)


# --- analyses ---------------------------------------------------------------------------------


def domain_enrichment(vset: dict[str, Any], regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One Fisher test per region (in vs out), BH q across all regions of the gene."""
    rows = []
    for r in regions:
        case_in = _in_range(vset["cases"], r["start"], r["end"])
        ctrl_in = _in_range(vset["controls"], r["start"], r["end"])
        case_out = len(vset["cases"]) - case_in
        ctrl_out = len(vset["controls"]) - ctrl_in
        rows.append({**r, "caseIn": case_in, "ctrlIn": ctrl_in, "caseOut": case_out,
                     "ctrlOut": ctrl_out, **fisher_exact(case_in, case_out, ctrl_in, ctrl_out)})  # fmt: skip
    for row, q in zip(rows, bh_adjust([r["p"] for r in rows]), strict=True):
        row["q"] = q
    return rows


def linear_scan(
    vset: dict[str, Any], w: int = 15, b: int = 10_000, seed: int = DEFAULT_SEED
) -> dict[str, Any]:
    """Sliding-window hypergeometric scan with min-p family-wise control."""
    length = vset["length"]
    k = len(vset["cases"])
    pos = np.asarray(vset["cases"] + vset["controls"], dtype=np.int64)
    n_total = len(pos)
    n_win = max(0, length - w + 1)
    width = length + 1  # residue bins 0..length

    def window_sums(counts: np.ndarray) -> np.ndarray:  # counts (..., width) -> (..., n_win)
        cum = np.cumsum(counts[..., 1:], axis=-1)
        cum = np.concatenate([np.zeros(cum.shape[:-1] + (1,), dtype=cum.dtype), cum], axis=-1)
        return np.asarray(cum[..., w : w + n_win] - cum[..., :n_win])

    win_n = window_sums(np.bincount(pos, minlength=width))
    table = _hyper_table(int(win_n.max(initial=0)), k, n_total)
    obs_k = window_sums(np.bincount(pos[:k], minlength=width))
    obs_p = table[win_n, obs_k]

    min_p = np.empty(b)
    i = 0
    for sel in _permutations(seed, n_total, k, b, width):
        p = table[win_n[None, :], window_sums(_row_counts(sel, pos, width))]
        min_p[i : i + len(sel)] = p.min(axis=1, initial=1.0)
        i += len(sel)
    min_p.sort()
    adj = _adjust_by_min_p(obs_p, min_p)

    windows = [
        {"start": s + 1, "end": s + w, "centre": s + 1 + (w - 1) / 2, "cases": int(obs_k[s]),
         "ctrls": int(win_n[s] - obs_k[s]), "p": float(obs_p[s]), "adjP": float(adj[s])}
        for s in range(n_win)
    ]  # fmt: skip
    # Merge significant windows whose residue ranges overlap or touch, then recount the span.
    spans: list[dict[str, Any]] = []
    for win in windows:
        if win["adjP"] >= ALPHA:
            continue
        if spans and win["start"] <= spans[-1]["end"] + 1:
            spans[-1]["end"] = win["end"]
            spans[-1]["adjP"] = min(spans[-1]["adjP"], win["adjP"])
        else:
            spans.append({"start": win["start"], "end": win["end"], "adjP": win["adjP"]})
    regions = [
        {"start": s["start"], "end": s["end"],
         "cases": _in_range(vset["cases"], s["start"], s["end"]),
         "ctrls": _in_range(vset["controls"], s["start"], s["end"]),
         "benign": _in_range(vset["benign"], s["start"], s["end"]), "adjP": s["adjP"]}
        for s in spans
    ]  # fmt: skip
    return {"windows": windows, "regions": regions, "B": b, "seed": seed, "w": w}


def _eligible(vset: dict[str, Any], residues: list[dict[str, Any]]) -> dict[str, Any]:
    """Variants at confident (pLDDT >= 70) residues as carrier indices; cases first."""
    elig = [r for r in residues if r["plddt"] >= PLDDT_MIN]
    by_resno = {r["resno"]: i for i, r in enumerate(elig)}
    cases = [by_resno[r] for r in vset["cases"] if r in by_resno]
    v_res = np.asarray(cases + [by_resno[r] for r in vset["controls"] if r in by_resno], dtype=int)
    xyz = np.asarray([[r["x"], r["y"], r["z"]] for r in elig], dtype=float).reshape(-1, 3)
    carriers, inv = np.unique(v_res, return_inverse=True)
    return {"elig": elig, "xyz": xyz, "v_res": v_res, "k": len(cases), "carriers": carriers,
            "inv": inv.astype(np.int64)}  # fmt: skip


def _dist(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.asarray(cdist(a, b))


def cluster_3d(
    vset: dict[str, Any], residues: list[dict[str, Any]], b: int = 10_000, seed: int = DEFAULT_SEED
) -> dict[str, Any] | None:
    """Mean pairwise C-alpha distance among distinct case residues vs the label-permutation
    null; one-sided (smaller = clustered). None with < TOO_FEW distinct eligible case residues."""
    el = _eligible(vset, residues)
    k, inv, n_c = el["k"], el["inv"], len(el["carriers"])
    d_mat = _dist(el["xyz"][el["carriers"]], el["xyz"][el["carriers"]])

    def mean_dist(sel: np.ndarray) -> tuple[np.ndarray, np.ndarray]:  # sel (rows, k)
        u = np.zeros((sel.shape[0], n_c))
        u[np.arange(sel.shape[0])[:, None], inv[sel]] = 1.0
        d = u.sum(axis=1)
        s = ((u @ d_mat) * u).sum(axis=1) / 2
        pairs = d * (d - 1) / 2
        return np.where(d > 1, s / np.where(pairs > 0, pairs, 1), 0.0), d

    obs, obs_d = mean_dist(np.arange(k)[None, :])
    if obs_d[0] < TOO_FEW:
        return None
    nulls = np.concatenate([mean_dist(sel)[0] for sel in _permutations(seed, len(inv), k, b, n_c)])
    hits = int((nulls <= obs[0] * (1 + 1e-12)).sum())
    nulls.sort()
    bins = 30
    lo = float(nulls[0])
    width = (float(nulls[-1]) - lo) / bins or 1.0
    counts = np.bincount(np.minimum(bins - 1, ((nulls - lo) / width).astype(int)), minlength=bins)
    return {
        "observed": float(obs[0]),
        "nullMean": float(nulls.mean()),
        "nullLo": float(np.quantile(nulls, 0.025)),
        "nullHi": float(np.quantile(nulls, 0.975)),
        "p": (hits + 1) / (b + 1),
        "histogram": [
            {"x0": lo + i * width, "x1": lo + (i + 1) * width, "n": int(counts[i])}
            for i in range(bins)
        ],  # fmt: skip
        "nCaseResidues": int(obs_d[0]),
        "B": b,
        "seed": seed,
    }


def hotspots_3d(
    vset: dict[str, Any],
    residues: list[dict[str, Any]],
    radius: float = 10,
    b: int = 2_000,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Per eligible residue, hypergeometric enrichment of cases among variants within `radius`
    (self included), min-p FWER. Significant residues connected within `radius` form a cluster;
    `residues` lists only those (R5), cases/ctrls count over the union of their spheres."""
    el = _eligible(vset, residues)
    elig, xyz, k, inv, v_res = el["elig"], el["xyz"], el["k"], el["inv"], el["v_res"]
    out: dict[str, Any] = {"clusters": [], "B": b, "seed": seed, "radius": radius}
    if k == 0:
        return out
    n_c = len(el["carriers"])
    near = (_dist(xyz[el["carriers"]], xyz) <= radius).astype(np.float32)  # (carriers, eligible)
    n_var = np.rint(np.bincount(inv, minlength=n_c) @ near).astype(int)
    table = _hyper_table(int(n_var.max()), k, len(inv))
    obs_k = np.rint(np.bincount(inv[:k], minlength=n_c) @ near).astype(int)
    obs_p = table[n_var, obs_k]
    min_p = np.concatenate([
        table[n_var[None, :], np.rint(_row_counts(sel, inv, n_c).astype(np.float32) @ near).astype(int)].min(axis=1)
        for sel in _permutations(seed, len(inv), k, b, len(elig))
    ])  # fmt: skip
    min_p.sort()
    adj = _adjust_by_min_p(obs_p, min_p)
    sig = np.flatnonzero(adj < ALPHA)
    if not len(sig):
        return out
    n_comp, label = connected_components(_dist(xyz[sig], xyz[sig]) <= radius, directed=False)
    for c in range(n_comp):
        centres = sorted(sig[label == c], key=lambda e: elig[e]["resno"])
        members = np.asarray((_dist(xyz[centres], xyz) <= radius).any(axis=0))
        out["clusters"].append({
            "residues": [int(elig[e]["resno"]) for e in centres],
            "residueAdjP": [float(adj[e]) for e in centres],
            "cases": int(members[v_res[:k]].sum()),
            "ctrls": int(members[v_res[k:]].sum()),
            "adjP": float(min(adj[e] for e in centres)),
        })  # fmt: skip
    return out


# --- response ---------------------------------------------------------------------------------


def _finite(v: float) -> float | None:
    """Infinity is not JSON: an unbounded OR/CI is sent as null."""
    return None if math.isinf(v) else v


def compute_position_statistics(
    *,
    gene: str,
    accession: str,
    length: int,
    sequence: str,
    clinvar_residues: list[dict[str, Any]] | None,
    gnomad: list[dict[str, Any]],
    domains: list[dict[str, Any]] | None,
    model: dict[str, Any] | None,
    min_stars: int,
    provenance: dict[str, Any],
    spatial_error: str | None = None,
) -> dict[str, Any]:
    """Assemble the API response (CPU-bound; run in a worker thread)."""
    vset = build_variant_set(sequence, clinvar_residues, gnomad, min_stars)
    status, message = "ready", None
    if vset["withheld"]:
        status, message = "withheld", vset["withheld"]
    elif len(vset["cases"]) < TOO_FEW:
        status, message = "too-few", TOO_FEW_MSG
    linear = spatial = spatial_message = None
    if status == "ready":
        domains_out = domain_enrichment(vset, protein_regions(domains))
        for d in domains_out:
            d["or"], d["hi"] = _finite(d["or"]), _finite(d["hi"])
        linear = {"domains": domains_out, "scan": linear_scan(vset)}
        if spatial_error:
            spatial_message = f"3D statistics unavailable: {spatial_error}"
        elif model and model.get("residues"):
            spatial = {"cluster": cluster_3d(vset, model["residues"]),
                       "hotspots": hotspots_3d(vset, model["residues"])}  # fmt: skip
        else:
            spatial_message = NO_MODEL
    alphafold = model and {"entryId": model["entryId"], "version": model["version"]}
    return {
        "gene": gene,
        "accession": accession,
        "length": length,
        "status": status,
        "message": message,
        "variantSet": {
            "cases": len(vset["cases"]),
            "controls": len(vset["controls"]),
            "benign": len(vset["benign"]),
            "dropped": vset["dropped"],
            "checked": vset["checked"],
        },
        "linear": linear,
        "spatial": spatial,
        "spatialMessage": spatial_message,
        "provenance": {
            **provenance,
            "alphafold": alphafold or None,
            "minStars": min_stars,
            "seed": DEFAULT_SEED,
        },  # fmt: skip
    }
