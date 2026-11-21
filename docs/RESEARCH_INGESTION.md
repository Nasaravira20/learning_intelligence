# Research ingestion

Phase 5 stores bibliographic metadata and short original notes. It does not store papers or books, and it does not choose a teaching strategy. Selection is Phase 6, and it cannot use this registry in production until a person marks the entries reviewed.

## Order

1. Start from the starter list in `AI_TEACHER_MVP_ROADMAP.md` section 15. Do not add a source that is not on that list unless the product owner adds it.
2. Check the bibliographic record. Use Crossref for a DOI. Use the publisher page or ERIC when the starter list has no DOI.
3. Record the access type and the license that the check actually showed. If no reader license was listed, write that. Do not relabel a publisher article as open access.
4. Write a short original summary of why the source is linked. Do not copy sentences, tables, or effect sizes from the source.
5. Leave `review_status` as `pending_human_review`.
6. A person reviews the note against the checklist in `docs/HUMAN_REVIEW_CHECKLIST.md`.
7. Only that person sets `review_status` to `reviewed` and sets `reviewed_by`.
8. Bump the strategy `version` and the matching line in `research/registry.yaml` when a reviewed strategy changes.

## What was checked on 2026-11-21

Crossref confirmed the DOI, title, authors, year, and container for Weinstein 2018, Dunlosky 2013, Carpenter 2022, Wood 1976, Sweller 1988, Mayer 2022, Black and Wiliam 1998, and National Academies 2018. Weinstein 2018 is the only one whose Crossref record listed CC BY 4.0.

The AFT page for Rosenshine returned HTTP 200 and the title Principles of Instruction. ERIC ED053419 names Benjamin S. Bloom, Learning for Mastery, Evaluation Comment, 1968.

The Cambridge Handbook URL in the roadmap returned HTTP 404, and the roadmap gave no DOI or year for that book. It was not ingested. The National Academies catalogue page returned HTTP 403, so the record uses the DOI and does not claim the book was downloaded.

## Validate

From the repository root, after the API image includes this catalogue:

```powershell
docker compose run --rm api python -m pytest tests/test_pedagogy_registry.py
```

`GET /api/pedagogy/registry` lists the catalogue. `production_selectable_strategy_ids` stays empty while the summaries are pending review.
