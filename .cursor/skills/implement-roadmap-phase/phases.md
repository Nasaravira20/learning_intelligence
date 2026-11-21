# Phase index

Do not start a phase until the previous phase is approved.

| Phase | Name | Gate |
|---|---|---|
| 0 | Project foundation | No Gemini, agents, or pedagogy |
| 1 | Gemini integration and model verification | Verified key, schema checks, and budget guard pass |
| 2 | Learner intelligence | Learner data model approved |
| 3 | Diagnostic engine | Diagnostic output reliable enough for the pilot |
| 4 | Learning planner | Planner approved |
| 5 | Research library and pedagogy registry | Registry validation passes |
| 6 | Pedagogy selection | Benchmark reviewed before it drives live sessions |
| 7 | Teaching engine | Teaching quality approved |
| 8 | Evaluation and adaptation | Evaluation reliability approved |
| 9 | Retention and learning progress | Retention loop approved |
| 10 | End-to-end validation and pilot | Full journey, budget, auth, and pilot report |

Phase 0 acceptance: frontend and backend start, they communicate, migrations work from a clean database, health reports real status, learner records and sessions can be created, retrieved, and resumed, tests pass, no secrets are committed, and the README matches the implementation.

Phase 0 is complete. Acceptance tests passed on 2026-11-21. The product owner approved moving to Phase 1 after that result. Phase 1 is approved.

Later acceptance criteria stay in `AI_TEACHER_MVP_ROADMAP.md` sections 12 and 18. Do not mark a criterion done unless it was executed.

# Completion report

Use this at the end of every phase:

```text
PHASE COMPLETION REPORT

Phase:
Name:

1. Implementation Summary
-

2. Deliverables
-

3. Files Created
-

4. Files Modified
-

5. Tests Executed
- Exact commands:

6. Test Results
- Passed:
- Failed:
- Skipped:

7. Acceptance Criteria
- Passed:
- Failed:
- Not implemented:

8. Known Limitations
-

9. API Usage
- Model:
- Requests:
- Tokens:
- Estimated cost:

10. Demo Instructions
-

11. Remaining Issues
-

PRODUCT OWNER DECISION:
[ ] Approve
[ ] Request changes
```

# Phase 0 completion report

```text
PHASE COMPLETION REPORT

Phase: 0
Name: Project foundation

1. Implementation Summary
- Next.js, FastAPI, and PostgreSQL run together through Docker Compose.
- The browser talks to Next.js. Next.js proxies /health and /api to FastAPI.
- Learners, topics, and learning sessions persist. A session stays in TOPIC_SELECTED and can be resumed.
- Accounts, the MNEMO landing page, sign-in, and sign-up were added on top of that foundation. Sign-in uses an HttpOnly cookie. A signed-in learner only sees their own sessions.

2. Deliverables
- Running frontend at http://localhost:3000
- Running FastAPI backend
- PostgreSQL 16
- Migrations 0001_initial and 0002_auth
- Docker Compose
- .env.example
- Health endpoint
- Structured JSON logs with secret redaction
- README
- Automated API and web tests

3. Files Created
- apps/web application, proxy, landing page, sign-in, sign-up, and Teacher Mode at /learn
- services/api FastAPI app, Alembic migrations, auth, learners, topics, and sessions
- docker-compose.yml, README.md, .env.example, .gitignore

4. Files Modified
- AI_TEACHER_MVP_ROADMAP.md Phase 0 acceptance boxes, marked passed on 2026-11-21

5. Tests Executed
- docker compose ps
- docker compose run --rm api python -m pytest
- npm test, run in apps/web
- curl.exe http://localhost:3000/health
- git check-ignore -v .env .env.example
- git ls-files filtered for a tracked .env

6. Test Results
- Passed: API 21, web 13, health 200 {"status":"ok","database":"ok"}, frontend web healthy, backend api healthy, database db healthy
- Failed: 0
- Skipped: 0
- Warning: 1 Starlette deprecation, TestClient wants httpx2. It does not fail the suite.

7. Acceptance Criteria
- Passed: frontend starts, backend starts, frontend reaches the backend, database connection succeeds, migrations apply from a clean database inside the API test fixture, health reports real database status, learners can be created and retrieved, sessions can be created, retrieved, and resumed, automated tests pass, .env is gitignored and untracked, README matches the running stack
- Failed: none
- Not implemented: none for Phase 0

8. Known Limitations
- Session status remains TOPIC_SELECTED. Diagnosis, teaching, evaluation, adaptation, and retention are later phases.
- Topics are shared. Sessions are private to the signed-in learner when a session cookie is present.
- Nothing has been committed to git yet.
- The API test client still emits the Starlette httpx2 deprecation warning.

9. API Usage
- Model: none
- Requests: 0
- Tokens: 0
- Estimated cost: USD 0

10. Demo Instructions
- From the repository root, run: docker compose up --build
- Open http://localhost:3000
- Create an account, then start and resume a session at /learn

11. Remaining Issues
- None that block Phase 0.

PRODUCT OWNER DECISION:
[x] Approve
[ ] Request changes
```

# Phase 1 completion report

```text
PHASE COMPLETION REPORT

Phase: 1
Name: Gemini integration and model verification

1. Implementation Summary
- Gemini is called only from the backend provider. The web app has no model client.
- The client uses the Interactions API, with a JSON schema in response_format, a per-call timeout, and automatic continuation turned off.
- Routine tests use the mock provider. A model stays unusable until a live generation check and the structured check for that task are both recorded as passed.
- Usage and estimated cost are stored in PostgreSQL. The budget guard blocks the next call at the USD $20 ceiling and at the category ceilings.

2. Deliverables
- Gemini provider
- Provider interface
- Mock provider
- Model verification script
- Model capability selection
- docs/GEMINI_MODEL_STRATEGY.md
- Usage tracker
- Budget guard
- Mock integration tests

3. Files Created
- services/api/app/ai/
- services/api/scripts/check_gemini_models.py
- services/api/alembic/versions/0003_ai_usage.py
- services/api/tests/test_ai.py
- docs/GEMINI_MODEL_STRATEGY.md

4. Files Modified
- services/api/pyproject.toml
- services/api/Dockerfile
- services/api/app/core/config.py
- services/api/app/models/entities.py
- services/api/app/models/__init__.py
- services/api/tests/conftest.py
- services/api/tests/test_api.py
- docker-compose.yml
- .env.example
- README.md
- AI_TEACHER_MVP_ROADMAP.md Phase 1 acceptance boxes

5. Tests Executed
- docker compose run --rm api python -m pytest
- docker compose run --rm api python scripts/check_gemini_models.py

6. Test Results
- Passed: 35
- Failed: 0
- Skipped: 0
- Live verifier exit code: 0
- Estimated smoke spend recorded: USD 0.006348

7. Acceptance Criteria
- Passed: key is read only from backend configuration, the live key listed its models, candidate models received real generation requests, structured output is validated, access failures are classified, timeout and network failures are handled, keys are kept out of logs, usage is recorded, the budget guard blocks at the ceiling, the mock provider covers routine tests, only models that passed the live checks are usable
- Failed: none
- Not implemented: none

8. Known Limitations
- Cost figures are internal estimates (USD 0.50 per million input tokens and USD 3.00 per million output tokens), not a provider invoice.
- The verifier sends generation requests to at most three text models that respond, after skipping models the key cannot access. Image, embedding, and research models are not in that default walk.
- Teaching workflows are not started.

9. API Usage
- Model: live key, Interactions API. Passed every checked task: gemma-4-31b-it. Also usable for some tasks: gemma-4-26b-a4b-it and gemini-3.1-flash-lite.
- Requests: 27 recorded
- Tokens: stored on the usage rows
- Estimated cost: USD 0.006348

10. Demo Instructions
- GEMINI_API_KEY is already in the repository .env. Do not commit that file.
- docker compose run --rm -v "${PWD}/docs:/docs" -e MODEL_STRATEGY_PATH=/docs/GEMINI_MODEL_STRATEGY.md api python scripts/check_gemini_models.py
- The script overwrites docs/GEMINI_MODEL_STRATEGY.md. Exit 0 means at least one model passed generation and the three structured checks.

11. Remaining Issues
- gemini-2.5-flash, gemini-2.5-pro, and gemini-2.5-flash-lite are listed but return model_not_found for this key.
- gemma-4-26b-a4b-it did not pass the diagnostic check. gemini-3.1-flash-lite did not pass the teaching check.
- Models further down the live list, including gemini-3.8-flash, were not sent a generation request because the verifier stops after three models that respond.

PRODUCT OWNER DECISION:
[x] Approve
[ ] Request changes
```
