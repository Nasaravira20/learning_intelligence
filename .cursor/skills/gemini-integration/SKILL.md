---
name: gemini-integration
description: >-
  Adds the Gemini provider, live model verification, structured output, usage
  logging, and the USD $20 budget guard for the AI Teacher. Use when working on
  Gemini, model routing, check_gemini_models.py, GEMINI_API_KEY, token limits,
  mock providers, or API cost controls.
---

# Gemini integration

This skill applies from Phase 1 onward. Phase 0 must not call Gemini.

## Layout

```text
services/api/app/ai/
├── providers/
│   ├── base.py
│   ├── gemini.py
│   └── mock.py
├── model_registry.py
├── model_capabilities.py
├── prompts/
├── schemas/
├── usage_tracker.py
└── budget_guard.py
scripts/check_gemini_models.py
```

Routes and workflow code call the registry, not the Gemini SDK.

## Verify the key before choosing models

`scripts/check_gemini_models.py` must:

1. Read `GEMINI_API_KEY` from the environment.
2. List models the key can access. Do not invent IDs in the report.
3. Run a tiny real generation request for each configured candidate.
4. Run a schema-constrained JSON test for diagnostic, teaching, and evaluation candidates.
5. Record latency, returned model ID, and status.
6. Classify errors: invalid key, permission, model not found, unsupported operation, quota, rate limit, timeout, network, unknown.
7. Exit non-zero if no configured model passes the minimum test.
8. Never print the key or authorization headers.

A model in the list is not approved. HTTP 200 is not approval. Critical layers also need the small teaching and evaluation benchmark under `tests/ai/`.

Check the current official Gemini docs for the recommended API before coding the client. Prefer the Interactions API for new agentic calls when the selected model supports the required features. If it does not, document the supported API you used.

## Budget

Internal allocation, not provider billing controls: $1 smoke tests, $3 development, $5 teaching and diagnostic experiments, $5 evaluation benchmarks, $4 demo buffer, $2 reserve.

- One client enforces per-request token limits, a cap on model calls per learner action, timeouts, and retry limits.
- Daily and total counters live in `ai_usage_records`.
- Block at the configured ceiling.
- Label costs as estimates unless they are reconciled with provider billing.

## Tests that must exist

Success, malformed output, timeout, quota, invalid key, and unavailable model. All of these use the mock provider.
