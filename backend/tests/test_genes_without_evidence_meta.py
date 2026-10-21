"""#337: /api/genes reports how many genes have no evidence rows at all."""

import pytest
from sqlalchemy import text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_meta_counts_genes_without_evidence(async_client, db_session):
    def count() -> int:
        return db_session.execute(
            text(
                "SELECT COUNT(*) FROM genes g WHERE NOT EXISTS "
                "(SELECT 1 FROM gene_evidence ge WHERE ge.gene_id = g.id)"
            )
        ).scalar_one()

    before = count()
    db_session.execute(
        text(
            "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
            "VALUES ('HGNC:NOEV337', 'NOEVIDENCE337', '{}')"
        )
    )
    db_session.flush()

    response = await async_client.get("/api/genes/", params={"page[size]": 1})

    assert response.status_code == 200
    assert response.json()["meta"]["genes_without_evidence"] == before + 1 == count()
