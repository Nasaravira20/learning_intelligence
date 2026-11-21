---
name: learning-workflow
description: >-
  Implements the AI Teacher learning loop, session state machine, diagnosis,
  planning, teaching, evaluation, adaptation, and retention. Use when building
  learner knowledge, diagnostics, lesson plans, assessments, mastery,
  misconceptions, spaced review, or the backpropagation benchmark.
---

# Learning workflow

Use the phase gates in the `implement-roadmap-phase` skill. This skill defines behavior, not permission to skip ahead.

## Evidence

- `observed`: the learner demonstrated it in a response.
- `inferred`: estimated from other evidence. Never store an inference as a confirmed fact.
- Persist confidence and provenance on knowledge, misconception, and mastery records.
- The learner can view and correct profile information.

## Decisions after evaluation

```text
strong evidence of understanding → MASTERED
partial evidence → REMEDIATION
correct answer with weak reasoning → further assessment, not mastery
ambiguous or thin evidence → NEEDS_REVIEW
```

Remediation must be able to pick a different registered strategy, then reassess. Advance only when the mastery criteria for that objective are met.

## Teaching shape

Activities are structured objects, not a single chat paragraph. A typical sequence, when the selector allows it:

objective → prerequisite explanation → concrete example → worked example → guided practice → self-explanation → independent practice → evaluation.

Checks for understanding happen during instruction. The first hint does not contain the final answer.

## Retention

Scheduling is code, not a model call. After a successful learning session, create a due review. Completing it updates mastery. A miss or a failed recall schedules a sensible next review and can return the learner to remediation. Test timezone boundaries.

## Fixed benchmark

Use backpropagation as the first end-to-end scenario:

- The learner knows basic functions and basic derivatives.
- The learner is weak on the chain rule and confuses loss with gradient.
- The learner has not learned backpropagation.
- The plan teaches the chain rule before backpropagation.
- Variants that must also be represented: complete beginner, partial prerequisites, correct answer with weak reasoning, persistent misconception, success followed by forgetting, and transfer to an unfamiliar problem.

Diagnosis and teaching prompts for this scenario belong in `tests/ai/` once those phases start. Do not treat a small pilot as proof of universal effectiveness. Report sample size and uncertainty.
