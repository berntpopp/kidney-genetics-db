"""STRING PPI per-gene results stay identical after indexing interactions by gene (#363)."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource

GOLDEN = Path(__file__).parent / "fixtures" / "string_ppi_golden.json"

# protein1, protein2, combined_score; P1-P4 map to genes, P9 has no gene
LINKS = [
    ("P1", "P2", 900),
    ("P2", "P1", 900),
    ("P1", "P3", 700),
    ("P1", "P3b", 750),  # second isoform of GENE3: the higher score must win
    ("P1", "P1", 999),  # self-interaction
    ("P1", "P4", 820),  # GENE4 is not a kidney gene
    ("P2", "P3", 820),
    ("P3", "P2", 820),
    ("P2", "P9", 990),  # unmapped protein
    ("P5", "P3", 450),  # below the score threshold
]
GENE_OF = {
    "P1": "GENE1",
    "P2": "GENE2",
    "P3": "GENE3",
    "P3b": "GENE3",
    "P4": "GENE4",
    "P5": "GENE5",
}
KIDNEY = {"GENE1": 80.0, "GENE2": 60.0, "GENE3": 40.0, "GENE5": 10.0}


def _source() -> StringPPIAnnotationSource:
    source = StringPPIAnnotationSource.__new__(StringPPIAnnotationSource)
    source.session = SimpleNamespace(commit=lambda: None)
    source.min_string_score = 500
    source.version = "test"
    source._protein_to_gene = None
    source._kidney_genes = set(KIDNEY)
    source._gene_evidence_scores = dict(KIDNEY)
    source._gene_ids = {g: i for i, g in enumerate(["GENE1", "GENE2", "GENE3", "GENE4", "GENE5"])}
    info = pd.DataFrame(
        {
            "#string_protein_id": [f"9606.{p}" for p in GENE_OF],
            "preferred_name": list(GENE_OF.values()),
        }
    )
    links = pd.DataFrame(
        [(f"9606.{a}", f"9606.{b}", s) for a, b, s in LINKS],
        columns=["protein1", "protein2", "combined_score"],
    )
    source._reads = iter([info, links])  # protein info, then physical links
    source.ensure_data_files = AsyncMock()
    source.data_dir = Path("/nonexistent")
    return source


@pytest.mark.asyncio
async def test_string_ppi_results_match_golden():
    source = _source()
    genes = [
        SimpleNamespace(id=i, approved_symbol=g)
        for i, g in enumerate(["GENE1", "GENE2", "GENE3", "GENE4", "GENE5"])
    ]
    with (
        patch("pandas.read_csv", side_effect=lambda *a, **k: next(source._reads)),
        patch.object(Path, "exists", return_value=True),
        patch(
            "app.core.percentile_service.PercentileService.get_cached_percentiles_only",
            AsyncMock(return_value={0: 0.9, 1: 0.5, 2: 0.1}),
        ),
    ):
        results = await source.fetch_batch(genes)

    got = json.loads(json.dumps(results, default=int, sort_keys=True))
    if not GOLDEN.exists():  # first run records the pre-refactor behaviour
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(got, indent=1, sort_keys=True))
    assert got == json.loads(GOLDEN.read_text())
