"""Clinical-group primary must not depend on config dict order (#254).

v2 (#338): ties are on equal evidence (frequency x IC) instead of equal matched/5.
"""

from app.pipeline.sources.annotations.hpo import ClinicalGroupClassifier

# Two sibling terms with the same information content (each in 1 of 2 diseases).
PARENTS = {"HP:C1": {"HP:ROOT"}, "HP:C2": {"HP:ROOT"}}


def _primary(groups: dict[str, list[str]], disease_terms: dict) -> str | None:
    classifier = ClinicalGroupClassifier(PARENTS, groups, "test")
    classifier.fit_information_content([{"HP:C1"}, {"HP:C2"}])
    return classifier.classify(disease_terms)["primary"]


def test_equal_scores_pick_same_group_regardless_of_dict_order():
    # The same term under both groups gives both the same evidence.
    tie = {"d1": {"HP:C1": 1.0}}
    forward = _primary({"cakut": ["HP:C1"], "cyst_cilio": ["HP:C1"]}, tie)
    reverse = _primary({"cyst_cilio": ["HP:C1"], "cakut": ["HP:C1"]}, tie)
    assert forward == reverse == "cakut"


def test_higher_score_still_wins_over_priority():
    groups = {"cakut": ["HP:C1"], "cyst_cilio": ["HP:C2"]}
    assert _primary(groups, {"d1": {"HP:C1": 0.5, "HP:C2": 1.0}}) == "cyst_cilio"


def test_unlisted_groups_tie_break_alphabetically_after_listed():
    tie = {"d1": {"HP:C1": 1.0}}
    assert _primary({"zeta": ["HP:C1"], "alpha": ["HP:C1"]}, tie) == "alpha"
    assert _primary({"zeta": ["HP:C1"], "cakut": ["HP:C1"]}, tie) == "cakut"
