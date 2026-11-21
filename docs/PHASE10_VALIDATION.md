# Phase 10 validation

This is the validation record for the local mock stack. It is not a claim that the product improves learning.

## Journey

`services/api/tests/test_journey.py` signs up a new learner and walks one session from diagnosis through a delayed recall, then deletes the account. The mock provider is the only model. The test fails if that journey takes 60 seconds or longer.

## Fixed benchmark

`services/api/tests/ai/benchmark_cases.json` has three cases. `tests/ai/test_benchmark_regression.py` loads that file and fails if a decision changes. Sample size 3. These cases are a regression fixture, not a measure of teaching effectiveness.

- A beginner who is missing prerequisites is assigned `small_step_instruction`. Production selection stays empty because the registry is still `pending_human_review`.
- A correct answer with weak reasoning is `further_assessment`, not mastery.
- A review scheduled at 18:30 UTC is due on the next local date in `Asia/Kolkata`, which is 23 November 2026 when the lesson was on 21 November 2026.

The broader diagnostic set remains `services/api/tests/ai/test_diagnostic_benchmark.py` (sample size 6). The broader selector set remains `services/api/tests/test_selector.py`.

## Cost and latency

No live Gemini call was made in this phase.

- Model: none
- Requests: 0
- Tokens: 0
- Estimated cost: USD 0

The journey bound is 60 seconds on the local mock stack. The full API suite that includes the journey, the budget guard, and this benchmark finished in 99.86 seconds (110 passed) before the journey timer line was added. The timer is checked by the journey test on its own.

`tests/test_ai.py::test_budget_guard_blocks_before_the_provider_is_called` is the ceiling check. A call that would pass the USD 20 total, or a category ceiling, is refused before the provider runs.

## Security checklist

These items are covered by the automated suite:

- Sign-in uses an HttpOnly cookie. Sign-out clears it.
- Another learner receives `404` `session_not_found` for a private session.
- The budget guard refuses a call before the provider runs.
- Connection strings, tokens, and API keys are redacted in logs. Account deletion logs the user id only.
- `DELETE /api/auth/account` removes the user, the private learner rows, and the cookie. Sign-in then returns `401`. The same email can be registered again, and the new account has an empty knowledge list. Shared topics are not deleted.
- Model output is accepted only after it matches a typed schema.

This is not a penetration test.

## Deployment

From the repository root:

```powershell
docker compose up --build
```

Open http://localhost:3000. `/health` returns `{"status":"ok","database":"ok"}` when PostgreSQL answers.

The clean-database check is the API test fixture. It drops the `ai_teacher_test` schema, applies every migration, downgrades to the base revision, and upgrades to head again before the suite runs. That check ran on this machine's Docker stack. It was not repeated on a second machine.

## Human evaluation

Not conducted. Sample size 0. No person has rated factuality or teaching quality for this release. `docs/TEACHING_REVIEW_CHECKLIST.md` and `docs/EVALUATION_REVIEW_CHECKLIST.md` are still waiting for a person.

## Pilot

Not conducted. Sample size 0. This document is not evidence that learners learned more with the product than without it.
