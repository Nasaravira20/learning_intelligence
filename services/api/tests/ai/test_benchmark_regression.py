"""Fail when a fixed benchmark case changes its decision."""

import json
from datetime import datetime
from pathlib import Path

from app.diagnostics.schemas import ItemJudgment
from app.evaluation.policy import decide
from app.pedagogy.registry import load_registry
from app.pedagogy.selector import SelectorInput, select
from app.retention.policy import INTERVALS, local_date, next_due_on, review_timing

CASES = json.loads(Path(__file__).with_name("benchmark_cases.json").read_text(encoding="utf-8"))


def test_fixed_benchmark_cases_keep_their_decisions() -> None:
    assert CASES["sample_size"] == 3
    registry = load_registry()
    for case in CASES["selector"]:
        decision = select(SelectorInput.model_validate(case["input"]), registry, production=False)
        assert decision.situation == case["expect_situation"]
        assert decision.primary_strategy == case["expect_primary"]
        assert set(case["expect_supporting_includes"]) <= set(decision.supporting_strategies)
        assert decision.production_primary_strategy == case["expect_production_primary"]
    for case in CASES["evaluation"]:
        decision_name, _credit = decide(ItemJudgment.model_validate(case["judgment"]))
        assert decision_name == case["expect_decision"]
        assert decision_name != "mastered"
    for case in CASES["retention"]:
        learned = datetime.fromisoformat(case["learned_at"])
        due_on, _index = next_due_on(local_date(learned, case["zone"]), 0, INTERVALS)
        assert due_on.isoformat() == case["expect_due_on"]
        before = datetime.fromisoformat(case["before"])
        after = datetime.fromisoformat(case["after"])
        assert review_timing(due_on, before, case["zone"]) == case["expect_before"]
        assert review_timing(due_on, after, case["zone"]) == case["expect_after"]
