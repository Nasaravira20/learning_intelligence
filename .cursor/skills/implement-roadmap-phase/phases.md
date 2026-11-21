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

Phase 2 is approved. The product owner approved starting Phase 3 on 2026-11-21. Phase 3 is approved. The product owner approved starting Phase 4 on 2026-11-21. Phase 4 is implemented. Acceptance tests passed on 2026-11-21. Do not start Phase 5 until the product owner approves the Phase 4 report.

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

# Phase 2 completion report

```text
PHASE COMPLETION REPORT

Phase: 2
Name: Learner intelligence

1. Implementation Summary
- Each signed-in learner has a private record: profile, one preference row, goals, topic knowledge, misconceptions, assessment notes, and learning activities.
- Observed knowledge requires a learner response or an assessment. Inferred knowledge, including every self-report from the dashboard, stays unconfirmed. A correction inserts a new row and keeps the original evidence kind.
- Deterministic code owns the writes. Learner routes do not call Gemini and do not create AI usage rows. Another learner's records return 404.

2. Deliverables
- Learner data model
- Alembic migration 0004
- Authenticated learner APIs
- Session history
- Profile update
- Basic learner dashboard on /learn
- API and web tests

3. Files Created
- services/api/app/learner/__init__.py
- services/api/app/learner/evidence.py
- services/api/app/models/learner_records.py
- services/api/app/schemas/learner.py
- services/api/app/services/learner_intelligence.py
- services/api/app/api/learner.py
- services/api/alembic/versions/0004_learner_intelligence.py
- services/api/tests/test_learner_intelligence.py
- apps/web/src/lib/evidence.ts
- apps/web/src/lib/evidence.test.ts
- apps/web/src/components/LearnerDashboard.tsx

4. Files Modified
- services/api/app/models/entities.py
- services/api/app/models/__init__.py
- services/api/alembic/env.py
- services/api/app/main.py
- services/api/app/api/sessions.py
- services/api/tests/conftest.py
- services/api/tests/test_api.py
- apps/web/src/lib/api.ts
- apps/web/src/components/TeacherShell.tsx
- apps/web/tsconfig.tsbuildinfo
- README.md
- AI_TEACHER_MVP_ROADMAP.md Phase 2 acceptance boxes

5. Tests Executed
- docker compose run --rm api python -m pytest
- npm test in apps/web
- curl.exe http://localhost:8000/health
- curl.exe http://localhost:3000/health
- Browser: signed in at http://localhost:3000/learn, saved profile, preferences, a goal, an inferred knowledge note, and an assessment, started a Chain rule session, opened its history, reloaded, restarted the API container, and reloaded again.

6. Test Results
- API: 42 passed, 0 failed, 0 skipped, in 21.32s
- Web: 14 passed, 0 failed, 0 skipped, 5 files
- Both health endpoints returned {"status":"ok","database":"ok"}
- After reload and after docker compose restart api, the same name, background, unhurried pace, goal, inferred knowledge at confidence 0.40, assessment note, and Chain rule session were still on the page. Session history showed 1 knowledge record labeled inferred and 1 assessment note.

7. Acceptance Criteria
- Passed: learner profiles persist; knowledge records are topic-specific; assessment history is retained; observed and inferred knowledge are distinguishable; confidence is persisted; learner corrections update the profile and keep the evidence kind; one learner cannot access another learner's records; relevant history can be retrieved for a session; restarting the application does not lose data
- Failed: none
- Not implemented: none

8. Known Limitations
- No diagnosis, teaching, evaluation, adaptation, or retention. Session status stays topic selected.
- The dashboard cannot mark a self-report as observed. Assessment outcomes are stored labels, not mastery decisions.
- Public learner list endpoints still return display names from Phase 0. Private fields are not on that payload.
- The correction dropdown does not preselect the current record after a reload. The record remains in the list.
- Phase 2 made no Gemini calls. Cost for this phase is USD 0. Earlier verification spend stays on the Phase 1 usage rows.

9. API Usage
- Model: none
- Requests: 0
- Tokens: 0
- Estimated cost: USD 0

10. Demo Instructions
- From the repository root: docker compose up --build
- Open http://localhost:3000, create an account, and open /learn
- Save a profile, a goal, and a knowledge note. The note is labeled "Inferred, not confirmed".
- Start a session and use History for that topic. Reload the page. The record is read back from PostgreSQL.

11. Remaining Issues
- None that block the Phase 2 gate. The product owner approved this report by starting Phase 3.

PRODUCT OWNER DECISION:
[x] Approve
[ ] Request changes
```

# Phase 3 completion report

```text
PHASE COMPLETION REPORT

Phase: 3
Name: Diagnostic Engine

1. Implementation Summary
- A signed-in learner can define learning objectives and prerequisites, then move a topic session from TOPIC_SELECTED to DIAGNOSING.
- Question wording and judgments come from the model provider and are parsed with typed schemas before any diagnosis row or learner record is written. Invalid output rolls back and does not change state.
- Deterministic policy classifies the starting point, keeps uncertain conclusions uncertain, and stores a misconception only when the evidence quote is copied from the learner's own answer or reasoning.
- The session stays DIAGNOSING after the report. No learning plan is created.
- Routine tests and the local UI use the mock provider. No live Gemini request was made.

2. Deliverables
- Diagnostic service and routes under /api
- Learning objective schema and prerequisite links
- Question and judgment schemas
- Diagnostic prompts
- Deterministic response evaluator
- Misconception hypotheses stored on the existing misconception records
- Diagnostic report
- Human-reviewed backpropagation benchmark

3. Files Created
- services/api/app/models/diagnostics.py
- services/api/app/diagnostics/__init__.py
- services/api/app/diagnostics/schemas.py
- services/api/app/diagnostics/policy.py
- services/api/app/diagnostics/prompts.py
- services/api/app/diagnostics/service.py
- services/api/app/schemas/diagnostics.py
- services/api/app/api/diagnostics.py
- services/api/app/ai/providers/diagnostic_mock.py
- services/api/alembic/versions/0005_diagnostics.py
- services/api/tests/test_diagnostics.py
- services/api/tests/ai/test_diagnostic_benchmark.py
- apps/web/src/components/DiagnosticPanel.tsx

4. Files Modified
- services/api/app/models/entities.py
- services/api/app/models/__init__.py
- services/api/app/main.py
- services/api/app/api/deps.py
- services/api/app/core/config.py
- services/api/app/services/sessions.py
- services/api/alembic/env.py
- services/api/tests/conftest.py
- services/api/tests/test_api.py
- apps/web/src/lib/api.ts
- apps/web/src/components/TeacherShell.tsx
- docker-compose.yml
- .env.example
- README.md
- AI_TEACHER_MVP_ROADMAP.md
- .cursor/skills/implement-roadmap-phase/phases.md

5. Tests Executed
- Exact commands:
- docker compose build api
- docker compose run --rm api python -m pytest
- npm test
  (working directory: apps/web)
- docker compose up -d --build api web
- curl.exe -s http://localhost:8000/health
- curl.exe -s http://localhost:3000/health
- Browser at http://localhost:3000/learn: created topic Backpropagation, started a session, started diagnosis, saved objective chain-rule.apply, answered and gave separate reasoning, submitted, reloaded.

6. Test Results
- API: 53 passed, 0 failed, 0 skipped, in 36.87s
- Web: 16 passed, 0 failed, 0 skipped, 5 files
- Both health endpoints returned {"status":"ok","database":"ok"}
- API logs: Running upgrade 0004_learner_intelligence -> 0005_diagnostics
- Browser: status became Diagnosing; the question was labeled chain-rule.apply, short answer. After submit the report read "Beginner. The first unmet objective is chain-rule.apply." with "answer partial, reasoning weak · not confirmed · needs review" and confidence 0.60. After reload the same report, profile background, product-rule knowledge, misconception, and practice activity were still on the page. The local mock does not claim the answer was mastered.

7. Acceptance Criteria
- Passed: Diagnostic questions align with learning objectives. Beginner learners can be distinguished from partially knowledgeable learners. Answers and reasoning are evaluated separately. Partial understanding is recognized. Misconception hypotheses include supporting evidence. Uncertain conclusions remain uncertain. Invalid model output is rejected. Diagnostic results persist. Human-reviewed benchmark cases pass agreed thresholds.
- Failed: none
- Not implemented: none

8. Known Limitations
- No lesson plan, teaching, evaluation mastery, adaptation, or retention. The session stays DIAGNOSING.
- The development mock used by the UI does not score real understanding. The benchmark uses scripted mock JSON. AI_PROVIDER=gemini is implemented and was not called.
- Topics and objectives are shared among signed-in users. Attempts, responses, and learner records stay private to the signed-in learner.
- A diagnosis writes observed knowledge only when understanding is solid, the answer is correct, the reasoning is sound, and confidence is not low. Partial understanding stays inferred and unconfirmed.
- The human-reviewed sample is 6 scripted backpropagation cases. It is not a claim of universal diagnostic accuracy.
- This phase made no live Gemini calls. Cost is USD 0.

9. API Usage
- Model: none
- Requests: 0
- Tokens: 0
- Estimated cost: USD 0

10. Demo Instructions
- From the repository root, with AI_PROVIDER=mock: docker compose up --build
- Open http://localhost:3000, sign in, and open /learn
- Create a topic, start a session, and choose Start diagnosis
- Save a learning objective, answer the question, and add reasoning separately
- Submit. The report names the starting point and keeps answer and reasoning verdicts apart. Reload the page. The report is still there.
- Do not set AI_PROVIDER=gemini for this demo. That path is not part of the verified Phase 3 run.

11. Remaining Issues
- None that block the Phase 3 gate. The product owner approved this report by starting Phase 4.

PRODUCT OWNER DECISION:
[x] Approve
[ ] Request changes
```

# Phase 4 completion report

```text
PHASE COMPLETION REPORT

Phase: 4
Name: Learning Planner

1. Implementation Summary
- After a completed diagnosis, deterministic code builds a prerequisite-ordered learning plan. The model does not choose the sequence, strategy IDs, citations, or effect sizes.
- A step is satisfied only by observed diagnostic evidence: understanding solid, answer correct, reasoning sound, and confidence above 0.400. Partial, weak, uncertain, inferred, or low-confidence evidence leaves the concept in the plan.
- The current step is the first unsatisfied objective in prerequisite order. A missing prerequisite moves the starting point to that objective. A dependency cycle is rejected before it is stored.
- Creating the plan moves the session from DIAGNOSING to PLAN_READY. A follow-up diagnosis can supersede the active plan with the next revision. The same evidence returns plan_unchanged and does not write a new revision.
- Teaching does not start. Routine tests and the local UI use the mock provider. No live Gemini request was made.

2. Deliverables
- Topic decomposition stored as topic concepts
- Prerequisite graph and cycle detection
- Learning plan service
- Learning activity note for the plan revision
- Plan progress on learning plan steps
- Progress UI on /learn

3. Files Created
- services/api/app/planner/__init__.py
- services/api/app/planner/graph.py
- services/api/app/planner/policy.py
- services/api/app/planner/service.py
- services/api/app/models/planning.py
- services/api/app/schemas/planning.py
- services/api/app/api/planning.py
- services/api/alembic/versions/0006_learning_plans.py
- services/api/tests/test_planner.py
- services/api/tests/ai/test_planner_benchmark.py
- apps/web/src/components/PlanPanel.tsx

4. Files Modified
- services/api/app/models/entities.py
- services/api/app/models/diagnostics.py
- services/api/app/models/__init__.py
- services/api/app/diagnostics/service.py
- services/api/app/schemas/diagnostics.py
- services/api/app/api/diagnostics.py
- services/api/app/services/sessions.py
- services/api/app/main.py
- services/api/alembic/env.py
- services/api/tests/conftest.py
- services/api/tests/test_api.py
- apps/web/src/lib/api.ts
- apps/web/src/components/DiagnosticPanel.tsx
- apps/web/src/components/TeacherShell.tsx
- README.md
- AI_TEACHER_MVP_ROADMAP.md
- .cursor/skills/implement-roadmap-phase/phases.md

5. Tests Executed
- Exact commands:
- docker compose build api
- docker compose run --rm api python -m pytest
- npm test
  (working directory: apps/web)
- npx tsc --noEmit
  (working directory: apps/web)
- docker compose up -d --build api web
- curl.exe -s http://localhost:8000/health
- curl.exe -s http://localhost:3000/health
- Browser at http://localhost:3000/learn as the existing signed-in learner: created topic Plan check, started a session, saved derivatives.basic, backprop.step (prerequisite derivatives.basic), and chain-rule.apply (prerequisite derivatives.basic), then added chain-rule.apply as a prerequisite of backprop.step. Started diagnosis, answered all three questions with separate reasoning, submitted, built the plan, reloaded, and chose Revise plan.

6. Test Results
- API: 65 passed, 0 failed, 0 skipped, in 47.08s. An earlier run of the same suite failed 1 and passed 64 before an unfinished first diagnosis was distinguished from an open follow-up. The passing run is the one after that fix and after docker compose build api.
- Web: 16 passed, 0 failed, 0 skipped, 5 files. npx tsc --noEmit exited 0.
- Both health endpoints returned {"status":"ok","database":"ok"}
- API logs: Running upgrade 0005_diagnostics -> 0006_learning_plans
- Browser: the plan was Revision 1, status Plan ready, order 1 Start here derivatives.basic, 2 Later chain-rule.apply, 3 Later backprop.step. Each step showed its objective statement and completion criteria. None were marked already demonstrated. After reload the same revision, order, and status were still on the page, and the activity list included "Learning plan revision 1 starts at derivatives.basic." Revise plan with no new evidence showed "The plan already matches the latest diagnostic evidence." with code plan_unchanged, and the revision stayed 1.

7. Acceptance Criteria
- Passed: Every learning step has an objective. Prerequisites are respected. Missing prerequisite knowledge changes the starting point. Concepts are not skipped without supporting evidence. Invalid dependency cycles are detected. Plan progress is persisted. Plans can be revised after new diagnostic evidence.
- Failed: none
- Not implemented: none

8. Known Limitations
- No pedagogy selection, teaching, evaluation mastery, adaptation, or retention. The session stops at PLAN_READY.
- The development mock used by the UI scores non-blank answers as partial with weak reasoning, so the local page does not mark a step observed. The revision test uses scripted solid, correct, sound, high-confidence judgments. AI_PROVIDER=gemini was not called.
- Topics, concepts, and objectives are shared among signed-in users. Plans, diagnostic attempts, and learner records stay private to the signed-in learner.
- The human-reviewed planner sample is 6 scripted backpropagation graphs. It is not a claim of universal planning accuracy.
- This phase made no live Gemini calls. Cost is USD 0.
- apps/web/tsconfig.tsbuildinfo changed when the typecheck ran. It is a local compiler cache and is not part of this phase.

9. API Usage
- Model: none
- Requests: 0
- Tokens: 0
- Estimated cost: USD 0

10. Demo Instructions
- From the repository root, with AI_PROVIDER=mock: docker compose up --build
- Open http://localhost:3000, sign in, and open /learn
- Create a topic, start a session, and save learning objectives with prerequisite codes that already exist on that topic
- Start diagnosis, answer each question, and add reasoning separately
- Submit, then choose Build learning plan. The first step without observed evidence is marked Start here. Reload the page. The same revision is still there.
- Choose Revise plan before any new diagnosis. The page reports plan_unchanged.
- Do not set AI_PROVIDER=gemini for this demo. That path is not part of the verified Phase 4 run.

11. Remaining Issues
- None that block the Phase 4 gate. Do not start Phase 5 until this report is approved.

PRODUCT OWNER DECISION:
[ ] Approve
[ ] Request changes
```
