"""
Tests for the public gene-resolver endpoint and CRUD: GET /api/genes/resolve.

Covers each identifier branch of ``gene_crud.resolve_query`` and the JSON:API
endpoint behaviour (single hit, ambiguous list, 404).

Uses the existing PostgreSQL test database with transaction-rollback isolation
(see ``conftest.py``). All test data is created within the rolled-back
transaction so it never persists. Annotation branches (ENSG / NCBI / UniProt /
alias-via-HGNC) are seeded as ``gene_annotations`` rows directly, since
``resolve_query`` queries the ``gene_annotations`` JSONB (not the
``gene_annotations_summary`` materialized view, which cannot be refreshed inside
a test transaction).
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.crud.gene import gene_crud
from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation


def _unique_suffix() -> str:
    return uuid.uuid4().hex[:8].upper()


def _unique_hgnc_id() -> str:
    """A numeric HGNC id (matches ``^HGNC:\\d+$``) in a high range unlikely
    to collide with real HGNC ids in the seeded database."""
    return f"HGNC:{9_000_000 + (uuid.uuid4().int % 1_000_000)}"


def _make_gene(
    db: Session,
    *,
    symbol: str,
    hgnc_id: str,
    aliases: list[str] | None = None,
) -> Gene:
    """Create and flush a Gene within the test transaction."""
    gene = Gene(approved_symbol=symbol, hgnc_id=hgnc_id, aliases=aliases or [])
    db.add(gene)
    db.flush()
    return gene


def _add_hgnc_annotation(
    db: Session,
    gene: Gene,
    *,
    ensembl_gene_id: str | None = None,
    ncbi_gene_id: str | None = None,
    alias_symbol: list[str] | None = None,
    prev_symbol: list[str] | None = None,
    name: str | None = None,
) -> GeneAnnotation:
    """Attach an HGNC-source annotation with the keys the resolver consults."""
    annotations: dict = {}
    if ensembl_gene_id is not None:
        annotations["ensembl_gene_id"] = ensembl_gene_id
    if ncbi_gene_id is not None:
        annotations["ncbi_gene_id"] = ncbi_gene_id
    if alias_symbol is not None:
        annotations["alias_symbol"] = alias_symbol
    if prev_symbol is not None:
        annotations["prev_symbol"] = prev_symbol
    if name is not None:
        annotations["name"] = name

    ann = GeneAnnotation(gene_id=gene.id, source="hgnc", version="test", annotations=annotations)
    db.add(ann)
    db.flush()
    return ann


def _add_uniprot_annotation(db: Session, gene: Gene, *, accession: str) -> GeneAnnotation:
    ann = GeneAnnotation(
        gene_id=gene.id,
        source="uniprot",
        version="test",
        annotations={"accession": accession},
    )
    db.add(ann)
    db.flush()
    return ann


# ---------------------------------------------------------------------------
# CRUD unit tests: gene_crud.resolve_query
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveQueryCrud:
    """Direct tests of each resolver branch."""

    def test_exact_symbol(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        gene = _make_gene(db_session, symbol=f"PKD1{suffix}", hgnc_id=f"HGNC:T{suffix}")
        result = gene_crud.resolve_query(db_session, f"PKD1{suffix}")
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_exact_symbol_case_insensitive(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        gene = _make_gene(db_session, symbol=f"PKD1{suffix}", hgnc_id=f"HGNC:T{suffix}")
        result = gene_crud.resolve_query(db_session, f"pkd1{suffix.lower()}")
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_hgnc_id(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        hgnc_id = _unique_hgnc_id()
        gene = _make_gene(db_session, symbol=f"GENE{suffix}", hgnc_id=hgnc_id)
        result = gene_crud.resolve_query(db_session, hgnc_id)
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_hgnc_id_case_insensitive_prefix(self, db_session: Session) -> None:
        # The "HGNC:" prefix detection is case-insensitive; the stored hgnc_id
        # itself is compared exactly via get_by_hgnc_id, so use a numeric id.
        suffix = uuid.uuid4().int % 1_000_000
        hgnc_id = f"HGNC:{suffix}"
        gene = _make_gene(db_session, symbol=f"GENE{suffix}", hgnc_id=hgnc_id)
        result = gene_crud.resolve_query(db_session, f"hgnc:{suffix}")
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_ensembl_id(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        ensg = f"ENSG{uuid.uuid4().int % 100000000000:011d}"
        gene = _make_gene(db_session, symbol=f"GENE{suffix}", hgnc_id=f"HGNC:T{suffix}")
        _add_hgnc_annotation(db_session, gene, ensembl_gene_id=ensg)
        result = gene_crud.resolve_query(db_session, ensg)
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_ncbi_id(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        ncbi = str(uuid.uuid4().int % 1_000_000_000)
        gene = _make_gene(db_session, symbol=f"GENE{suffix}", hgnc_id=f"HGNC:T{suffix}")
        _add_hgnc_annotation(db_session, gene, ncbi_gene_id=ncbi)
        result = gene_crud.resolve_query(db_session, ncbi)
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_uniprot_accession(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        # Valid UniProt accession matching ^[OPQ][0-9][A-Z0-9]{3}[0-9]$ that is
        # synthetic (unlikely to collide with seeded real accessions).
        accession = "Q9ZZZ9"
        gene = _make_gene(db_session, symbol=f"GENE{suffix}", hgnc_id=_unique_hgnc_id())
        _add_uniprot_annotation(db_session, gene, accession=accession)
        result = gene_crud.resolve_query(db_session, accession)
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_alias_via_genes_array(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        alias = f"OLDSYM{suffix}"
        gene = _make_gene(
            db_session,
            symbol=f"GENE{suffix}",
            hgnc_id=f"HGNC:T{suffix}",
            aliases=[alias],
        )
        result = gene_crud.resolve_query(db_session, alias.lower())
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_alias_via_hgnc_annotation(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        alias = f"TRPP{suffix}"
        gene = _make_gene(db_session, symbol=f"GENE{suffix}", hgnc_id=f"HGNC:T{suffix}")
        _add_hgnc_annotation(db_session, gene, alias_symbol=[alias])
        result = gene_crud.resolve_query(db_session, alias)
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_prev_symbol_via_hgnc_annotation(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        prev = f"PREV{suffix}"
        gene = _make_gene(db_session, symbol=f"GENE{suffix}", hgnc_id=f"HGNC:T{suffix}")
        _add_hgnc_annotation(db_session, gene, prev_symbol=[prev])
        result = gene_crud.resolve_query(db_session, prev)
        assert isinstance(result, Gene)
        assert result.id == gene.id

    def test_ambiguous_alias(self, db_session: Session) -> None:
        suffix = _unique_suffix()
        shared_alias = f"SHARED{suffix}"
        gene_a = _make_gene(
            db_session,
            symbol=f"GENEA{suffix}",
            hgnc_id=f"HGNC:TA{suffix}",
            aliases=[shared_alias],
        )
        gene_b = _make_gene(
            db_session,
            symbol=f"GENEB{suffix}",
            hgnc_id=f"HGNC:TB{suffix}",
            aliases=[shared_alias],
        )
        result = gene_crud.resolve_query(db_session, shared_alias)
        assert isinstance(result, list)
        ids = {g.id for g in result}
        assert gene_a.id in ids
        assert gene_b.id in ids
        assert len(result) >= 2

    def test_unknown_returns_none(self, db_session: Session) -> None:
        result = gene_crud.resolve_query(db_session, f"NOTAGENE{_unique_suffix()}")
        assert result is None

    def test_blank_query_returns_none(self, db_session: Session) -> None:
        assert gene_crud.resolve_query(db_session, "   ") is None


# ---------------------------------------------------------------------------
# Endpoint tests: GET /api/genes/resolve
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestResolveEndpoint:
    async def test_resolve_exact_symbol(
        self, async_client: AsyncClient, db_session: Session
    ) -> None:
        suffix = _unique_suffix()
        symbol = f"PKD1{suffix}"
        gene = _make_gene(db_session, symbol=symbol, hgnc_id=f"HGNC:T{suffix}")
        db_session.commit()

        resp = await async_client.get(f"/api/genes/resolve?query={symbol}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["type"] == "gene"
        assert body["data"]["id"] == str(gene.id)
        attrs = body["data"]["attributes"]
        assert attrs["approved_symbol"] == symbol
        assert attrs["hgnc_id"] == f"HGNC:T{suffix}"
        assert attrs["matched_on"] == symbol
        assert attrs["match_type"] == "symbol"

    async def test_resolve_hgnc_id(self, async_client: AsyncClient, db_session: Session) -> None:
        suffix = _unique_suffix()
        hgnc_id = _unique_hgnc_id()
        gene = _make_gene(db_session, symbol=f"GENE{suffix}", hgnc_id=hgnc_id)
        db_session.commit()

        resp = await async_client.get(f"/api/genes/resolve?query={hgnc_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["id"] == str(gene.id)
        assert body["data"]["attributes"]["match_type"] == "hgnc_id"

    async def test_resolve_alias_to_canonical(
        self, async_client: AsyncClient, db_session: Session
    ) -> None:
        suffix = _unique_suffix()
        alias = f"OLDSYM{suffix}"
        gene = _make_gene(
            db_session,
            symbol=f"GENE{suffix}",
            hgnc_id=f"HGNC:T{suffix}",
            aliases=[alias],
        )
        db_session.commit()

        resp = await async_client.get(f"/api/genes/resolve?query={alias}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["id"] == str(gene.id)
        assert body["data"]["attributes"]["approved_symbol"] == f"GENE{suffix}"
        assert body["data"]["attributes"]["match_type"] == "alias"

    async def test_resolve_ambiguous(self, async_client: AsyncClient, db_session: Session) -> None:
        suffix = _unique_suffix()
        shared_alias = f"SHARED{suffix}"
        gene_a = _make_gene(
            db_session,
            symbol=f"GENEA{suffix}",
            hgnc_id=f"HGNC:TA{suffix}",
            aliases=[shared_alias],
        )
        gene_b = _make_gene(
            db_session,
            symbol=f"GENEB{suffix}",
            hgnc_id=f"HGNC:TB{suffix}",
            aliases=[shared_alias],
        )
        db_session.commit()

        resp = await async_client.get(f"/api/genes/resolve?query={shared_alias}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] is None
        assert body["meta"]["ambiguous"] is True
        candidate_ids = {c["id"] for c in body["meta"]["candidates"]}
        assert str(gene_a.id) in candidate_ids
        assert str(gene_b.id) in candidate_ids
        # Candidate shape
        for cand in body["meta"]["candidates"]:
            assert set(cand.keys()) >= {"id", "hgnc_id", "approved_symbol"}

    async def test_resolve_not_found(self, async_client: AsyncClient) -> None:
        resp = await async_client.get(f"/api/genes/resolve?query=NOTAGENE{_unique_suffix()}")
        assert resp.status_code == 404

    async def test_resolve_is_public_no_auth(
        self, async_client: AsyncClient, db_session: Session
    ) -> None:
        """The resolve endpoint must work without any auth header."""
        suffix = _unique_suffix()
        symbol = f"PUB{suffix}"
        _make_gene(db_session, symbol=symbol, hgnc_id=f"HGNC:T{suffix}")
        db_session.commit()

        assert "Authorization" not in async_client.headers
        resp = await async_client.get(f"/api/genes/resolve?query={symbol}")
        assert resp.status_code == 200

    async def test_resolve_not_shadowed_by_gene_symbol_route(
        self, async_client: AsyncClient, db_session: Session
    ) -> None:
        """`/resolve` must be matched by the resolver, not the /{gene_symbol} route.

        If shadowed, the request would be treated as a lookup for a gene named
        'resolve' and 404 with that identifier; instead it resolves the query.
        """
        suffix = _unique_suffix()
        symbol = f"NOSHADOW{suffix}"
        gene = _make_gene(db_session, symbol=symbol, hgnc_id=f"HGNC:T{suffix}")
        db_session.commit()

        resp = await async_client.get(f"/api/genes/resolve?query={symbol}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == str(gene.id)
