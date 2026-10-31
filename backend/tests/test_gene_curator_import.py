"""One-shot Gene Curator export upload (#448), with a fixture in the pinned export v1 shape."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.security import create_access_token
from app.models.gene import Gene
from app.models.gene_disease_association import GeneDiseaseAssociation as GDA
from app.models.gene_disease_association import GeneDiseaseAssociationEvent as Event
from app.models.user import User
from app.schemas.gene_disease_association import AssociationUpdate, ReviewDecision
from app.services import gene_curator_import as gc
from app.services import gene_disease_association_service as workflow
from tests.fixtures.auth import get_or_create_user

URL = "/api/admin/gene-curator/import"
PAGE = json.loads((Path(__file__).parent / "fixtures/gene_curator_export.json").read_text())
MENDELIAN, SUSCEPTIBILITY, PROBABLE, DIGENIC, NOT_IN_KGDB = PAGE["items"]


def _row(base: dict, **changes) -> dict:
    return {**copy.deepcopy(base), **changes}


def _page(*items: dict) -> dict:
    return {**PAGE, "items": list(items)}


def _file(doc) -> dict:
    content = doc if isinstance(doc, bytes) else json.dumps(doc).encode()
    return {"file": ("export.json", content, "application/json")}


def _bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


@pytest.fixture
def admin(db_session):
    return get_or_create_user(
        db_session, "gc448_admin", "gc448_admin@example.com", "Pw-1!", "admin"
    )


@pytest.fixture
def curator(db_session):
    return get_or_create_user(db_session, "gc448_cur", "gc448_cur@example.com", "Pw-1!", "curator")


@pytest.fixture
def genes(db_session):
    rows = [
        Gene(approved_symbol="GC448A", hgnc_id="HGNC:99944801"),
        Gene(approved_symbol="GC448B", hgnc_id="HGNC:99944802"),
    ]
    db_session.add_all(rows)
    db_session.commit()
    return rows


def _records(db_session) -> list[GDA]:
    return db_session.query(GDA).filter(GDA.source == "gene_curator").order_by(GDA.id).all()


def _events(db_session, record: GDA) -> list[tuple[str, int]]:
    rows = db_session.query(Event.action, Event.user_id).filter(Event.association_id == record.id)
    return [tuple(r) for r in rows.order_by(Event.id)]


def test_fixture_matches_pinned_schema_and_extra_fields_pass() -> None:
    assert len(gc.parse_export(json.dumps(PAGE).encode())) == 5
    added = _page(_row(MENDELIAN, field_added_in_v1={"x": 1}))
    assert len(gc.parse_export(json.dumps([added, _page()]).encode())) == 1


@pytest.mark.parametrize(
    "doc, error",
    [
        (_page(_row(MENDELIAN, total_score="16")), "$[0].items[0].total_score: matches no"),
        (
            _page({k: v for k, v in MENDELIAN.items() if k != "hgnc_id"}),
            "items[0].hgnc_id: required",
        ),
        (_page(_row(MENDELIAN, curation_id="not-a-uuid")), "curation_id: not a uuid"),
        (_page(_row(MENDELIAN, relationship_type="risk")), "relationship_type: must be one of"),
        ({**PAGE, "export_version": "2"}, "export_version: must be '1'"),
        ({"items": "x"}, "items: expected array"),
    ],
)
def test_schema_mismatch_is_rejected(doc, error) -> None:
    with pytest.raises(gc.DomainValidationError) as e:
        gc.parse_export(json.dumps(doc).encode())
    assert "not a Gene Curator export v1" in e.value.message and error in e.value.message


@pytest.mark.integration
async def test_upload_is_admin_only_and_bad_files_are_4xx(
    async_client, db_session, admin, curator, monkeypatch
) -> None:
    assert (await async_client.post(URL, files=_file(PAGE))).status_code == 401
    assert (
        await async_client.post(URL, files=_file(PAGE), headers=_bearer(curator))
    ).status_code == 403
    for content in (
        b"not json",
        b"\xff\xfe",
        json.dumps(_page(_row(MENDELIAN, url=None))).encode(),
    ):
        resp = await async_client.post(URL, files=_file(content), headers=_bearer(admin))
        assert resp.status_code == 422, resp.text
    # Schema errors come as a list of paths, not only inside the message
    assert resp.json()["error"]["details"]["errors"] == ["$[0].items[0].url: expected string"]
    monkeypatch.setattr(gc, "MAX_UPLOAD", 10)
    resp = await async_client.post(URL, files=_file(PAGE), headers=_bearer(admin))
    assert resp.status_code == 422 and "larger than" in resp.json()["error"]["message"]
    assert _records(db_session) == []


@pytest.mark.integration
async def test_upload_creates_drafts_and_reupload_skips(
    async_client, db_session, genes, admin
) -> None:
    resp = await async_client.post(URL, files=_file(PAGE), headers=_bearer(admin))
    assert resp.status_code == 200, resp.text
    report = resp.json()
    # Mendelian and susceptibility on one gene, disease and MOI are two records (#472)
    assert [c["curation_id"] for c in report["created"]] == [
        MENDELIAN["curation_id"],
        SUSCEPTIBILITY["curation_id"],
    ]
    assert [g["hgnc_id"] for g in report["genes_not_in_kgdb"]] == ["HGNC:99944899"]
    assert len(report["rejected"]) == 2 and report["conflicts"] == []

    account = db_session.query(User).filter(User.username == "gene-curator-import").one()
    assert (account.is_active, account.role) == (False, "viewer")
    mendelian, susceptibility = _records(db_session)
    for record in (mendelian, susceptibility):
        assert (record.status, record.curator_id) == ("draft", account.id)
        assert _events(db_session, record) == [("gc_import", admin.id)]
    assert susceptibility.evidence_strength == "Established association"
    assert mendelian.evidence_strength == "Definitive"
    assert (mendelian.disease_id, mendelian.moi) == ("MONDO:0009633", "HP:0000007")
    assert (mendelian.external_id, mendelian.external_url) == (
        MENDELIAN["curation_id"],
        MENDELIAN["url"],
    )
    assert (mendelian.external_curator, mendelian.external_reviewer) == (
        "Alice Curator",
        "Bob Reviewer",
    )
    assert (mendelian.methodology, mendelian.methodology_version) == (
        "KGDB Mendelian Curation",
        "1",
    )
    assert mendelian.scores == {
        "genetic": 10.0,
        "experimental": 6.0,
        "association": None,
        "total": 16.0,
    }
    assert mendelian.citations[0] == "PMID:31000001" and len(mendelian.citations) == 14
    assert mendelian.evidence_summary.startswith("Ten unrelated")

    # Re-upload: nothing changes, every imported curation is reported
    again = (await async_client.post(URL, files=_file([PAGE]), headers=_bearer(admin))).json()
    assert [a["record_id"] for a in again["already_imported"]] == [mendelian.id, susceptibility.id]
    assert again["created"] == [] and len(_records(db_session)) == 2
    assert _events(db_session, mendelian) == [("gc_import", admin.id)]


@pytest.mark.integration
def test_diagnostics_map_to_kgdb(db_session, genes, admin) -> None:
    report = gc.import_export(db_session, [MENDELIAN], admin)
    [record] = _records(db_session)
    d = record.diagnostics
    transcript = d["recommended_transcript"]
    assert (transcript["refseq"], transcript["mane_status"]) == ("NM_006580.4", "not_checked")
    assert transcript["verified_via"] == "MANE Select in Ensembl 115"
    assert d["detectability_note"] == "standard short-read testing adequate"
    [row] = d["detectability"]
    assert row["tools"] == [
        {
            "name": "ExomeDepth",
            "url": "https://github.com/vplagnol/ExomeDepth",
            "pmid_or_doi": "PMID:22942019",
        }
    ]
    [resource] = d["resources"]
    assert resource["verified"] == {"method": "fetched", "date": "2026-10-30"}
    assert resource["country_or_scope"] == "EU"
    assert report["dropped_fields"] == []


@pytest.mark.integration
def test_unknown_values_rejected(db_session, genes, admin) -> None:
    rows = [
        PROBABLE,
        DIGENIC,
        _row(
            MENDELIAN, curation_id="11111111-0000-4000-8000-0000000000aa", moi_hpo_id="HP:0000001"
        ),
        # A susceptibility tier is only valid for a susceptibility relationship
        _row(
            MENDELIAN,
            curation_id="11111111-0000-4000-8000-0000000000ab",
            final_classification="likely",
        ),
        _row(
            MENDELIAN,
            curation_id="11111111-0000-4000-8000-0000000000ac",
            status="archived",
            archive_reason="Curation deleted",
        ),
    ]
    report = gc.import_export(db_session, rows, admin)
    reasons = {r["curation_id"][-2:]: r["reason"] for r in report["rejected"]}
    assert "'probable' is not a mendelian class" in reasons["03"]
    assert "'Digenic' has no HPO term" in reasons["04"]
    assert "unknown MOI 'HP:0000001'" in reasons["aa"]
    assert "'likely' is not a mendelian class" in reasons["ab"]
    assert "archived" in reasons["ac"]
    assert _records(db_session) == []


@pytest.mark.integration
def test_existing_record_on_the_entity_is_a_conflict(db_session, genes, admin) -> None:
    kgdb = GDA(
        gene_id=genes[0].id,
        disease_id="MONDO:0009633",
        disease_name="x",
        evidence_strength="Strong",
        moi="HP:0000007",
        citations=["PMID:1"],
        curator_id=admin.id,
    )
    db_session.add(kgdb)
    db_session.commit()
    # A Gene Curator re-curation has a new curation_id; the KGDB key still decides
    recurated = _row(MENDELIAN, curation_id="11111111-0000-4000-8000-000000000011")
    report = gc.import_export(db_session, [MENDELIAN, recurated], admin)
    assert [(c["existing_record_id"], c["existing_source"]) for c in report["conflicts"]] == [
        (kgdb.id, "kgdb"),
        (kgdb.id, "kgdb"),
    ]
    assert report["created"] == [] and _records(db_session) == []


def _publish(db_session, record: GDA, user: User) -> None:
    db_session.refresh(record)
    seen = ReviewDecision(expected_updated_at=record.updated_at)
    workflow.publish(db_session, record.id, seen, user)


@pytest.mark.integration
def test_unedited_import_one_curator_submits_and_publishes(
    db_session, genes, admin, curator
) -> None:
    gc.import_export(db_session, [MENDELIAN], admin)
    [record] = _records(db_session)
    assert workflow.to_response(record)["imported_unclaimed"] is True
    workflow.submit(db_session, record.id, curator)
    _publish(db_session, record, curator)  # Gene Curator's review covers an unchanged import
    assert (record.status, record.reviewer_id) == ("published", curator.id)
    assert record.curator.username == "gene-curator-import"
    assert [a for a, _ in _events(db_session, record)] == ["gc_import", "submit", "publish"]


@pytest.mark.integration
def test_editing_an_import_takes_it_over(db_session, genes, admin, curator) -> None:
    second = get_or_create_user(db_session, "gc448_c2", "gc448_c2@example.com", "Pw-1!", "curator")
    gc.import_export(db_session, [MENDELIAN], admin)
    [record] = _records(db_session)
    workflow.update(db_session, record.id, AssociationUpdate(evidence_summary="Checked"), curator)
    assert record.curator_id == curator.id
    assert workflow.to_response(record)["imported_unclaimed"] is False
    with pytest.raises(workflow.PermissionDeniedError):  # now author-only
        workflow.submit(db_session, record.id, second)
    workflow.submit(db_session, record.id, curator)
    with pytest.raises(workflow.PermissionDeniedError):  # no self-review of the edit
        _publish(db_session, record, curator)
    _publish(db_session, record, second)
    assert (record.status, record.curator_id, record.reviewer_id) == (
        "published",
        curator.id,
        second.id,
    )


@pytest.mark.integration
def test_active_import_account_is_neither_author_nor_reused(db_session, genes, admin) -> None:
    gc.import_export(db_session, [MENDELIAN], admin)
    account = gc.import_account(db_session)
    account.is_active = True
    db_session.commit()
    [record] = _records(db_session)
    assert workflow.unclaimed_import(record) is False
    with pytest.raises(gc.ResourceConflictError):
        gc.import_export(db_session, [SUSCEPTIBILITY], admin)


@pytest.mark.integration
async def test_malformed_evidence_rejects_only_that_row(
    async_client, db_session, genes, admin
) -> None:
    evidence = MENDELIAN["evidence"]
    diagnostics = evidence["diagnostics"]
    detectability = diagnostics["detectability"][0]
    bad = {
        "a1": {**evidence, "diagnostics_notes": "x"},
        "a2": {**evidence, "diagnostics": ["x"]},
        "a3": {**evidence, "diagnostics": {**diagnostics, "recommended_transcript": "NM_1.1"}},
        "a4": {**evidence, "diagnostics": {**diagnostics, "detectability": ["x"]}},
        "a5": {**evidence, "diagnostics": {**diagnostics, "resources": [1]}},
        "a6": {
            **evidence,
            "diagnostics": {**diagnostics, "detectability": [{**detectability, "tools": "abc"}]},
        },
        "a7": {**evidence, "evidence_summary": 5},
    }
    rows = [
        _row(MENDELIAN, curation_id=f"11111111-0000-4000-8000-0000000000{k}", evidence=v)
        for k, v in bad.items()
    ]
    resp = await async_client.post(
        URL, files=_file(_page(*rows, SUSCEPTIBILITY)), headers=_bearer(admin)
    )
    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert [c["curation_id"] for c in report["created"]] == [SUSCEPTIBILITY["curation_id"]]
    assert sorted(r["curation_id"][-2:] for r in report["rejected"]) == sorted(bad)
    assert "tools must be a list" in str(report["rejected"])
    assert len(_records(db_session)) == 1


@pytest.mark.integration
def test_other_scope_rejected_and_curation_id_normalised(db_session, genes, admin) -> None:
    other = _row(SUSCEPTIBILITY, scope_name="other-scope")
    upper = _row(MENDELIAN, curation_id=MENDELIAN["curation_id"].upper())
    report = gc.import_export(db_session, [other, upper], admin)
    assert "scope 'other-scope' is not 'kidney-genetics'" in report["rejected"][0]["reason"]
    [record] = _records(db_session)
    assert record.external_id == MENDELIAN["curation_id"]
    assert gc.import_export(db_session, [MENDELIAN], admin)["already_imported"]


@pytest.mark.integration
def test_first_import_race_reuses_the_account(db_session, genes, admin, monkeypatch) -> None:
    """Another upload created the account between our lookup and our commit (deterministic)."""
    existing = gc.import_account(db_session)
    real_query, real_rollback = db_session.query, db_session.rollback
    misses, rollbacks = [], []

    def query(*entities):
        if entities[0] is User and not misses:  # the first lookup misses, once
            misses.append(entities)
            return SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: None))
        return real_query(*entities)

    def rollback():
        rollbacks.append(1)
        real_rollback()

    monkeypatch.setattr(db_session, "query", query)
    monkeypatch.setattr(db_session, "rollback", rollback)
    report = gc.import_export(db_session, [MENDELIAN], admin)
    monkeypatch.undo()

    assert misses and rollbacks == [1]  # the duplicate insert hit the unique key and rolled back
    assert [c["curation_id"] for c in report["created"]] == [MENDELIAN["curation_id"]]
    [record] = _records(db_session)
    assert record.curator_id == existing.id
    assert db_session.query(User).filter(User.username == "gene-curator-import").count() == 1


@pytest.mark.parametrize(
    "key, strength",
    [
        ("established", "Established association"),
        ("likely", "Likely association"),
        ("uncertain", "Uncertain association"),
        ("refuted", "Refuted association"),
    ],
)
def test_susceptibility_classes_map_to_kgdb_tiers(key, strength) -> None:
    values = gc._values(_row(SUSCEPTIBILITY, final_classification=key), [])
    assert (values["relationship_type"], values["evidence_strength"]) == (
        "susceptibility",
        strength,
    )


def test_values_keep_the_classification_when_only_diagnostics_fail() -> None:
    """GC does not check evidence-table cells: bad diagnostics are dropped, not the row."""
    evidence = copy.deepcopy(MENDELIAN["evidence"])
    evidence["diagnostics"]["resources"][0]["type"] = "patient_organization"  # US spelling
    dropped: list[str] = []
    values = gc._values(_row(MENDELIAN, evidence=evidence, mondo_id="MONDO_0009633"), dropped)
    assert (values["evidence_strength"], values["diagnostics"]) == ("Definitive", None)
    assert values["disease_id"] == "MONDO:0009633"
    assert any(d.startswith("diagnostics (diagnostics.resources.0.type") for d in dropped)
    with pytest.raises(ValueError, match="citations"):  # any other error still rejects
        gc._values(_row(MENDELIAN, evidence=evidence, pmids=[]), [])


def test_values_keep_susceptibility_association_points_and_flag_missing_evidence() -> None:
    row = _row(SUSCEPTIBILITY, scores={"association_total": 4, "total_score": 5}, evidence=None)
    dropped: list[str] = []
    values = gc._values(row, dropped)
    assert values["scores"]["association"] == 4
    assert dropped == ["evidence (null: export with a kidney-genetics member's token)"]


ADOPTION = {
    "type": "Statement",
    "id": "CGGV:assertion_x",
    "classification": "Definitive",
    "reportedIn": [{"title": "ClinGen KCCD", "urls": ["https://search.clinicalgenome.org/x"]}],
    "contributions": [
        {
            "contributor": {"name": "Kidney Cystic and Ciliopathy Disorders GCEP"},
            "activityType": {"name": "interpreter"},
            "date": "2023-10-25T00:00:00Z",
        }
    ],
}


@pytest.mark.integration
def test_adopted_clingen_imports_without_points_or_pmids(db_session, genes, admin) -> None:
    row = _row(
        MENDELIAN,
        adoption=ADOPTION,
        pmids=[],
        computed_verdict="no_known",
        curator_classification_rationale="ClinGen citation",
        genetic_score=0,
        experimental_score=0,
        total_score=0,
    )
    report = gc.import_export(db_session, [row], admin)
    assert report["rejected"] == []
    [record] = _records(db_session)
    assert (record.citations, record.scores) == ([], None)
    assert record.methodology == gc.ADOPTED and record.methodology_version is None
    assert record.adopted_clingen["expert_panel"].startswith("Kidney Cystic")
    assert record.adopted_clingen["classified_date"] == "2023-10-25"
    assert record.classification_rationale is None
    with pytest.raises(ValueError, match="malformed"):
        gc._values(_row(row, adoption={"id": "x"}), [])


def test_values_cite_clingen_beside_our_own_curation() -> None:
    row = _row(MENDELIAN, clingen_reference=ADOPTION, final_classification="definitive")
    values = gc._values(row, [])
    assert values["methodology"] != gc.ADOPTED and values["scores"] is not None
    assert values["adopted_clingen"]["classification"] == "Definitive"
    assert values["classification_rationale"] is None


def test_values_need_a_reason_to_differ_from_clingen() -> None:
    row = _row(
        MENDELIAN,
        clingen_reference=ADOPTION,
        final_classification="strong",
        computed_verdict="strong",
        curator_classification_rationale=None,
    )
    with pytest.raises(ValueError, match="differs from ClinGen"):
        gc._values(row, [])
    values = gc._values(_row(row, curator_classification_rationale="no replication"), [])
    assert values["classification_rationale"] == "no replication"
    assert values["evidence_summary"] == MENDELIAN["evidence"]["evidence_summary"]
    both = gc._values(
        _row(
            row,
            computed_verdict="definitive",
            final_classification="moderate",
            curator_classification_rationale="no replication",
        ),
        [],
    )
    assert both["classification_rationale"] == "no replication"
    with pytest.raises(ValueError, match="at least one PMID"):
        gc._values(_row(row, pmids=[], curator_classification_rationale="x"), [])


def test_values_credit_software_agents_and_keep_the_override_reason() -> None:
    software = {"contributor": {"name": "claude-opus", "agentType": "software"}}
    row = _row(
        MENDELIAN,
        contributions=[software, {"contributor": {"name": "x", "agentType": "person"}}],
        computed_verdict="limited",
        final_classification="moderate",
        curator_classification_rationale="two large families",
    )
    values = gc._values(row, [])
    assert values["ai_agents"] == ["claude-opus"]
    assert values["external_curator"] == MENDELIAN["curator_name"]
    assert values["classification_rationale"] == "two large families"
    assert "two large families" not in values["evidence_summary"]
    agreed = gc._values(_row(row, final_classification="limited"), [])
    assert agreed["classification_rationale"] is None  # nothing departs, nothing to explain


@pytest.mark.integration
def test_each_named_risk_allele_is_its_own_entity(db_session, genes, admin) -> None:
    def allele(cid: str, name: str | None) -> dict:
        return _row(
            SUSCEPTIBILITY, curation_id=f"11111111-0000-4000-8000-0000000000{cid}", risk_allele=name
        )

    report = gc.import_export(
        db_session, [allele("b1", "rs1 A"), allele("b2", "rs2 G"), allele("b3", "rs1 A")], admin
    )
    assert [c["curation_id"][-2:] for c in report["created"]] == ["b1", "b2"]
    assert [c["curation_id"][-2:] for c in report["conflicts"]] == ["b3"]
    assert {r.risk_allele for r in _records(db_session)} == {"rs1 A", "rs2 G"}
    with pytest.raises(ValueError, match="risk_allele is only for a susceptibility"):
        gc._values(_row(MENDELIAN, risk_allele="rs1 A"), [])


def test_values_keep_a_long_synopsis() -> None:
    evidence = {**copy.deepcopy(MENDELIAN["evidence"]), "evidence_summary": "x" * 3000}
    assert len(gc._values(_row(MENDELIAN, evidence=evidence), [])["evidence_summary"]) == 3000


def test_values_read_gc_iteration8_fields() -> None:
    """GC #619: undetermined MOI exports the HPO root, association points get a field."""
    row = _row(
        SUSCEPTIBILITY,
        moi_hpo_id="HP:0000005",
        mode_of_inheritance="UNDETERMINED",
        association_score=6,
        scores={"association_total": 1},
    )
    values = gc._values(row, [])
    assert (values["moi"], values["scores"]["association"]) == (None, 6)
    no_id = _row(SUSCEPTIBILITY, moi_hpo_id=None, mode_of_inheritance="HP:0000005")
    assert gc._values(no_id, [])["moi"] is None


AI_ROW = {"approval_kind": "ai", "approval_model": "model-x"}


@pytest.mark.integration
def test_ai_approved_import_is_published_pending_human_review(db_session, genes, admin) -> None:
    gc.import_export(db_session, [_row(MENDELIAN, **AI_ROW), SUSCEPTIBILITY], admin)
    ai, human = _records(db_session)
    assert (ai.status, ai.reviewer_id, ai.approval_kind, ai.approval_model) == (
        "published",
        None,
        "ai",
        "model-x",
    )
    assert ai.published_at is not None and ai.human_reviewed_at is None
    assert (human.status, human.approval_kind, human.approval_model) == ("draft", "human", None)
    assert workflow.to_response(ai)["human_reviewer_name"] is None


@pytest.mark.integration
async def test_human_review_endpoint(async_client, db_session, genes, admin, curator) -> None:
    gc.import_export(db_session, [_row(MENDELIAN, **AI_ROW)], admin)
    [record] = _records(db_session)
    url = f"/api/curation/associations/{record.id}/human-review"
    seen = {"expected_updated_at": record.updated_at.isoformat()}
    viewer = get_or_create_user(db_session, "gc639_v", "gc639_v@example.com", "Pw-1!", "viewer")
    assert (await async_client.post(url, json=seen, headers=_bearer(viewer))).status_code == 403
    stale = {"expected_updated_at": "2000-01-01T00:00:00+00:00"}
    assert (await async_client.post(url, json=stale, headers=_bearer(curator))).status_code == 409
    with pytest.raises(workflow.PermissionDeniedError):  # the import account never reviews
        workflow.human_review(
            db_session, record.id, ReviewDecision(**seen), gc.import_account(db_session)
        )
    db_session.rollback()
    response = await async_client.post(url, json=seen, headers=_bearer(curator))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["human_reviewed_at"] and body["human_reviewer_name"]
    assert body["approval_kind"] == "ai" and body["status"] == "published"
    again = {"expected_updated_at": body["updated_at"]}
    assert (await async_client.post(url, json=again, headers=_bearer(curator))).status_code == 409
    db_session.refresh(record)
    assert [a for a, _ in _events(db_session, record)] == ["gc_import", "human_review"]


@pytest.mark.integration
def test_human_publishing_an_ai_import_is_its_human_review(
    db_session, genes, admin, curator
) -> None:
    second = get_or_create_user(db_session, "gc639_c2", "gc639_c2@example.com", "Pw-1!", "curator")
    gc.import_export(db_session, [_row(MENDELIAN, **AI_ROW)], admin)
    [record] = _records(db_session)
    seen = ReviewDecision(expected_updated_at=record.updated_at)
    workflow.return_to_draft(db_session, record.id, seen, second)
    workflow.update(db_session, record.id, AssociationUpdate(evidence_summary="Checked"), curator)
    workflow.submit(db_session, record.id, curator)
    _publish(db_session, record, second)
    assert (record.human_reviewer_id, record.approval_kind) == (second.id, "ai")
    assert record.human_reviewed_at == record.published_at
