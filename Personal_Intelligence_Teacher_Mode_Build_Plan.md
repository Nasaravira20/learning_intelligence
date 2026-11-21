# Personal Intelligence --- Teacher Mode Build Plan

> **Working principle:** Build Teacher Mode first. Keep the broader
> Personal Mentor / Personal Intelligence vision in the architecture,
> but do not implement mentor, always-on companion, or institutional
> features until Teacher Mode is working and validated.

## 1. Product vision

### 1.1 Long-term direction

Build a personal intelligence companion that understands an individual,
helps them learn, supports their growth, and improves its guidance over
time.

The broader product may eventually include:

-   **Personal Mentor:** goals, decisions, planning, accountability,
    career and skill development.
-   **Personal Teacher:** adaptive learning, practice, assessment, and
    mastery.
-   **Memory:** relevant personal context, preferences, history, and
    insights.
-   **Companion:** voice, summaries, reminders, and continuity across
    devices.

### 1.2 First product to build: Teacher Mode

Teacher Mode is an adaptive teaching system---not a general-purpose
chatbot that simply answers questions.

Its job is to:

1.  Understand the learner and their learning goal.
2.  Diagnose what they already know.
3.  Identify knowledge gaps, missing prerequisites, and misconceptions.
4.  Create a suitable learning path.
5.  Teach using an appropriate explanation strategy.
6.  Check understanding through reasoning and application.
7.  Adapt its teaching when the learner struggles.
8.  Track mastery and schedule retention checks.
9.  Resume the learner's journey across sessions.

**Core learning loop:**

`Understand → Diagnose → Plan → Teach → Evaluate → Adapt → Retain`

### 1.3 Product positioning

**Core principle:** From Answer Intelligence to Learning Intelligence.

Differentiate through: - A persistent learner model rather than isolated
chat history. - Explicit diagnosis of prior knowledge and
misconceptions. - Pedagogical decisions about what to teach next and
how. - Evaluation of demonstrated understanding, not just answer
generation. - A longitudinal record of mastery, retention, and learning
progress. - Evidence that the system improves learning outcomes.

Do not claim that the product is uniquely capable or demonstrably better
until it has been benchmarked against alternatives.

## 2. Definition of done

Teacher Mode is ready for an MVP pilot when a new learner can:

1.  Create an account and choose a subject or topic.
2.  Complete a diagnostic assessment.
3.  Receive a learning plan suited to their current knowledge.
4.  Learn through an adaptive lesson.
5.  Answer questions and solve unfamiliar problems.
6.  Receive an evaluation with explanations and targeted remediation.
7.  Demonstrate mastery against explicit criteria.
8.  Have progress saved and resume later.
9.  Return after a delay and complete a retention assessment.
10. See an understandable record of progress and next steps.

A fluent explanation alone does **not** count as a completed learning
experience. Mastery must be supported by assessment evidence.

## 3. Scope and prioritization

### 3.1 MVP scope

Prioritize:

1.  Learner profile and learner model.
2.  Diagnostic assessment.
3.  Teaching and lesson planning.
4.  Evaluation and misconception detection.
5.  Adaptive learning loop.
6.  Learning progression and mastery tracking.
7.  Session history and persistence.
8.  Basic retention/revision scheduling.
9.  A usable learning interface.
10. Logging, testing, security, and deployment basics.

### 3.2 Later scope --- do not build yet

Keep these in the roadmap, but do not let them delay the first working
Teacher Mode:

-   Simulated classroom with multiple student personas.
-   Learner-as-teacher simulations.
-   Advanced visual simulations and interactive diagrams.
-   Broad web research and source intelligence.
-   Full document and video ingestion.
-   Teacher copilot and institutional analytics.
-   Communities, peer learning, and course marketplaces.
-   Personal Mentor workflows unrelated to learning.
-   Always-on audio, transparent recording, VAD, and multi-device
    companion features.

### 3.3 Five learning depth levels

  -----------------------------------------------------------------------
  Level                   Learner can...          Evidence
  ----------------------- ----------------------- -----------------------
  1\. Familiarization     Recognize terms and     Accurate recall
                          explain basic           
                          definitions             

  2\. Conceptual          Explain why/how and     Explanation in their
  understanding           connect ideas           own words

  3\. Practical           Apply concepts to       Correct worked example
  application             familiar tasks          

  4\. Critical thinking   Analyze, compare,       Reasoned transfer task
                          challenge, and solve    
                          unfamiliar problems     

  5\. Mastery and         Independently apply or  Novel solution or
  creation                teach the concept       teach-back
  -----------------------------------------------------------------------

The evaluation process should determine whether the learner is ready to
progress. Do not treat one correct multiple-choice answer as proof of
mastery.

## 4. Agent and workflow architecture

### 4.1 Logical roles

Use modular roles with clear responsibilities. These are logical
components, not a requirement to deploy six separate LLM services.

  -----------------------------------------------------------------------
  Role                    Responsibility          Expected output
  ----------------------- ----------------------- -----------------------
  Orchestrator            Controls workflow,      Valid next workflow
                          state, routing,         action
                          retries, and tool       
                          permissions             

  Learner Intelligence    Reads and updates       Structured learner
                          learner profile and     context
                          learning history        

  Diagnostic              Assesses prior          Diagnostic report
                          knowledge and finds     
                          gaps/prerequisites      

  Teaching                Plans and delivers      Structured lesson
                          explanations, examples, 
                          and practice            

  Evaluation              Scores reasoning,       Rubric-based evaluation
                          application, and        
                          misconceptions          

  Learning Planner        Recommends progression  Next-step plan
                          and revision            
  -----------------------------------------------------------------------

### 4.2 Important engineering rule

Do not make every operation an agent. Use deterministic code for:

-   Database reads and writes.
-   Session state transitions.
-   Scheduling and due dates.
-   Authorization and access control.
-   Input validation.
-   Budget and rate-limit enforcement.
-   Retry policies and audit logs.

Use an LLM where interpretation, teaching, generation, or judgment is
genuinely needed. All model outputs that affect state must be validated
against schemas and business rules.

### 4.3 End-to-end workflow

1.  Learner selects a topic.
2.  Backend loads learner profile and relevant learning history.
3.  Diagnostic component generates a short, targeted assessment.
4.  Learner answers; the system evaluates the evidence.
5.  System identifies prerequisites, gaps, and likely misconceptions.
6.  Teaching component creates a lesson plan at the right level.
7.  Learner studies the lesson and completes practice.
8.  Evaluation component assesses reasoning and application using a
    rubric.
9.  If understanding is insufficient, the system identifies the gap and
    changes teaching strategy.
10. If mastery criteria are met, the system updates mastery and
    recommends the next step.
11. Backend schedules a retention check and persists the session.

### 4.4 Workflow state machine

Implement explicit states, for example:

`TOPIC_SELECTED → DIAGNOSING → PLAN_READY → TEACHING → PRACTICE → EVALUATING`

From `EVALUATING`, transition to: - `REMEDIATION` when evidence is
insufficient. - `MASTERED` when mastery criteria are met. -
`NEEDS_REVIEW` when the result is uncertain or insufficiently evidenced.

Then schedule: `RETENTION_DUE → RETENTION_ASSESSMENT → MASTERY_UPDATED`

Persist state transitions. A page refresh or service restart must not
lose the learner's place.

## 5. Gemini API model strategy

### 5.1 Design principle

Use Gemini as the initial model provider, but keep a
provider-independent interface so models can be changed without
rewriting product logic.

**Do not hard-code model names throughout the application.** Put model
assignments in environment/configuration and maintain a model capability
registry.

The model names and availability can change. Cursor must verify the
current official Gemini API model catalogue and pricing before choosing
production defaults. Do not assume that a model shown in AI Studio is
necessarily available to this API key, project, region, or billing
configuration.

### 5.2 Initial task-to-model routing

Start with a small number of models. Do not use the most expensive model
for every request.

  -------------------------------------------------------------------------
  Layer / task      Initial model tier  Why               Fallback
  ----------------- ------------------- ----------------- -----------------
  Orchestrator      Deterministic code  Workflow routing  Rule-based
  decisions         first;              should be         routing
                    fast/low-cost       reliable and      
                    Gemini model only   inexpensive       
                    for ambiguous                         
                    intent                                

  Learner profile   Fast/low-cost model Extract           Retry once, then
  extraction                            structured facts  mark uncertain
                                        from learner      
                                        responses         

  Diagnostic        Strong              Questions must    Fast model with
  question          general-purpose     target            constrained
  generation        model               prerequisites and template
                                        knowledge gaps    

  Diagnostic answer Strong              Requires          Second-pass
  interpretation    general-purpose     reasoning about   evaluation or
                    model               partial           human review
                                        understanding     

  Teaching and      Best affordable     Explanation       Fast model for
  lesson generation general-purpose     quality is        simple
                    model that passes   central to the    explanations
                    quality tests       product           

  Evaluation and    Strong              Incorrect mastery Re-evaluate
  misconception     reasoning-capable   decisions damage  uncertain cases;
  detection         model               learning outcomes do not auto-award
                                                          mastery

  Short summaries   Fast/low-cost model Simple generation Deterministic
  and session                           task              title fallback
  titles                                                  

  Embeddings /      Dedicated embedding Search learner    Keyword search
  semantic          model, only when    notes and         
  retrieval         retrieval is        resources         
                    implemented                           

  Speech / audio    Separate            Not required for  Defer
                    speech-capable      initial text MVP  
                    model or API, later                   
                    phase                                 
  -------------------------------------------------------------------------

This is a routing policy, not a claim that a particular Gemini model has
already been tested or is available to the supplied key.

### 5.2.1 Recommended starting candidates (verify against the key)

Use these as **candidate defaults to test**, not guaranteed access:

| Layer | First candidate to test | Alternative / fallback |
|---|---|---|
| Teaching | `gemini-3.8-flash` | Another currently listed Flash model that passes the teaching benchmark |
| Diagnostic generation and interpretation | `gemini-3.8-flash` | A currently listed Pro/reasoning-capable model only if it improves benchmark results and fits the budget |
| Evaluation and misconception detection | `gemini-3.8-flash` | Escalate uncertain/high-impact evaluations only; otherwise return `needs_review` |
| Learner profile extraction | `gemini-2.5-flash-lite` | `gemini-3.8-flash` |
| Session summaries and titles | `gemini-2.5-flash-lite` | Deterministic fallback |
| Orchestration | Deterministic workflow code | `gemini-2.5-flash-lite` for ambiguous natural-language intent only |
| Embeddings | Defer until retrieval is implemented | Verify a currently supported embedding model separately |

Why start this way: one capable Flash model can handle the core teaching workflow while a cheaper Flash-Lite-class model handles simple extraction and summaries. This keeps the initial integration small and makes the $20 budget easier to control. These are candidate model IDs, not a guarantee that the supplied key can use them. If a candidate is absent from the key's model list or fails a real generation test, do not configure it.

For a new Gemini integration, Cursor must check Google's current API guidance. Google's current developer documentation identifies the **Interactions API** as the recommended/default interface for new agentic applications. Use it where the selected model and required features are supported. If a required capability is not supported, document why another supported API is being used; do not blindly copy older `generateContent` examples.

### 5.3 Model selection procedure

Cursor must implement a model verification utility before selecting
defaults:

1.  Read the API key from `GEMINI_API_KEY`; never put it in source code,
    frontend variables, logs, screenshots, or committed files.
2.  Call the official Gemini API model-list endpoint using the key.
3.  Store the returned model IDs and supported methods in a local
    diagnostic report, excluding the secret.
4.  For each candidate model, verify that it supports the required
    generation method.
5.  Run a minimal generation request against each candidate.
6.  Record success/failure, latency, returned model ID, and sanitized
    error category.
7.  Run structured-output tests for the tasks that need JSON.
8.  Run a small teaching/evaluation benchmark before assigning a model
    to a critical layer.
9.  Select the cheapest model that passes the quality and reliability
    threshold for each task.
10. Re-run this check when the key, project, billing setup, SDK, or
    model configuration changes.

**Important:** A model appearing in the list is not sufficient proof
that generation will work. The smoke test must make an actual request.

### 5.4 Required model capability test

Create a script such as:

`services/api/scripts/check_gemini_models.py`

It should: - List models accessible to the configured key. - Show
supported generation methods where the API returns them. - Test a tiny
prompt against each configured candidate. - Test JSON/schema-constrained
output for models assigned to structured tasks. - Report latency and
success status. - Categorize errors: invalid key, permission/access,
model not found, quota/rate limit, billing/project restriction, network,
and unknown. - Exit non-zero if no configured model passes the minimum
required test. - Never print the API key or full authorization headers.

Example report:

  --------------------------------------------------------------------------------
  Model ID            Listed     Generate   Structured      Latency Status
                                     test       output              
  ------------- ------------ ------------ ------------ ------------ --------------
  candidate-a            Yes         Pass         Pass     measured Available

  candidate-b            Yes         Fail          ---          --- Access/quota
                                                                    error
  --------------------------------------------------------------------------------

Do not invent model IDs in this report. Populate it from the live API
response.

### 5.5 Model configuration

Use configuration similar to this (actual model IDs must be selected
only after live verification):

``` env
GEMINI_API_KEY=replace_me
GEMINI_MODEL_FAST=verified_model_id
GEMINI_MODEL_TEACHING=verified_model_id
GEMINI_MODEL_EVALUATION=verified_model_id
GEMINI_MODEL_DIAGNOSTIC=verified_model_id
GEMINI_MODEL_EMBEDDING=verified_embedding_model_id
```

Keep `.env` out of Git. Commit only `.env.example` with placeholder
values.

Centralize model routing in a service such as:

`services/api/app/ai/model_registry.py`

The application should be able to change a model assignment through
configuration without changing agent or workflow code.

### 5.6 Model quality benchmark

Before using a model for teaching or evaluation, run a small fixed
benchmark containing:

-   Beginner explanation of a known concept.
-   Explanation adapted for a learner with partial knowledge.
-   Detection of a deliberately included misconception.
-   Diagnostic questions for a stated prerequisite.
-   Evaluation of a correct answer with weak reasoning.
-   Evaluation of an incorrect answer with sound partial reasoning.
-   A novel application problem.
-   Strict structured-output response.

Score each response for: - Factual correctness. - Clarity and
learner-appropriate language. - Reasoning quality. - Misconception
detection. - Schema validity. - Consistency across repeated runs. -
Latency and token usage.

Keep the benchmark prompts and expected evaluation rubric versioned in
`tests/ai/`. A model is not approved for a critical layer merely because
it returns HTTP 200.

## 6. API budget and cost controls

### 6.1 Budget assumption

The available Gemini API budget is **USD \$20 total for the
project/team**, not \$20 per agent or per layer. Treat this as a hard
ceiling unless the owner explicitly changes it.

Actual cost depends on the model, input/output tokens, cached tokens,
tool use, and current provider pricing. Do not assume the full \$20 is
available for ordinary development calls.

### 6.2 Suggested internal allocation

Use this as an initial planning allocation, not as a claim about
provider billing controls:

  Use                                     Internal budget
  ------------------------------------- -----------------
  Model availability and smoke tests                  \$1
  Development and debugging                           \$3
  Teaching and diagnostic experiments                 \$5
  Evaluation and benchmark runs                       \$5
  Final end-to-end demo buffer                        \$4
  Emergency reserve                                   \$2
  **Total**                                      **\$20**

The backend must enforce its own budget guardrails. Provider-side quotas
or billing alerts are additional protection, not a replacement.

### 6.3 Required cost controls

Implement: - A centralized Gemini client; no direct model calls
scattered across routes. - Per-request input/output token limits. -
Maximum number of model calls per learner action. - Retry limits; do not
retry quota or invalid-key errors indefinitely. - Timeouts and
exponential backoff for transient failures only. - Usage logging per
request: task, model ID, input/output token counts when available,
latency, status, and estimated cost. - Daily and total project budget
counters. - A configurable hard stop when the internal budget threshold
is reached. - A low-cost fallback for non-critical tasks. - A clear
user-facing error when the budget guard blocks a request. - A
development mode with mock responses so frontend work does not consume
API credits.

Never log learner secrets or the Gemini API key. Minimize storage of raw
prompts and responses in operational logs; learning content belongs in
the application database under the product's privacy policy.

### 6.4 Cost reporting

Create an admin/developer usage summary showing: - Total estimated
spend. - Spend by model. - Spend by task/layer. - Request count. - Input
and output tokens. - Average latency. - Failed requests. - Remaining
internal budget estimate.

Clearly label calculated costs as estimates unless they are reconciled
with provider billing data. The app must not claim to know the
provider's exact remaining credit if the API does not expose it.

## 7. Proposed technical stack

Use this as the starting point; document any changes before
implementation.

  -----------------------------------------------------------------------
  Area                                Initial choice
  ----------------------------------- -----------------------------------
  Frontend                            Next.js + TypeScript

  UI                                  Tailwind CSS + component library

  Backend                             Python + FastAPI

  Database                            PostgreSQL

  Vector retrieval                    pgvector, only when needed

  AI provider                         Gemini through a provider
                                      abstraction

  Workflow                            Explicit state machine initially;
                                      LangGraph only if complexity
                                      justifies it

  Background jobs                     Add a worker/queue when retention
                                      scheduling requires it

  Cache                               Redis later, if measured need
                                      exists

  File storage                        S3-compatible storage when file
                                      uploads are introduced

  Observability                       Structured logs first;
                                      OpenTelemetry as the system grows

  Tests                               Pytest + frontend test framework

  Deployment                          Docker and Docker Compose for local
                                      development
  -----------------------------------------------------------------------

Start with one capable model and a small fast model, if both are
available and pass tests. Avoid premature microservices and unnecessary
agent frameworks.

## 8. Data model --- initial entities

Design migrations for the minimum viable entities:

-   `users`
-   `learner_profiles`
-   `learning_topics`
-   `learning_sessions`
-   `messages`
-   `diagnostic_attempts`
-   `learner_knowledge`
-   `lesson_plans`
-   `assessments`
-   `assessment_attempts`
-   `mastery_records`
-   `revision_schedule`
-   `ai_usage_records`

Store structured evaluation evidence, not only a single opaque mastery
score. Include timestamps and version fields where they help audit
changes. Apply user-level authorization to every learner-owned record.

## 9. Roadmap and milestones

The estimates below are planning estimates for a solo developer, not
fixed deadlines. Finish and verify each milestone before starting the
next.

### Milestone 0 --- Product and engineering foundation

**Deliverables** - Repository and directory structure. - Product and
architecture documents. - Next.js frontend shell. - FastAPI backend
shell. - PostgreSQL and migrations. - Docker Compose. - Environment
configuration. - Health endpoints. - Frontend-to-backend connectivity. -
Structured logging and basic tests.

**Acceptance criteria** - Frontend and backend start locally. - Database
connection and migrations work. - Health endpoints return correct
status. - Frontend can create and retrieve a learning session. - Tests
pass. - No secrets are committed.

### Milestone 1 --- Gemini integration and model verification

**Deliverables** - Centralized Gemini client. - Provider abstraction. -
Live model-listing and smoke-test script. - Candidate model capability
report. - Environment-based model registry. - Usage and latency
logging. - Token limits, timeout, retry, and budget guard. - Mock
provider for development and tests.

**Acceptance criteria** - The supplied key can list accessible models
through the official API. - Each configured model passes a real
generation test. - Unsupported or inaccessible models are identified
clearly. - Structured output is tested for relevant models. - The key
never appears in logs or frontend code. - A mocked test suite runs
without spending API credits. - A real request is recorded with model,
latency, token usage when available, and estimated cost. - Internal
budget guard blocks calls at its configured threshold.

### Milestone 2 --- Learner Intelligence

**Deliverables** - Learner profile. - Learning goals and preferences. -
Knowledge records by topic. - Learning history retrieval. - Confidence
and misconception fields with provenance.

**Acceptance criteria** - Profile data persists across sessions. - The
system distinguishes known facts from uncertain inferences. - Relevant
learner context is passed to the teaching workflow. - The learner can
view and correct profile information.

### Milestone 3 --- Diagnostic Intelligence

**Deliverables** - Diagnostic question generation. - Prerequisite
mapping for the selected topic. - Answer and reasoning analysis. -
Knowledge-gap and misconception report.

**Acceptance criteria** - A beginner and a partially knowledgeable
learner receive meaningfully different starting points. - Diagnostic
output follows a validated schema. - Uncertain diagnosis is represented
as uncertain, not as fact. - Diagnostic evidence is saved.

### Milestone 4 --- Teaching Intelligence

**Deliverables** - Structured lesson plans. - Concept decomposition. -
Adaptive explanations and examples. - Practice questions. - Strategy
switching when the learner struggles.

**Acceptance criteria** - Lessons follow the diagnostic results. - The
system can explain a concept in more than one way. - A repeated failure
triggers a different strategy, not merely the same explanation again. -
Teaching output passes factual and schema checks.

### Milestone 5 --- Evaluation Intelligence

**Deliverables** - Assessment generation. - Rubric-based answer
evaluation. - Reasoning and transfer assessment. - Misconception
detection. - Evidence-based feedback.

**Acceptance criteria** - The system distinguishes a correct guess from
a reasoned answer where evidence permits. - Partial understanding
receives partial credit and actionable feedback. - Evaluation output
includes evidence and confidence. - Mastery is not awarded from a single
trivial recall question.

### Milestone 6 --- Adaptive Learning Engine

**Deliverables** - Persistent workflow state machine. -
Advance/remediate/re-explain/reassess decisions. - Teaching strategy
selection. - Difficulty adjustment. - Mastery progression.

**Acceptance criteria** - A failed assessment routes to targeted
remediation. - A successful assessment can progress the learner. - Every
transition is validated and persisted. - A learner can resume after
refresh or restart.

### Milestone 7 --- Retention Intelligence

**Deliverables** - Revision schedule. - Due-review list. - Delayed
assessment. - Mastery update based on retention evidence.

**Acceptance criteria** - A review can be scheduled after a learning
session. - Completing a review updates the learner's mastery record. -
Missed or failed reviews trigger a sensible next review. - Scheduling is
deterministic and tested.

### Milestone 8 --- Advanced teaching experience

**Deliverables** - Learner-as-teacher activity. - Simulated student
personas. - Concept maps or visual explanations where useful. -
Practical assignments.

**Acceptance criteria** - Simulated personas ask questions appropriate
to their configured behavior. - Feedback evaluates conceptual accuracy
and clarity against a rubric. - Visual elements are useful and
accessible, not decorative filler.

### Milestone 9 --- Quality, pilot, and release

**Deliverables** - AI benchmark suite. - Regression tests. - Cost and
latency dashboard. - Security and privacy review. - End-to-end tests. -
Pilot feedback and product refinements. - Deployment and operational
documentation.

**Acceptance criteria** - Core workflows pass repeatable end-to-end
tests. - Model changes can be evaluated against a fixed benchmark. -
Errors, costs, and latency are observable. - A small pilot demonstrates
measurable learning improvement or identifies where the product fails. -
Known limitations are documented.

## 10. Evaluation and pilot design

Do not evaluate Teacher Mode only by whether users like the
explanations.

Run a small controlled pilot:

-   **Group A:** conventional LLM chat or a reasonable baseline teaching
    workflow.
-   **Group B:** adaptive Teacher Mode.
-   Use comparable topics, learner starting levels, and learning time.
-   Give both groups a pre-test, immediate post-test, and delayed
    retention test.
-   Include at least one transfer question that was not used in the
    lesson.

Measure: - Conceptual understanding improvement. - Ability to solve
unfamiliar problems. - Delayed retention. - Misconception correction. -
Completion rate. - Learner-reported clarity and usefulness. - Cost and
latency per completed learning session.

Initial engineering targets may be set for diagnostic accuracy,
evaluation agreement, and workflow reliability, but treat them as
hypotheses until measured against human-reviewed data. Report sample
size and uncertainty; do not present a small pilot as proof of universal
effectiveness.

## 11. Initial repository structure

``` text
personal-intelligence/
├── apps/
│   └── web/
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── ai/
│       │   │   ├── providers/
│       │   │   ├── model_registry.py
│       │   │   └── prompts/
│       │   ├── agents/
│       │   ├── workflows/
│       │   ├── core/
│       │   ├── db/
│       │   ├── models/
│       │   ├── schemas/
│       │   └── services/
│       ├── scripts/
│       │   └── check_gemini_models.py
│       └── tests/
│           └── ai/
├── docs/
│   ├── PRODUCT_VISION.md
│   ├── PRD.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── AGENT_DESIGN.md
│   ├── GEMINI_MODEL_STRATEGY.md
│   ├── AI_BENCHMARKS.md
│   ├── DATA_MODEL.md
│   ├── API_CONTRACTS.md
│   ├── ROADMAP.md
│   └── decisions/
├── infrastructure/
├── tests/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

Adjust the structure if the implementation has a clear reason, but
document the decision. Do not create empty abstractions merely to match
this tree.

## 12. Cursor Agent working agreement

Use Cursor Agent as an implementation partner. Work one milestone at a
time.

### Rules for the agent

1.  Read this document completely before making changes.
2.  Inspect the existing repository before assuming it is empty.
3.  Do not implement the entire roadmap in one pass.
4.  Start with Milestone 0, then Milestone 1 (Gemini integration and
    model verification).
5.  Before coding a milestone, explain the proposed design,
    dependencies, files to be changed, and acceptance tests.
6.  Verify current Gemini API documentation, model availability methods,
    supported model capabilities, SDK usage, and pricing from official
    Google sources. Do not rely on stale model names or blog posts for
    API compatibility.
7.  Do not invent model IDs or claim that a model is available without
    testing it with the configured key.
8.  Keep Gemini API calls on the backend only.
9.  Keep secrets in environment variables; never commit `.env`.
10. Use typed schemas for model inputs and outputs. Validate model
    output before using it.
11. Add tests for success, malformed output, timeout, quota, invalid
    key, and unavailable model cases.
12. Use mocks for routine tests so tests do not consume the \$20 API
    budget.
13. Run the relevant tests and report exact results.
14. Update documentation to match the implementation.
15. List completed work, incomplete work, known limitations, and
    commands to run the project.
16. Stop at the end of each milestone and wait for approval before
    moving on.

### First implementation request

Implement **Milestone 0 only**:

-   Create the initial repository structure.
-   Build the Next.js + TypeScript frontend shell.
-   Build the FastAPI backend shell.
-   Add PostgreSQL and Docker Compose.
-   Add environment configuration and `.env.example`.
-   Add health endpoints and frontend/backend connectivity.
-   Add initial learning-session create/list/get endpoints.
-   Add database migrations and basic tests.
-   Write the core documentation listed in `docs/`.

Do not implement the teaching agents or call Gemini in Milestone 0.

At the end, run tests and verify the application locally. Provide exact
setup commands and a checklist against Milestone 0 acceptance criteria.
Then stop.

### Second implementation request --- after Milestone 0 is approved

Implement **Milestone 1 only**:

-   Verify official Gemini API documentation and current pricing.
-   Implement the provider abstraction and centralized Gemini client.
-   Implement live model listing for the supplied key.
-   Implement actual generation smoke tests for candidate models.
-   Test structured output for models intended for diagnostic, teaching,
    and evaluation tasks.
-   Generate a sanitized capability report.
-   Add configurable task-to-model routing.
-   Add usage logging, token limits, retry policy, and internal budget
    guard.
-   Add a mock provider and tests that do not use API credits.
-   Update `GEMINI_MODEL_STRATEGY.md` with the models that actually
    passed.

Do not begin Learner Intelligence until Milestone 1 is reviewed and
approved.

## 13. Security, privacy, and reliability checklist

-   [ ] Gemini key exists only in backend environment configuration.
-   [ ] `.env` is ignored by Git.
-   [ ] No key is returned by an API endpoint or printed in logs.
-   [ ] All learner-owned records enforce authorization.
-   [ ] Model outputs are schema-validated.
-   [ ] Model-generated content is treated as untrusted input.
-   [ ] Tool access is allowlisted and bounded.
-   [ ] Retries are capped.
-   [ ] Quota and billing errors fail safely.
-   [ ] Budget guard is tested.
-   [ ] Learners can inspect and correct stored profile information.
-   [ ] Data retention and deletion behavior is documented.
-   [ ] Tests use mocked model responses by default.

## 14. Project completion checklist

-   [ ] A learner can start and resume a learning session.
-   [ ] Learner profile and learning history persist.
-   [ ] Diagnostic assessment identifies gaps with evidence.
-   [ ] Lesson plan responds to the learner's current level.
-   [ ] Teaching can change strategy when the learner struggles.
-   [ ] Evaluation tests reasoning and application.
-   [ ] Misconceptions are identified and addressed.
-   [ ] Mastery decisions are evidence-based.
-   [ ] Learning progression is persistent.
-   [ ] Retention assessments can be scheduled and completed.
-   [ ] Gemini model access is verified for the configured key.
-   [ ] Each task is routed to a model that passed capability and
    quality tests.
-   [ ] Cost and usage are observable and bounded.
-   [ ] Security, reliability, and end-to-end tests pass.
-   [ ] A pilot measures actual learning outcomes.

**North-star metric:** verified learning progress per learner over time.

**Build discipline:** one milestone, one review, one approval, then the
next milestone.
