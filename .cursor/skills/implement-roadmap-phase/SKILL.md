---
name: implement-roadmap-phase
description: >-
  Implements one approved phase of the AI Teacher MVP roadmap. Use when the
  user mentions a phase, milestone, the roadmap, Teacher Mode, Phase 0 through
  Phase 10, a completion report, or asks to start, continue, or review
  implementation of AI_TEACHER_MVP_ROADMAP.md.
---

# Implement one roadmap phase

Read `AI_TEACHER_MVP_ROADMAP.md` before proposing or coding. Implement one phase, then stop.

Phase index and the completion report are in [phases.md](phases.md).

## Before any code

1. Inspect the repository. Name what already exists.
2. Confirm which phase is explicitly approved. If none is approved, propose Phase 0 and stop. Do not write implementation code.
3. Publish a short proposal:
   - Existing architecture
   - Proposed architecture
   - Files to create or modify
   - Dependencies
   - Database changes
   - Acceptance tests
4. Wait for the product owner to approve that proposal.

## While implementing

- Build only the approved phase. Leave the app runnable.
- Use deterministic code for persistence, transitions, scheduling, authorization, and budget checks.
- Use the mock model provider for routine tests.
- Update docs and migrations in the same phase as the code they describe.
- Do not add voice, scraping, personas, institutional analytics, or extra agent services.

## Before declaring the phase done

1. Run the phase acceptance tests, not only the files you just edited.
2. Record the exact commands and pass, fail, and skip counts.
3. Fill in the completion report in [phases.md](phases.md).
4. Stop. Ask for approval or changes. Do not open the next phase.
