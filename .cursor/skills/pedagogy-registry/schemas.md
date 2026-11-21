# Registry schemas

## Strategy

```yaml
strategy_id: retrieval_practice
name: Retrieval Practice
version: 1.0
category: memory_and_retrieval
description: >
  Ask learners to retrieve previously learned information
  before showing the answer.
learning_objectives:
  - recall
  - retention
  - diagnosis
suitable_contexts:
  - previously_taught_concepts
  - revision
  - knowledge_assessment
learner_conditions:
  - initial_instruction_has_been_provided
avoid_or_modify_conditions:
  - learner_has_never_been_taught_the_concept
implementation_steps:
  - Ask a focused question.
  - Allow independent recall.
  - Evaluate the response.
  - Provide corrective feedback.
assessment_signals:
  - independent_recall
  - delayed_recall_accuracy
  - explanation_quality
limitations:
  - Incorrect retrieval requires corrective feedback.
  - Not a substitute for initial instruction.
sources:
  - weinstein_2018
review_status: reviewed
```

## Source

```yaml
source_id: weinstein_2018
title: Teaching the Science of Learning
authors:
  - Yana Weinstein
  - Christopher R. Madan
  - Megan A. Sumeracki
year: 2018
publication: Cognitive Research: Principles and Implications
doi: 10.1186/s41235-017-0087-y
url: https://link.springer.com/article/10.1186/s41235-017-0087-y
access_type: open_access
license: CC BY 4.0
retrieved_date: YYYY-MM-DD
relevant_sections:
  - Spacing
  - Retrieval Practice
evidence_notes: >
  Human-reviewed summary of the relevant findings.
review_status: reviewed
```

Verify DOI, URL, license, and access type against the live source before marking `reviewed`. The starter bibliography lives in roadmap section 15. It is not already ingested.

## Selector shapes

Input fields: `topic`, `learning_objective`, `learner_level`, `prior_knowledge`, `knowledge_gaps`, `misconceptions`, `recent_performance`, `session_stage`, `time_available_minutes`, `previous_strategy_outcomes`.

Output fields: `primary_strategy`, `supporting_strategies`, `sequence`, `success_signals`, `fallback_strategy`, `rationale`, `registry_version`.

## Initial policies

| Situation | Policy hypothesis |
|---|---|
| Missing prerequisites | Prerequisite remediation, small steps, concrete examples |
| Partial understanding | Self-explanation and targeted examples |
| Correct answer, weak reasoning | Reasoning prompts and transfer questions |
| Confuses similar concepts | Contrastive examples |
| Forgets earlier content | Retrieval practice and spaced revision |
| Repeated failure | Lower complexity and investigate the misconception |
| Strong performance | Fade scaffolding and increase variation |

Treat these as hypotheses to revise from learner outcomes.
