"""GTEx PAR_Y duplicate rows must not overwrite the X-chromosome rows (#365.2)."""

from pathlib import Path

import pytest

from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

GCT = """\
#1.2
2\t1
Name\tDescription\tKidney_Cortex
ENSG00000185960.13\tSHOX\t3.5
ENSG00000185960.13_PAR_Y\tSHOX\t0
"""


@pytest.mark.unit
def test_par_y_row_is_skipped(tmp_path: Path) -> None:
    gct = tmp_path / "median.gct"
    gct.write_text(GCT)
    data = GTExAnnotationSource.__new__(GTExAnnotationSource).parse_bulk_file(gct)
    assert data["SHOX"]["tissues"]["Kidney_Cortex"]["median_tpm"] == pytest.approx(3.5)
    assert data["SHOX"]["gencode_id"] == "ENSG00000185960.13"
