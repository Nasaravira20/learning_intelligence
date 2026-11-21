"""Human-reviewed planner benchmark for backpropagation.

Agreed checks, sample size 6 scripted graph cases:
- A complete beginner starts at functions.basic. chain-rule.apply is before backprop.step.
- Partial prerequisites (functions and derivatives observed) start at chain-rule.apply, not backprop.step.
- A missing loss prerequisite keeps the start on loss-gradient.distinguish when the chain rule is already observed.
- A correct answer with weak reasoning does not mark the step satisfied.
- Partial chain-rule evidence stays in the sequence and is not satisfied.
- Low-confidence evidence does not satisfy a step.
- A prerequisite cycle is rejected.

These cases are not a claim of universal planning accuracy. No live model is called.
"""

from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.diagnostics.policy import ObjectiveNode
from app.planner.policy import plan_sequence

MET = ("solid", "correct", "sound", Decimal("0.850"))
PARTIAL = ("partial", "partial", "partial", Decimal("0.600"))
WEAK = ("partial", "correct", "weak", Decimal("0.600"))
NONE = ("none", "incorrect", "weak", Decimal("0.600"))
UNCERTAIN = ("uncertain", "unanswered", "uncertain", Decimal("0.300"))

NODES = [
    ObjectiveNode("functions.basic", "functions", "Use functions in a short original explanation.", 0, ()),
    ObjectiveNode("derivatives.basic", "derivatives", "Use derivatives in a short original explanation.", 1, ("functions.basic",)),
    ObjectiveNode("chain-rule.apply", "chain rule", "Use the chain rule in a short original explanation.", 2, ("derivatives.basic",)),
    ObjectiveNode("loss-gradient.distinguish", "loss", "Distinguish loss from the gradient.", 3, ("derivatives.basic",)),
    ObjectiveNode(
        "backprop.step",
        "backpropagation",
        "Apply one backpropagation step.",
        0,
        ("chain-rule.apply", "loss-gradient.distinguish"),
    ),
]


def _evidence(**overrides: tuple[str, str, str, Decimal] | None) -> dict[str, tuple[str, str, str, Decimal] | None]:
    base: dict[str, tuple[str, str, str, Decimal] | None] = {node.code: NONE for node in NODES}
    base.update(overrides)
    return base


def test_beginner_starts_at_the_first_prerequisite() -> None:
    steps = plan_sequence(NODES, _evidence())
    assert [step.code for step in steps] == [
        "functions.basic",
        "derivatives.basic",
        "chain-rule.apply",
        "loss-gradient.distinguish",
        "backprop.step",
    ]
    assert steps[0].status == "current"
    assert steps[0].code == "functions.basic"
    chain = next(step for step in steps if step.code == "chain-rule.apply")
    backprop = next(step for step in steps if step.code == "backprop.step")
    assert steps.index(chain) < steps.index(backprop)
    assert all(step.evidence == "none" for step in steps)
    assert all(step.statement in step.completion_criteria and step.code for step in steps)


def test_partial_prerequisites_start_at_the_chain_rule() -> None:
    steps = plan_sequence(
        NODES,
        _evidence(**{"functions.basic": MET, "derivatives.basic": MET}),
    )
    assert [step.code for step in steps if step.status == "satisfied"] == ["functions.basic", "derivatives.basic"]
    current = next(step for step in steps if step.status == "current")
    assert current.code == "chain-rule.apply"
    assert current.evidence == "none"
    assert next(step for step in steps if step.code == "backprop.step").status == "upcoming"


def test_missing_loss_prerequisite_changes_the_start() -> None:
    steps = plan_sequence(
        NODES,
        _evidence(
            **{
                "functions.basic": MET,
                "derivatives.basic": MET,
                "chain-rule.apply": MET,
            }
        ),
    )
    assert next(step for step in steps if step.status == "current").code == "loss-gradient.distinguish"
    assert next(step for step in steps if step.code == "backprop.step").status == "upcoming"


def test_weak_reasoning_and_partial_evidence_are_not_skipped() -> None:
    steps = plan_sequence(
        NODES,
        _evidence(
            **{
                "functions.basic": MET,
                "derivatives.basic": MET,
                "chain-rule.apply": WEAK,
                "loss-gradient.distinguish": PARTIAL,
            }
        ),
    )
    chain = next(step for step in steps if step.code == "chain-rule.apply")
    loss = next(step for step in steps if step.code == "loss-gradient.distinguish")
    assert chain.status == "current"
    assert chain.evidence == "none"
    assert loss.status == "upcoming"
    assert loss.evidence == "none"
    assert "chain rule" in chain.concept


def test_uncertain_evidence_does_not_satisfy_a_step() -> None:
    steps = plan_sequence(NODES, _evidence(**{"functions.basic": UNCERTAIN}))
    first = steps[0]
    assert first.code == "functions.basic"
    assert first.status == "current"
    assert first.evidence == "none"


def test_prerequisite_cycle_is_rejected() -> None:
    nodes = [
        ObjectiveNode("chain-rule.apply", "chain rule", "Apply the chain rule.", 0, ("backprop.step",)),
        ObjectiveNode("backprop.step", "backpropagation", "Apply one step.", 1, ("chain-rule.apply",)),
    ]
    with pytest.raises(AppError) as caught:
        plan_sequence(nodes, {"chain-rule.apply": NONE, "backprop.step": NONE})
    assert caught.value.code == "dependency_cycle"
