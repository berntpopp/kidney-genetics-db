"""Position statistics: R reference values, calibration/power, 3D planted clusters, endpoint."""

import math
import time
import uuid

import httpx
import numpy as np
import pytest

from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation
from app.services import position_stats_sources as sources
from app.services.position_stats import (
    bh_adjust,
    build_variant_set,
    cluster_3d,
    domain_enrichment,
    fisher_exact,
    hotspots_3d,
    hyper_upper,
    linear_scan,
    protein_regions,
)


def rel(x: float, y: float, tol: float) -> bool:
    return x == y or abs(x - y) <= tol * max(abs(y), 1e-300)


def mk_set(length, cases, controls, benign=()):
    return {"length": length, "cases": list(cases), "controls": list(controls),
            "benign": list(benign), "dropped": {"clinvar": 0, "gnomad": 0},
            "checked": {"clinvar": 0, "gnomad": 0}, "withheld": None}  # fmt: skip


def uniform(rng, n, length):
    return [int(v) for v in rng.integers(1, length + 1, n)]


def line(n=60, plddt=90):  # residues on a straight line, 3.8 A apart
    return [{"resno": r, "x": 3.8 * r, "y": 0.0, "z": 0.0, "plddt": plddt} for r in range(1, n + 1)]


INF = math.inf
# R 4.5: fisher.test(matrix(c(a,b,c,d), 2, byrow = TRUE))
FISHER_R = [
    ((8, 2, 1, 5), 0.03496503497, 15.46968746, 1.00884938, 1049.791446),
    ((3, 1, 1, 3), 0.4857142857, 6.408308867, 0.2117329153, 621.9337505),
    ((0, 10, 5, 5), 0.03250773994, 0, 0, 0.8365428425),
    ((10, 0, 2, 8), 0.0007144558228, INF, 3.817010258, INF),
    ((27, 84, 58, 794), 1.064301661e-7, 4.389990715, 2.530858761, 7.486828435),
    ((1, 9, 11, 3), 0.002759456185, 0.03723311725, 0.0006438283884, 0.4258840381),
    ((12, 5, 30, 40), 0.0577727087, 3.157421529, 0.9133653002, 12.71750941),
    ((0, 0, 3, 4), 1, 0, 0, INF),
]


@pytest.mark.unit
class TestCore:
    @pytest.mark.parametrize(("t", "p", "odds", "lo", "hi"), FISHER_R)
    def test_fisher_matches_r(self, t, p, odds, lo, hi):
        r = fisher_exact(*t)
        assert rel(r["p"], p, 1e-6)
        # R's printed OR/CI carry uniroot tolerance; exact values checked below.
        assert rel(r["or"], odds, 1e-3)
        assert rel(r["lo"], lo, 2e-2)
        assert rel(r["hi"], hi, 2e-2)

    def test_fisher_exact_roots(self):  # R uniroot tol=1e-14 (ruling R4)
        r = fisher_exact(8, 2, 1, 5)
        assert rel(r["or"], 15.46581972, 1e-8)
        assert rel(r["lo"], 1.00884920794769, 1e-8)
        assert rel(r["hi"], 1059.639495086282, 1e-8)

    def test_fisher_row_swap_inverts_or(self):
        assert fisher_exact(2, 3, 4, 1)["or"] * fisher_exact(3, 2, 1, 4)["or"] == pytest.approx(1)

    def test_hyper_upper(self):
        assert rel(hyper_upper(5, 20, 100, 7), 0.003259144891, 1e-8)  # phyper(4,20,80,7,F)
        assert hyper_upper(0, 20, 100, 7) == 1
        assert hyper_upper(8, 20, 100, 7) == 0
        assert hyper_upper(21, 20, 100, 30) == 0
        assert hyper_upper(20, 20, 100, 100) == pytest.approx(1, abs=1e-12)
        assert abs(hyper_upper(1, 300, 5000, 400) - 0.9999999999939356) < 1e-9

    def test_bh_matches_r(self):
        out = bh_adjust([0.01, 0.04, 0.03, 0.005, 0.5, 0.2, 0.04])
        exp = [0.035, 0.056, 0.056, 0.035, 0.5, 0.2333333333, 0.056]
        assert out == pytest.approx(exp, abs=1e-9)
        with pytest.raises(ValueError):
            bh_adjust([0.1, math.nan])


SEQ = "MRQGAAAAAA"  # 1 M, 2 R, 3 Q, 4 G
PASS = {"ac": 1, "filters": []}


def g(hgvsp, **o):
    return {"variant_id": "x", "consequence": "missense_variant", "hgvsp": hgvsp,
            "exome": PASS, "genome": None, **o}  # fmt: skip


def cv(residue, ref, counts):
    return {"residue": residue, "ref": ref, "counts": counts}


@pytest.mark.unit
class TestVariantSet:
    def test_counts_and_min_stars(self):
        rows = [cv(2, "Arg", {"pathogenic": {"0": 1, "2": 2}, "likely_pathogenic": {"1": 1},
                              "benign": {"1": 1}})]  # fmt: skip
        s0 = build_variant_set(SEQ, rows, [], 0)
        assert s0["cases"] == [2, 2, 2, 2] and s0["benign"] == [2] and s0["length"] == 10
        assert build_variant_set(SEQ, rows, [], 1)["cases"] == [2, 2, 2]

    def test_gnomad_filters(self):
        gnomad = [
            g("p.Gln3Arg"),
            g("p.Gly4Ala", consequence="synonymous_variant"),
            g("p.Arg2Cys", exome={"ac": 1, "filters": ["AC0"]}),
            g("p.Arg2His", exome={"ac": 0, "filters": []}),
            g("p.Arg2fs"),
            g("p.Arg2Ter"),
            g("p.Arg2Arg"),
            g("p.Arg2Gln", exome=None, genome=PASS),
        ]
        r = build_variant_set(SEQ, [], gnomad, 0)
        assert r["controls"] == [3, 2]
        assert r["checked"]["gnomad"] == 5 and r["dropped"]["gnomad"] == 3

    def test_clinvar_mismatch_and_vus(self):
        rows = [cv(2, "Lys", {"pathogenic": {"2": 50}}), cv(3, "Lys", {"vus": {"2": 9}})]
        r = build_variant_set(SEQ, rows, [], 1)
        assert r["dropped"]["clinvar"] == 50 and r["checked"]["clinvar"] == 50

    def test_withhold_strictly_above_ten_percent(self):
        def run(bad):
            rows = [cv(2, "Arg", {"pathogenic": {"1": 100 - bad}}),
                    cv(2, "Lys", {"pathogenic": {"1": bad}})]  # fmt: skip
            return build_variant_set(SEQ, rows, [], 0)["withheld"]

        assert run(10) is None
        assert "11.0% of ClinVar" in run(11)
        bad = build_variant_set(SEQ, [], [g("p.Gln3Arg"), g("p.Gln2Arg"), g("p.Arg99Cys")], 0)
        assert bad["withheld"] == (
            "Statistics withheld: 66.7% of gnomAD missense variants do not match the UniProt "
            "sequence (likely a transcript mismatch)."
        )

    def test_missing_residues_need_refresh(self):
        assert build_variant_set(SEQ, None, [], 0)["withheld"] == (
            "Statistics need a ClinVar data refresh."
        )

    def test_protein_regions(self):
        regions = protein_regions([
            {"type": "Chain", "description": "HNF1B", "start": 1, "end": 557},
            {"type": "Domain", "description": "POU-specific atypical", "start": 93, "end": 188},
            {"type": "Region", "description": "Dimerization", "start": 1, "end": 31},
            {"type": "Region", "description": "Dimerization", "start": 1, "end": 31},
            {"type": "Region", "description": "Broken", "start": 50, "end": 40},
            {"type": "Region", "description": "No range"},
        ])  # fmt: skip
        assert [r["key"] for r in regions] == ["1-31", "93-188"]


def in_region(arr, r):
    return sum(1 for x in arr if r["start"] <= x <= r["end"])


@pytest.mark.unit
class TestLinear:
    def test_domain_enrichment(self):
        s = mk_set(100, [5, 6, 7, 8, 50, 90], [1, 5, 20, 30, 40, 50, 60, 70, 80, 95])
        regions = [{"key": "1-10", "label": "A", "type": "Domain", "start": 1, "end": 10},
                   {"key": "45-55", "label": "B", "type": "Region", "start": 45, "end": 55},
                   {"key": "61-69", "label": "C", "type": "Motif", "start": 61, "end": 69}]  # fmt: skip
        res = domain_enrichment(s, regions)
        tables = [(4, 2, 2, 8), (1, 5, 1, 9), (0, 6, 0, 10)]
        assert [(r["caseIn"], r["caseOut"], r["ctrlIn"], r["ctrlOut"]) for r in res] == tables
        hand = [fisher_exact(*t) for t in tables]
        for r, h in zip(res, hand, strict=True):
            assert {k: r[k] for k in ("p", "or", "lo", "hi")} == h
        assert [r["q"] for r in res] == bh_adjust([h["p"] for h in hand])

    def test_deterministic_and_layout(self):
        rng = np.random.default_rng(7)
        s = mk_set(200, uniform(rng, 15, 200), uniform(rng, 150, 200))
        a, b = linear_scan(s, b=499, seed=11), linear_scan(s, b=499, seed=11)
        assert [w["adjP"] for w in a["windows"]] == [w["adjP"] for w in b["windows"]]
        assert len(a["windows"]) == 186
        assert a["windows"][0]["start"] == 1 and a["windows"][0]["end"] == 15
        assert a["windows"][0]["centre"] == 8
        for w in a["windows"]:
            assert w["adjP"] >= w["p"]
            assert w["cases"] == in_region(s["cases"], w)
            assert w["ctrls"] == in_region(s["controls"], w)
            exp = hyper_upper(w["cases"], 15, 165, w["cases"] + w["ctrls"]) if w["cases"] else 1
            assert w["p"] == pytest.approx(exp, rel=1e-12)

    def test_calibrated(self):
        hits = 0
        for i in range(200):
            rng = np.random.default_rng(i)
            s = mk_set(300, uniform(rng, 20, 300), uniform(rng, 200, 300))
            hits += bool(linear_scan(s, b=199, seed=1000 + i)["regions"])
        # Binomial 99% interval for n = 200, p = 0.05: qbinom(c(0.005, 0.995), 200, 0.05)
        assert 3 <= hits <= 19, hits

    def test_planted_hotspot(self):
        rng = np.random.default_rng(42)
        cases = [99 + x for x in uniform(rng, 15, 15)] + uniform(rng, 5, 300)
        s = mk_set(300, cases, uniform(rng, 200, 300), [101, 250])
        res = linear_scan(s, b=999, seed=1)
        hit = next(r for r in res["regions"] if r["start"] <= 114 and r["end"] >= 100)
        assert hit["adjP"] < 0.05
        assert hit["benign"] == in_region([101, 250], hit)

    def test_merges_touching_windows(self):
        s = mk_set(300, [10] * 8 + [38] * 8, range(1, 301), [5, 30, 60])
        res = linear_scan(s, b=999, seed=3)
        assert all(w["adjP"] >= 0.05 for w in res["windows"][10:23])
        assert res["windows"][9]["adjP"] < 0.05 and res["windows"][23]["adjP"] < 0.05
        sig = min(w["adjP"] for w in res["windows"] if w["adjP"] < 0.05)
        assert res["regions"] == [
            {"start": 1, "end": 52, "cases": 16, "ctrls": 52, "benign": 2, "adjP": sig}
        ]

    def test_performance_budget(self):  # 4303 residues, 60 cases, 3000 controls, B = 10 000
        rng = np.random.default_rng(3)
        s = mk_set(4303, uniform(rng, 60, 4303), uniform(rng, 3000, 4303))
        t0 = time.perf_counter()
        linear_scan(s)
        assert time.perf_counter() - t0 < 4


@pytest.mark.unit
class TestSpatial:
    controls = list(range(1, 61)) * 2

    def test_cluster_planted(self):
        planted = mk_set(60, range(10, 15), self.controls)
        res = cluster_3d(planted, line(), b=999, seed=5)
        assert res["nCaseResidues"] == 5
        assert res["observed"] == pytest.approx(7.6, abs=1e-10)  # mean |i-j| over 5 = 2
        assert res["p"] < 0.01
        assert res["nullLo"] < res["nullMean"] < res["nullHi"]
        assert len(res["histogram"]) == 30 and sum(h["n"] for h in res["histogram"]) == 999
        assert cluster_3d(planted, line(), b=999, seed=5) == res

    def test_cluster_null_mean_p(self):
        ps = []
        for i in range(100):
            rng = np.random.default_rng(500 + i)
            res = cluster_3d(mk_set(60, uniform(rng, 8, 60), uniform(rng, 60, 60)), line(),
                             b=199, seed=i)  # fmt: skip
            if res:
                ps.append(res["p"])
        assert len(ps) == 100 and 0.4 <= sum(ps) / 100 <= 0.6

    def test_cluster_too_few(self):
        res = [{**r, "plddt": 50} if 10 <= r["resno"] <= 14 else r for r in line()]
        assert cluster_3d(mk_set(60, [10, 11, 12, 30, 31, 31], self.controls), res) is None
        assert cluster_3d(mk_set(60, [5, 5], self.controls), line()) is None

    def test_hotspot_planted(self):
        s = mk_set(60, range(10, 15), self.controls)
        res = hotspots_3d(s, line(), b=999, seed=9)
        assert len(res["clusters"]) == 1
        hit = res["clusters"][0]
        assert hit["residues"] and all(10 <= r <= 14 for r in hit["residues"])  # R5
        assert len(hit["residueAdjP"]) == len(hit["residues"])
        assert all(p < 0.05 for p in hit["residueAdjP"])
        assert hit["adjP"] == min(hit["residueAdjP"]) and hit["cases"] == 5
        assert res["radius"] == 10
        assert hotspots_3d(s, line(), b=999, seed=9) == res

    def test_hotspot_uniform_labels(self):
        s = mk_set(60, [r for r in range(1, 61) if r % 6 == 0], range(1, 61))
        assert hotspots_3d(s, line(), b=499, seed=2)["clusters"] == []

    def test_hotspot_calibrated(self):
        radius = (3 * 300 * 140 / (4 * math.pi)) ** (1 / 3)  # protein-like density
        hits = 0
        for i in range(200):
            rng = np.random.default_rng(9000 + i)
            pts = rng.uniform(-radius, radius, (2000, 3))
            pts = pts[(pts**2).sum(1) <= radius**2][:300]
            residues = [{"resno": j + 1, "x": x, "y": y, "z": z, "plddt": 90}
                        for j, (x, y, z) in enumerate(pts)]  # fmt: skip
            s = mk_set(300, uniform(rng, 20, 300), uniform(rng, 200, 300))
            hits += bool(hotspots_3d(s, residues, b=199, seed=i)["clusters"])
        assert 3 <= hits <= 19, hits


CIF = """data_x
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.label_atom_id
_atom_site.label_comp_id
_atom_site.label_seq_id
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.B_iso_or_equiv
ATOM 1 N MET 1 0.0 0.0 0.0 40.1
ATOM 2 CA MET 1 1.5 2.5 -3.0 41.2
ATOM 3 CA "ARG" 2 4.0 5.0 6.0 91.0
HETATM 4 CA XYZ 3 9 9 9 99
#
"""


@pytest.mark.unit
def test_parse_ca_atoms():
    assert sources.parse_ca_atoms(CIF) == [
        {"resno": 1, "x": 1.5, "y": 2.5, "z": -3.0, "plddt": 41.2},
        {"resno": 2, "x": 4.0, "y": 5.0, "z": 6.0, "plddt": 91.0},
    ]


@pytest.mark.integration
async def test_endpoint_with_mocked_upstreams(async_client, db_session, monkeypatch):
    symbol = f"PS{uuid.uuid4().hex[:6].upper()}"
    accession = f"T{uuid.uuid4().hex[:5].upper()}"
    length = 60
    sequence = "M" + "A" * (length - 1)
    gene = Gene(approved_symbol=symbol, hgnc_id=f"HGNC:TEST{uuid.uuid4().hex[:8].upper()}")
    db_session.add(gene)
    db_session.commit()
    residues = [cv(r, "Ala", {"pathogenic": {"2": 1}}) for r in range(10, 15)]
    db_session.add_all([
        GeneAnnotation(gene_id=gene.id, source="clinvar", annotations={"missense_residues": residues}),
        GeneAnnotation(gene_id=gene.id, source="uniprot", annotations={
            "accession": accession, "length": length,
            "domains": [{"type": "Domain", "description": "D", "start": 8, "end": 16}]}),
    ])  # fmt: skip
    db_session.commit()
    gnomad = [g(f"p.Ala{r}Val") for r in list(range(2, 61)) * 2]
    calls = {"gnomad": 0}

    async def fake_gnomad(client, s):
        calls["gnomad"] += 1
        return gnomad

    async def fake_seq(client, acc):
        return sequence

    async def fake_model(client, acc, n):
        return {"entryId": f"AF-{acc}-F1", "version": 6, "residues": line(length)}

    monkeypatch.setattr(sources, "fetch_gnomad_missense", fake_gnomad)
    monkeypatch.setattr(sources, "fetch_uniprot_sequence", fake_seq)
    monkeypatch.setattr(sources, "fetch_alphafold_model", fake_model)

    res = await async_client.get(f"/api/genes/{symbol.lower()}/position-statistics")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "ready" and body["gene"] == symbol and body["length"] == length
    assert body["variantSet"]["cases"] == 5 and body["variantSet"]["controls"] == 118
    assert body["linear"]["domains"][0]["hi"] is None  # unbounded CI as null
    assert body["linear"]["scan"]["regions"]
    assert body["spatial"]["cluster"]["p"] < 0.01 and body["spatial"]["hotspots"]["clusters"]
    assert body["provenance"]["alphafold"] == {"entryId": f"AF-{accession}-F1", "version": 6}
    again = await async_client.get(f"/api/genes/{symbol}/position-statistics")
    assert again.json() == body and calls["gnomad"] == 1  # result and gnomAD payload cached

    async def failing_gnomad(client, s):
        raise sources.UpstreamError("gnomAD responded 429")

    monkeypatch.setattr(sources, "fetch_gnomad_missense", failing_gnomad)
    res = await async_client.get(f"/api/genes/{symbol}/position-statistics?min_stars=3")
    # min_stars=3 drops every case, but the gnomAD payload is cached, so this still succeeds.
    assert res.status_code == 200 and res.json()["status"] == "too-few"
    other = f"PX{uuid.uuid4().hex[:6].upper()}"
    gene2 = Gene(approved_symbol=other, hgnc_id=f"HGNC:TEST{uuid.uuid4().hex[:8].upper()}")
    db_session.add(gene2)
    db_session.commit()
    db_session.add(GeneAnnotation(gene_id=gene2.id, source="uniprot",
                                  annotations={"accession": accession, "length": length}))  # fmt: skip
    db_session.commit()
    res = await async_client.get(f"/api/genes/{other}/position-statistics")
    assert res.status_code == 502
    assert res.json()["error"]["detail"] == "gnomAD responded 429"  # project error envelope
    assert (await async_client.get("/api/genes/NOPE_GENE_X/position-statistics")).status_code == 404


def _gene_with_annotations(db_session):
    symbol = f"PA{uuid.uuid4().hex[:6].upper()}"
    accession = f"T{uuid.uuid4().hex[:5].upper()}"
    gene = Gene(approved_symbol=symbol, hgnc_id=f"HGNC:TEST{uuid.uuid4().hex[:8].upper()}")
    db_session.add(gene)
    db_session.commit()
    residues = [cv(r, "Ala", {"pathogenic": {"2": 1}}) for r in range(10, 15)]
    db_session.add_all([
        GeneAnnotation(gene_id=gene.id, source="clinvar", annotations={"missense_residues": residues}),
        GeneAnnotation(gene_id=gene.id, source="uniprot",
                       annotations={"accession": accession, "length": 60}),
    ])  # fmt: skip
    db_session.commit()
    return symbol


def _mock_linear_upstreams(monkeypatch):
    async def fake_gnomad(client, s):
        return [g(f"p.Ala{r}Val") for r in list(range(2, 61)) * 2]

    async def fake_seq(client, acc):
        return "M" + "A" * 59

    monkeypatch.setattr(sources, "fetch_gnomad_missense", fake_gnomad)
    monkeypatch.setattr(sources, "fetch_uniprot_sequence", fake_seq)


@pytest.mark.integration
async def test_alphafold_failure_keeps_linear(async_client, db_session, monkeypatch):
    symbol = _gene_with_annotations(db_session)
    _mock_linear_upstreams(monkeypatch)
    calls = []

    async def failing_model(client, acc, n):
        calls.append(acc)
        req = httpx.Request("GET", "https://alphafold.ebi.ac.uk/api/prediction/x")
        raise httpx.HTTPStatusError("503", request=req, response=httpx.Response(503, request=req))

    monkeypatch.setattr(sources, "fetch_alphafold_model", failing_model)
    res = await async_client.get(f"/api/genes/{symbol}/position-statistics")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "ready" and body["linear"]["scan"]["regions"]
    assert body["spatial"] is None
    assert body["spatialMessage"] == "3D statistics unavailable: AlphaFold responded 503"
    assert body["provenance"]["alphafold"] is None

    async def timeout_model(client, acc, n):
        calls.append(acc)
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(sources, "fetch_alphafold_model", timeout_model)
    # The degraded result was not cached, so this recomputes and asks AlphaFold again.
    body = (await async_client.get(f"/api/genes/{symbol}/position-statistics")).json()
    assert body["spatialMessage"] == "3D statistics unavailable: AlphaFold did not respond"
    assert len(calls) == 2


@pytest.mark.integration
async def test_no_model_outcome_is_cached(async_client, db_session, monkeypatch):
    symbol = _gene_with_annotations(db_session)
    _mock_linear_upstreams(monkeypatch)
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(404)

    monkeypatch.setattr(sources, "_client", lambda: sources.RetryableHTTPClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        sources.RetryConfig(max_retries=0)))  # fmt: skip
    for stars in (1, 2):  # different result keys, one AlphaFold cache entry
        url = f"/api/genes/{symbol}/position-statistics?min_stars={stars}"
        body = (await async_client.get(url)).json()
        assert body["spatial"] is None and body["provenance"]["alphafold"] is None
        assert body["spatialMessage"] == (
            "No full-length AlphaFold model for this protein, so no 3D statistics."
        )
    assert len(requests) == 1 and "alphafold.ebi.ac.uk/api/prediction" in requests[0]


def _mock_transport(monkeypatch, handler):
    monkeypatch.setattr(sources, "_client", lambda: sources.RetryableHTTPClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        sources.RetryConfig(max_retries=0)))  # fmt: skip


@pytest.mark.integration
async def test_alphafold_foreign_cif_and_unreadable_reply(async_client, db_session, monkeypatch):
    _mock_linear_upstreams(monkeypatch)
    seen = []

    def foreign(request):
        seen.append(request.url.host)
        acc = request.url.path.rsplit("/", 1)[-1]
        entry = {"entryId": "AF-X-F1", "uniprotAccession": acc, "uniprotStart": 1,
                 "uniprotEnd": 60, "cifUrl": "https://evil.example/model.cif"}  # fmt: skip
        return httpx.Response(200, json=[entry])

    _mock_transport(monkeypatch, foreign)
    url = f"/api/genes/{_gene_with_annotations(db_session)}/position-statistics"
    body = (await async_client.get(url)).json()
    assert body["status"] == "ready" and body["spatial"] is None
    assert body["spatialMessage"].startswith("No full-length AlphaFold model")
    assert seen == ["alphafold.ebi.ac.uk"]  # the foreign host was never contacted

    _mock_transport(monkeypatch, lambda request: httpx.Response(200, text="<html>oops</html>"))
    url = f"/api/genes/{_gene_with_annotations(db_session)}/position-statistics"
    res = await async_client.get(url)
    assert res.status_code == 200 and res.json()["linear"] is not None
    assert res.json()["spatialMessage"] == (
        "3D statistics unavailable: AlphaFold returned an unreadable response"
    )


@pytest.mark.integration
async def test_gnomad_unreadable_reply_is_502(async_client, db_session, monkeypatch):
    symbol = _gene_with_annotations(db_session)

    async def fake_seq(client, acc):
        return "M" + "A" * 59

    monkeypatch.setattr(sources, "fetch_uniprot_sequence", fake_seq)
    _mock_transport(monkeypatch, lambda request: httpx.Response(200, text="<html>busy</html>"))
    res = await async_client.get(f"/api/genes/{symbol}/position-statistics")
    assert res.status_code == 502
    assert res.json()["error"]["detail"] == "gnomAD returned an unreadable response"
