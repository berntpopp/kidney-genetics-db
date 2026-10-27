"""Kidney keyword matching: keywords.yaml list with an explicit "adrenal" exclusion (#369)."""

import pytest

from app.core.datasource_config import matches_kidney_keyword


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "classic congenital adrenal hyperplasia due to 21-hydroxylase deficiency",
        "X-linked adrenoleukodystrophy",
        "adrenal insufficiency",
        "cystic fibrosis",
        "tubulinopathy",
        "tubular aggregate myopathy",
    ],
)
def test_non_kidney_diseases_do_not_match(text):
    assert not matches_kidney_keyword(text)


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "renal cysts and diabetes syndrome",
        "nephronophthisis 1",
        "steroid-resistant nephrotic syndrome",
        "autosomal dominant polycystic kidney disease 1",
        "Alport syndrome",
        "focal segmental glomerulosclerosis 4",
        "oculocerebrorenal syndrome",
        "branchiootorenal syndrome 1",
        "Fanconi renotubular syndrome 1",
    ],
)
def test_kidney_diseases_match(text):
    assert matches_kidney_keyword(text)


@pytest.mark.unit
def test_adrenal_exclusion_does_not_veto_real_kidney_term():
    assert matches_kidney_keyword("adrenal and renal malformation")


@pytest.mark.unit
def test_explicit_keyword_list_applies_exclusion():
    assert matches_kidney_keyword("Renal tubulopathies", ["renal"])
    assert not matches_kidney_keyword("adrenal", ["renal"])
