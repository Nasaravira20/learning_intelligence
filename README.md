# AI Teacher

Phase 0 is a local learning-session shell. The browser talks to Next.js, Next.js proxies to FastAPI, and FastAPI stores learners, topics, and sessions in PostgreSQL.

A session starts in `TOPIC_SELECTED`. Diagnosis moves it to `DIAGNOSING`, and a learning plan moves it to `PLAN_READY`. Resume reloads that saved session and records when it was resumed. Teaching and pedagogy begin in later phases.

A signed-in learner has a private record: profile, goals, preferences, topic knowledge, misconceptions, assessment history, and learning activities. Observed knowledge was demonstrated. Inferred knowledge is an estimate or a self-report, and a correction does not turn it into an observation. Session history is `GET /api/sessions/{session_id}/history`.

Open http://localhost:3000 for the landing page. Create an account, then continue in Teacher Mode. Sign-in uses an HttpOnly cookie. Passwords are stored as bcrypt hashes and are not written to logs. A signed-in learner only sees their own sessions.

## Run the stack

From the repository root:

```powershell
docker compose up --build
```

Open http://localhost:3000.

The local database credentials are `ai_teacher` / `ai_teacher` on port 5432. They are for this development stack. API logs are JSON on the `api` container stdout. Web proxy logs are JSON on the `web` container stdout.

```powershell
docker compose logs -f api
docker compose logs -f web
```

A log line looks like:

```json
{"timestamp":"...","level":"INFO","logger":"app.core.middleware","message":"request_completed","request_id":"...","fields":{"method":"POST","path":"/api/learners","status_code":201,"duration_ms":8.2}}
```

Connection strings, bearer tokens, and API keys are redacted before a line is written. Learner display names are stored in the database and are not written to info logs.

## Errors

Failed responses use one envelope:

```json
{"error":{"code":"learner_not_found","message":"Learner was not found.","request_id":"..."}}
```

The same request ID is returned in the `X-Request-ID` header. Validation errors add a `details` array of `field` and `message`. `/health` returns `{"status":"ok","database":"ok"}` only when PostgreSQL answers. If the database is down, it returns `503` with code `database_unavailable`.

## Tests

API tests run inside the API image so they use the same Python as the service. They create a separate `ai_teacher_test` database, drop its schema, and apply migrations from empty.

```powershell
docker compose run --rm api python -m pytest
```

Web tests:

```powershell
cd apps/web
npm install
npm test
```

## Run the processes without rebuilding images

Start only the database:

```powershell
docker compose up -d db
```

API, from `services/api`:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
$env:DATABASE_URL = "postgresql+psycopg://ai_teacher:ai_teacher@localhost:5432/ai_teacher"
$env:LOG_LEVEL = "INFO"
$env:WEB_ORIGIN = "http://localhost:3000"
.\.venv\Scripts\python -m app.entrypoint
```

Web, from `apps/web`:

```powershell
npm install
npm run dev
```

The web app proxies to `http://127.0.0.1:8000` unless `API_PROXY_TARGET` is set.

Copy `.env.example` when you want those values in a file. Do not commit `.env`.

## Phase 0 acceptance

- Frontend and backend start with Docker Compose.
- The web app reaches `/health` through its proxy.
- Alembic upgrades a clean database, and the migration can downgrade and upgrade again.
- `/health` reports database failure instead of a standing ok.
- A learner, topic, and session can be created and fetched.
- Resume keeps the same session id and `TOPIC_SELECTED` status after the write is committed.
- Pytest and Vitest pass.
- `.env` is listed in `.gitignore`.

## Gemini verification

Gemini stays on the backend. Routine tests use the mock provider and do not call the API. A model is usable only after `scripts/check_gemini_models.py` records a successful live generation and structured-output check. The script reads `GEMINI_API_KEY` from the environment and does not print it.

```powershell
docker compose run --rm -v "${PWD}/docs:/docs" -e MODEL_STRATEGY_PATH=/docs/GEMINI_MODEL_STRATEGY.md api python scripts/check_gemini_models.py
```

The report is `docs/GEMINI_MODEL_STRATEGY.md`. Internal cost figures in that report are estimates. The hard stop is USD $20.

## Learner dashboard

Open http://localhost:3000/learn after signing in. The page saves a display name, a background note, preferences, a goal, a self-reported knowledge record, an assessment note, a misconception, and a learning activity. Self-reported knowledge and misconceptions are labeled “Inferred, not confirmed.” Reloading the page reads the same rows back from PostgreSQL. A session history view lists the knowledge, assessments, misconceptions, and activities saved for that topic.

## Diagnosis

A signed-in learner can add learning objectives to a topic, including prerequisite codes that already exist on that topic, then start a diagnosis from a saved session. The session moves from topic selected to diagnosing. Questions have to use those objective codes. Answers and reasoning are judged separately. A completed report stores the starting point, confidence, and any misconception evidence copied from the learner's own response. Uncertain judgments stay unconfirmed.

Local diagnosis uses `AI_PROVIDER=mock` and does not call Gemini. Set `AI_PROVIDER=gemini` only for a live check after a model has passed `scripts/check_gemini_models.py` for the diagnostic task. Routine tests keep the mock provider.

## Learning plan

After a diagnosis is complete, build a learning plan from the same session. The plan orders every objective by its prerequisites, gives each step that objective's completion criteria, and starts at the first step that does not yet have observed diagnostic evidence. A partial or uncertain answer does not skip a concept. Adding a prerequisite that would create a cycle is rejected. A later diagnostic follow-up can revise the plan; the previous revision stays stored and the active plan is the one shown on `/learn`. The session status becomes plan ready. Teaching does not start in this phase.

The sequence is computed in the API. Routine tests keep `AI_PROVIDER=mock` and do not call Gemini.

## Pedagogy selection

After a plan is ready, Choose strategies records a deterministic selection for the current plan step. The same inputs and policy version return the same strategy ids. A missing prerequisite selects small-step instruction with concrete and worked examples. Repeated failure skips the strategy that already failed. Strong performance leaves scaffolding, worked examples, and guided practice off the list. The saved decision does not change the session away from plan ready, and `controls_teaching` stays false. Unreviewed registry entries are not a production selection. `GET /api/sessions/{session_id}/pedagogy-selection` returns the saved decision to the signed-in learner only.

## Teaching

Start lesson runs the saved strategy choice as structured activities for the current plan objective. The session moves to teaching. A check sits before the last activity. The first hint does not contain the complete answer, and the answer is not returned by the API. Continue lowers the next activity's support by one step. I need more support inserts a high-support activity from a strategy already on the selection. Reloading or Resume keeps the same lesson. The lesson stays pending factuality review, and the session does not move on to evaluation.

Local teaching uses `AI_PROVIDER=mock` and does not call Gemini.

## Pedagogy registry

`research/strategies/` and `research/sources/` hold the P0 catalogue. Bibliographic metadata was checked on 2026-11-21. The notes are original and pending human review, so none of the strategies can be selected in production. `GET /api/pedagogy/registry` returns the catalogue and an empty `production_selectable_strategy_ids` list. Ingestion and the review checklist are in `docs/RESEARCH_INGESTION.md` and `docs/HUMAN_REVIEW_CHECKLIST.md`. This phase does not choose a strategy and does not start teaching.
