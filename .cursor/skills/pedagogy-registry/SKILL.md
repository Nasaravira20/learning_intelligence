---
name: pedagogy-registry
description: >-
  Creates and validates the AI Teacher research library and pedagogy strategy
  registry, and applies deterministic strategy selection. Use when adding
  teaching strategies, research sources, YAML registry entries, pedagogy
  policies, or when the user mentions retrieval practice, scaffolding, mastery
  learning, or research-backed teaching.
---

# Pedagogy registry

Use this from Phase 5. The selector is Phase 6. Do not let an unverified registry drive teaching.

Schemas and P0 policy table: [schemas.md](schemas.md).

## Rules

- Store strategies in `research/strategies/` and sources in `research/sources/` as YAML.
- The model must not create strategy IDs, citations, DOIs, quotations, or effect sizes.
- Prefer open-access reviews and meta-analyses, national academies, university pages, and open educational resources. Label practitioner material as practitioner guidance.
- Ingestion order: discover, verify bibliographic metadata, check license, extract relevant sections, write an original summary, human review, record limitations, link to a strategy.
- Do not scrape or store full copyrighted books or paywalled papers.
- Validation fails if an ID is missing or duplicated, a version or limitation is missing, a source reference does not resolve, metadata is incomplete, or `review_status` is not `reviewed` while the entry is selectable in production.
- Selection input and output must match the typed examples in [schemas.md](schemas.md). Those examples are illustrative, not a fixed plan for every learner.
- Start with deterministic policies. Record why the strategy was eligible. Reject strategies that miss learner conditions or hit avoid conditions.
- Same selector inputs plus the same policy version must return the same strategy IDs.

## P0 catalogue

`retrieval_practice`, `spaced_practice`, `worked_examples`, `guided_practice`, `scaffolding`, `small_step_instruction`, `checks_for_understanding`, `formative_feedback`, `self_explanation`, `concrete_examples`, `elaborative_interrogation`, `mastery_learning`.

Leave P1 strategies out of the selectable registry until the core loop is approved.
