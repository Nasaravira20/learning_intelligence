# Human review checklist

A strategy or source can be selected in production only when a person sets `review_status` to `reviewed` and sets `reviewed_by`. Agent-written notes stay `pending_human_review`.

Review one source, then the strategies that cite it.

## Source

- The title, authors, year, and publication match the Crossref record, publisher page, or ERIC record named in `metadata_verification`.
- The DOI or URL in `metadata_verification.identifier` is the same identifier that was opened.
- `access_type` and `license` match what that check showed. An absent Creative Commons license is not recorded as open access.
- `evidence_notes` are a short original summary. They contain no quotation, no copied paragraph, and no effect size.
- The repository does not contain the PDF, chapter, or book.
- Limitations say what the record does not claim.
- The source is on the starter list in roadmap section 15, or the product owner added it in writing.

## Strategy

- `strategy_id` is one of the P0 identifiers. The model did not invent it.
- `version` matches `research/registry.yaml`.
- Every source id points at a source file that passed the source checks.
- Suitable contexts, learner conditions, and avoid conditions are present.
- Limitations say when the strategy should not be used.
- Implementation steps do not claim a result the linked sources were not checked for.
- `reviewed_by` is the person who did this check, not the agent that drafted the note.

## After review

- Change `review_status` from `pending_human_review` to `reviewed`.
- Set `reviewed_by`.
- If the text changed, bump the strategy version and the registry manifest together.
- Run `docker compose run --rm api python -m pytest tests/test_pedagogy_registry.py`.
- Do not start pedagogy selection until the strategies that the selector may use are reviewed.
