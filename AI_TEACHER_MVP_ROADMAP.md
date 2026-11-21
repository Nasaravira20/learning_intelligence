
# Research-Backed AI Teacher
## Product Roadmap, Technical Architecture, Research References & Phase-by-Phase Implementation Plan

**Project:** AI Teacher — Teacher Mode MVP  
**Development approach:** Cursor AI Agent + Human Review  
**Implementation style:** Phase-by-phase, test-driven, measurable deliverables  
**Initial AI provider:** Google Gemini API  
**Total API budget:** USD $20  
**Primary objective:** Build an AI system that improves a learner's understanding, not merely one that generates answers.

---

# 1. Product Vision

## 1.1 The Problem

Traditional AI chatbots are primarily answer-oriented.

A learner asks a question, receives an explanation, and moves on. The system generally does not establish:

- What the learner already understands.
- What foundational concepts are missing.
- Why the learner is struggling.
- Which teaching approach is appropriate.
- Whether the learner genuinely understood the explanation.
- Whether the learner can apply the concept independently.
- Whether the learner remembers it after several days.

We want to address this gap.

## 1.2 Our Product

Build an AI Teacher that understands a learner's current knowledge, identifies learning gaps, creates an adaptive learning plan, teaches using appropriate pedagogical strategies, evaluates understanding, and tracks long-term progress.

The core principle:

> From Answer Intelligence to Learning Intelligence.

The system should behave like an adaptive teacher rather than a conventional chatbot.

## 1.3 Core Learning Loop

The product must implement this complete cycle:

1. Understand the learner.
2. Diagnose existing knowledge.
3. Identify knowledge gaps and misconceptions.
4. Create a personalized learning plan.
5. Select appropriate teaching strategies.
6. Teach through structured learning activities.
7. Evaluate actual understanding.
8. Adapt the teaching approach.
9. Track mastery and retention.
10. Revisit concepts when necessary.

**Core workflow:**

`UNDERSTAND → DIAGNOSE → PLAN → TEACH → EVALUATE → ADAPT → RETAIN`

## 1.4 Definition of Success

A learner should be able to:

- Start learning a topic with little or no prior knowledge.
- Receive instruction appropriate to their current understanding.
- Practice concepts through structured activities.
- Explain why an answer is correct.
- Solve unfamiliar problems independently.
- Receive corrective instruction when they struggle.
- Return later and demonstrate retained knowledge.
- Resume their learning journey without losing progress.

### North-star metric

**Verified learning progress per learner over time.**

Do not measure success only through conversation length, number of generated answers, or learner satisfaction.

---

# 2. MVP Scope

The first release focuses exclusively on Teacher Mode.

Do not attempt to build the entire future Personal Intelligence Companion in this MVP.

## 2.1 Features Included in MVP

| Module | Responsibility |
|---|---|
| Learner Profile | Maintain learner knowledge, goals and preferences |
| Diagnostic Engine | Identify existing knowledge and knowledge gaps |
| Learning Planner | Create prerequisite-aware learning plans |
| Research Library | Maintain curated research and educational references |
| Pedagogy Registry | Store versioned teaching strategies |
| Pedagogy Selector | Select appropriate strategies using learner context |
| Teaching Engine | Generate structured teaching activities |
| Evaluation Engine | Evaluate understanding, reasoning and application |
| Adaptation Engine | Change teaching approach based on performance |
| Retention Engine | Schedule and conduct revision assessments |
| Progress Dashboard | Display mastery, history and upcoming revisions |

## 2.2 Features Deferred Until Later

- Always-on voice conversations.
- Continuous microphone listening.
- Voice activity detection and real-time interruption handling.
- Full PDF and video ingestion.
- Autonomous internet research without review.
- Simulated classroom environments.
- Multiple learner personas.
- Institutional analytics.
- Teacher marketplace.
- Multi-device synchronization.
- Large-scale multi-agent infrastructure.

These features should not delay the core learning loop.

---

# 3. Product Architecture

## 3.1 Architectural Principle

Use an agentic architecture where reasoning is useful, but keep critical application operations deterministic.

Do not create separate deployed agents for every module in the MVP.

Start with logical components inside a modular backend.

## 3.2 Main Components

### 1. Orchestrator

Responsible for:

- Managing the learning workflow.
- Determining the current learning state.
- Invoking the appropriate component.
- Validating transitions.
- Handling errors and retries.
- Maintaining session continuity.

The orchestrator should use deterministic workflow logic.

### 2. Learner Intelligence

Responsible for:

- Maintaining learner profiles.
- Tracking topic-level knowledge.
- Recording previous assessments.
- Identifying recurring weaknesses.
- Maintaining learner preferences.
- Retrieving relevant learning history.

It must distinguish observed evidence from inferred knowledge.

### 3. Diagnostic Engine

Responsible for:

- Identifying learning objectives.
- Generating diagnostic questions.
- Evaluating learner responses.
- Identifying misconceptions.
- Estimating confidence in diagnostic conclusions.

### 4. Learning Planner

Responsible for:

- Breaking topics into smaller concepts.
- Identifying prerequisites.
- Ordering learning objectives.
- Determining where the learner should begin.
- Creating a structured learning sequence.

### 5. Research Library

Responsible for:

- Maintaining research references.
- Storing source metadata.
- Recording educational evidence.
- Providing research-backed information to the pedagogy registry.

### 6. Pedagogy Registry

Responsible for:

- Maintaining teaching strategy definitions.
- Recording suitable learning contexts.
- Recording limitations and contraindications.
- Maintaining evidence and source references.
- Versioning strategies.

### 7. Pedagogy Selector

Responsible for:

- Understanding the learner's current situation.
- Checking strategy eligibility.
- Selecting primary and supporting strategies.
- Defining a teaching sequence.
- Providing a selection rationale.

Initially, use deterministic selection policies with structured model assistance where appropriate.

### 8. Teaching Engine

Responsible for:

- Generating structured lessons.
- Explaining concepts.
- Creating examples and non-examples.
- Generating practice activities.
- Providing hints.
- Fading instructional support.

### 9. Evaluation Engine

Responsible for:

- Assessing answers.
- Evaluating reasoning.
- Applying assessment rubrics.
- Identifying misconceptions.
- Providing corrective feedback.
- Determining whether further instruction is necessary.

### 10. Retention Engine

Responsible for:

- Scheduling revision.
- Generating delayed retrieval assessments.
- Updating mastery estimates.
- Maintaining retention history.

---

# 4. Suggested Technology Stack

Use the following as the initial stack. Change it only when there is a clear technical reason.

| Layer | Technology |
|---|---|
| Frontend | Next.js + TypeScript |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| AI Provider | Google Gemini API |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Backend Testing | Pytest |
| Frontend Testing | Vitest / Playwright |
| Containers | Docker + Docker Compose |
| API Validation | Pydantic |
| Version Control | Git |

## Important Architecture Decisions

1. Keep the AI provider behind an abstraction layer.
2. Never expose Gemini API keys in the frontend.
3. Validate all model-generated structured responses.
4. Keep learner history in PostgreSQL.
5. Use deterministic code for state transitions.
6. Keep retention scheduling deterministic.
7. Maintain research provenance.
8. Use mocks for routine development tests.
9. Do not introduce vector databases until retrieval requirements justify them.
10. Avoid microservices until actual scaling requirements demand them.

---

# 5. Learning Workflow and State Machine

The learning workflow must be explicit and persistent.

## 5.1 States

```text
TOPIC_SELECTED
      |
      v
DIAGNOSING
      |
      v
PLAN_READY
      |
      v
TEACHING
      |
      v
PRACTICE
      |
      v
EVALUATING
      |
      +-------------------+
      |                   |
      v                   v
REMEDIATION           MASTERED
      |                   |
      +-----> TEACHING    v
                    NEEDS_REVIEW
                         |
                         v
                    RETENTION_DUE
                         |
                         v
                 RETENTION_ASSESSMENT
                         |
                         v
                  MASTERY_UPDATED
```

`NEEDS_REVIEW` should also be available when the evaluation is ambiguous or insufficient to justify a mastery decision.

## 5.2 Workflow Requirements

- Every state transition must be persisted.
- Invalid transitions must be rejected.
- Sessions must survive application restarts.
- A learner must be able to resume an unfinished session.
- Every assessment must be associated with a learning objective.
- Every mastery update must have supporting evidence.
- Uncertain evaluation must not automatically result in mastery.

---

# 6. Research-Backed Pedagogy Strategy Library

This is one of the most important parts of the product.

The system should not randomly choose teaching styles.

It should maintain a structured registry of teaching strategies, their evidence, appropriate contexts and limitations.

The strategies below are the initial catalogue. They are starting hypotheses for implementation, not universal rules that guarantee learning.

## 6.1 P0: Strategies for the MVP

### A. Retrieval Practice

**Purpose:** Strengthen recall and identify knowledge gaps.

Implementation:

1. Ask the learner to retrieve previously taught information.
2. Do not immediately reveal the answer.
3. Allow the learner to attempt recall.
4. Evaluate the response.
5. Provide corrective feedback.
6. Record the result.

Important: Retrieval practice is not a replacement for initial instruction. Incorrect retrieval should be followed by appropriate corrective feedback.

### B. Spaced Practice

**Purpose:** Improve long-term retention.

Implementation:

1. Record when a concept was learned.
2. Schedule a later retrieval assessment.
3. Evaluate recall.
4. Update the next revision schedule.
5. Track retention over time.

Revision intervals should be configurable and validated. Do not assume one universal schedule works for every learner.

### C. Worked Examples

**Purpose:** Help learners understand how to solve a problem.

Implementation:

1. Present a problem.
2. Show the complete solution.
3. Explain each step.
4. Explain why each step is necessary.
5. Ask the learner to solve a related problem.

Especially useful as an initial support for learners who lack prerequisite knowledge.

### D. Guided Practice

**Purpose:** Help learners move from understanding to independent application.

Implementation:

1. Present a problem.
2. Ask the learner to solve the first step.
3. Provide hints when necessary.
4. Gradually reduce support.
5. Evaluate independent performance.

### E. Scaffolding and Gradual Release

**Purpose:** Provide temporary instructional support.

Implementation:

1. Begin with explicit instruction.
2. Provide a worked example.
3. Solve a problem together.
4. Reduce hints.
5. Ask the learner to solve independently.

The support must gradually fade.

### F. Small-Step Instruction

**Purpose:** Reduce unnecessary cognitive load.

Implementation:

1. Break complex concepts into smaller units.
2. Teach one important idea at a time.
3. Check understanding.
4. Resolve gaps before introducing dependent concepts.
5. Combine the ideas once foundational understanding is established.

### G. Checks for Understanding

**Purpose:** Identify confusion before continuing.

Implementation:

- Ask short questions during instruction.
- Check conceptual understanding.
- Ask the learner to predict outcomes.
- Ask for explanations rather than only definitions.
- Use the responses to determine the next step.

### H. Formative Feedback

**Purpose:** Help learners understand how to improve.

Feedback should contain:

1. What was correct.
2. What was incorrect or missing.
3. Why it matters.
4. What the learner should try next.

Avoid generic feedback such as "Good job" without meaningful information.

### I. Self-Explanation

**Purpose:** Encourage the learner to explain the reasoning behind an answer.

Examples:

- Why does this equation work?
- Why did you choose this method?
- What would happen if this assumption changed?
- How are these two concepts related?

### J. Concrete Examples and Non-Examples

**Purpose:** Help learners distinguish a concept from similar concepts.

Implementation:

- Present a valid example.
- Present a non-example.
- Explain the difference.
- Ask the learner to classify new cases.

### K. Elaborative Interrogation

**Purpose:** Encourage deeper understanding through why/how questions.

Examples:

- Why does this happen?
- How does this relate to the previous concept?
- Why is this method appropriate?
- What would change if the conditions were different?

### L. Mastery Learning

**Purpose:** Ensure that important learning objectives are achieved before progressing.

Implementation:

1. Define an objective.
2. Assess the learner.
3. Identify missing understanding.
4. Provide corrective instruction.
5. Reassess.
6. Advance when the mastery criteria are satisfied.

Mastery must be based on sufficient evidence, not merely confidence or a single correct answer.

## 6.2 P1: Strategies for Later Versions

- Interleaved practice.
- Dual coding.
- Concept mapping.
- Teach-back / learning by teaching.
- Analogical comparison.
- Varied practice.
- Transfer-oriented practice.
- Multimedia segmenting.

These should be added after the core MVP loop works.

Important limitations:

- Interleaving may be unsuitable before foundational methods are understood.
- Dual coding is not decorative imagery; representations must support learning.
- Analogies need explicit explanations of where they stop being accurate.
- Teach-back is useful as an assessment activity, but fluent explanations alone do not prove mastery.

---

# 7. Pedagogy Registry Design

Use YAML or JSON files under version control initially.

Do not build a complex strategy management dashboard in the first version.

## 7.1 Strategy Schema

Each strategy should contain:

```yaml
strategy_id: retrieval_practice
name: Retrieval Practice
version: 1.0

category: memory_and_retrieval

description: >
  Ask learners to retrieve previously learned information
  before showing the answer.

learning_objectives:
  - recall
  - retention
  - diagnosis

suitable_contexts:
  - previously_taught_concepts
  - revision
  - knowledge_assessment

learner_conditions:
  - initial_instruction_has_been_provided

avoid_or_modify_conditions:
  - learner_has_never_been_taught_the_concept

implementation_steps:
  - Ask a focused question.
  - Allow independent recall.
  - Evaluate the response.
  - Provide corrective feedback.

assessment_signals:
  - independent_recall
  - delayed_recall_accuracy
  - explanation_quality

limitations:
  - Incorrect retrieval requires corrective feedback.
  - Not a substitute for initial instruction.

sources:
  - weinstein_2018

review_status: reviewed
```

## 7.2 Research Source Schema

Each source should contain:

```yaml
source_id: weinstein_2018

title: Teaching the Science of Learning

authors:
  - Yana Weinstein
  - Christopher R. Madan
  - Megan A. Sumeracki

year: 2018

publication: Cognitive Research: Principles and Implications

doi: 10.1186/s41235-017-0087-y

url: https://link.springer.com/article/10.1186/s41235-017-0087-y

access_type: open_access

license: CC BY 4.0

retrieved_date: YYYY-MM-DD

relevant_sections:
  - Spacing
  - Interleaving
  - Retrieval Practice
  - Elaboration
  - Concrete Examples
  - Dual Coding

evidence_notes: >
  Human-reviewed summary of the relevant findings.

review_status: reviewed
```

The example source metadata must be verified during research ingestion.

## 7.3 Registry Validation

Create automated validation for:

- Missing strategy IDs.
- Duplicate IDs.
- Missing versions.
- Missing descriptions.
- Missing implementation steps.
- Missing limitations.
- Invalid source references.
- Missing source metadata.
- Unreviewed entries being used in production.

The LLM must never invent strategy IDs or research references.

---

# 8. Pedagogy Selection Engine

The selector is responsible for choosing a suitable teaching strategy based on the learner's context.

## 8.1 Input

```json
{
  "topic": "Backpropagation",
  "learning_objective": "Understand the chain rule",
  "learner_level": "beginner",
  "prior_knowledge": [
    "basic_derivatives"
  ],
  "knowledge_gaps": [
    "chain_rule"
  ],
  "misconceptions": [
    "confuses_loss_and_gradient"
  ],
  "recent_performance": [],
  "session_stage": "initial_teaching",
  "time_available_minutes": 20,
  "previous_strategy_outcomes": []
}
```

## 8.2 Expected Output

```json
{
  "primary_strategy": "small_step_instruction",
  "supporting_strategies": [
    "concrete_examples",
    "worked_examples",
    "guided_practice"
  ],
  "sequence": [
    "Explain the prerequisite concept",
    "Present a concrete example",
    "Demonstrate a worked example",
    "Ask a guided practice question"
  ],
  "success_signals": [
    "correct_explanation",
    "independent_application"
  ],
  "fallback_strategy": "additional_prerequisite_instruction",
  "rationale": "The learner has a prerequisite knowledge gap.",
  "registry_version": "1.0"
}
```

The values above are illustrative, not a fixed selection for every learner.

## 8.3 Initial Selection Policies

| Learner situation | Initial policy hypothesis |
|---|---|
| Missing prerequisites | Prerequisite remediation, small steps and concrete examples |
| Partial understanding | Self-explanation and targeted examples |
| Correct answer but weak reasoning | Reasoning prompts and transfer questions |
| Confuses similar concepts | Contrastive examples |
| Forgets previously learned content | Retrieval practice and spaced revision |
| Repeatedly fails | Reduce complexity and investigate misconceptions |
| Strong performance | Fade scaffolding and increase variation |

These policies must be benchmarked and revised using actual learner outcomes.

## 8.4 Selection Requirements

- Only select strategies present in the validated registry.
- Check eligibility conditions.
- Respect avoid/modify conditions.
- Include a rationale.
- Record the strategy and registry versions.
- Provide a safe fallback.
- Persist the selection decision.
- Make selection reproducible when the inputs and policy version are unchanged.

Start with deterministic policies. Do not rely entirely on unconstrained LLM reasoning.

---

# 9. Research Ingestion Workflow

The product needs a trustworthy research foundation.

Do not implement unrestricted scraping.

## 9.1 Preferred Research Sources

Prioritize:

1. Open-access peer-reviewed reviews and meta-analyses.
2. National academies and government educational research.
3. University educational resources.
4. Open educational resources.
5. Official publisher pages and bibliographic records.
6. Practitioner resources, clearly labelled as such.

## 9.2 Ingestion Process

```text
Discover Source
      |
      v
Verify Bibliographic Metadata
      |
      v
Check Access and Licensing
      |
      v
Extract Relevant Sections
      |
      v
Generate Original Summary
      |
      v
Human Review
      |
      v
Record Evidence and Limitations
      |
      v
Link to Pedagogy Strategy
```

## 9.3 Copyright and Research Integrity

- Do not scrape full copyrighted books or paywalled papers without permission.
- Do not reproduce entire chapters or substantial portions of research papers.
- Store source metadata and concise original summaries.
- Preserve source URLs, DOI, authors, publication year and relevant locators.
- Distinguish research findings from practitioner recommendations.
- Distinguish research evidence from product assumptions.
- Do not invent quotations, DOI values, effect sizes or citations.
- Require human review before a research summary influences production strategy selection.

---

# 10. Gemini API Integration and Model Strategy

**Total API budget: USD $20.**

The product must support model verification against the actual configured API key.

Do not hardcode an assumed model ID.

A model appearing in documentation or a model-list endpoint does not automatically prove that the configured key can successfully generate content with it.

## 10.1 Required Architecture

Create a centralized provider abstraction.

Suggested structure:

```text
ai/
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
```

## 10.2 Model Verification

Build a script:

```text
scripts/check_gemini_models.py
```

It should:

1. Read the API key from backend environment variables.
2. Fetch the models available to the configured key.
3. Record supported generation capabilities.
4. Attempt a small real generation request for candidate models.
5. Test structured output where supported.
6. Record latency and usage information.
7. Report errors separately.
8. Never print the API key.

Differentiate:

- Invalid API key.
- Permission denied.
- Model not found.
- Unsupported operation.
- Quota exceeded.
- Rate limiting.
- Timeout.
- Network failure.

## 10.3 Model Routing

Do not assign model names until actual access and task quality are verified.

The initial routing policy should consider:

| Task | Required capability |
|---|---|
| Classification | Reliable structured classification |
| Diagnostics | Reasoning and structured output |
| Learning planning | Multi-step reasoning |
| Teaching | Clear explanations and instruction following |
| Evaluation | Consistent rubric-based assessment |
| Simple feedback | Low latency and low cost |

Choose the cheapest model that passes the task-specific quality benchmark.

A single model may initially handle multiple tasks.

## 10.4 Budget Allocation

| Activity | Budget |
|---|---:|
| Model listing and smoke tests | $1 |
| Development and debugging | $3 |
| Diagnostic and teaching experiments | $5 |
| Evaluation and benchmarks | $5 |
| End-to-end demo | $4 |
| Reserve | $2 |
| **Total** | **$20** |

These are spending limits, not guaranteed API charges.

## 10.5 Budget Protection

- All Gemini requests must pass through one backend client.
- Enforce an internal hard spending ceiling of $20.
- Record model, task, token usage, latency and request status.
- Use bounded output token limits.
- Limit retries.
- Do not repeatedly retry invalid keys or quota errors.
- Use mock responses during routine tests.
- Maintain an internal reserve.
- Never commit API keys.
- Never expose API keys to the frontend.
- Treat provider billing as the authoritative cost source; internal cost calculations are estimates.

---

# 11. Suggested Repository Structure

Adapt this to the existing repository instead of creating unnecessary empty directories.

```text
personal-intelligence/
│
├── apps/
│   └── web/
│
├── services/
│   └── api/
│       └── app/
│           ├── api/
│           ├── ai/
│           │   ├── providers/
│           │   ├── prompts/
│           │   └── schemas/
│           │
│           ├── learner/
│           ├── diagnostics/
│           ├── planner/
│           │
│           ├── pedagogy/
│           │   ├── registry/
│           │   └── policies/
│           │
│           ├── teaching/
│           ├── evaluation/
│           ├── retention/
│           ├── workflows/
│           ├── core/
│           ├── db/
│           └── models/
│
├── research/
│   ├── sources/
│   ├── strategies/
│   └── reviews/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── ai/
│   ├── pedagogy/
│   └── e2e/
│
├── scripts/
│
├── docs/
│
├── infrastructure/
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

# 12. Phase-by-Phase Development Roadmap

**IMPORTANT: Implement one phase at a time. Do not allow the coding agent to implement the entire roadmap in one pass.**

Every phase has:

- Objective.
- Implementation scope.
- Deliverables.
- Acceptance criteria.
- Required tests.
- Completion gate.

The next phase begins only after the current phase is reviewed and explicitly approved.

---

# PHASE 0 — Project Foundation

## Objective

Establish a reliable application foundation before introducing AI functionality.

## Implementation

1. Inspect the existing repository.
2. Identify existing frontend, backend and database code.
3. Set up frontend and backend communication.
4. Configure PostgreSQL.
5. Configure environment variables.
6. Implement database migrations.
7. Implement health endpoints.
8. Configure structured logging.
9. Create initial learner, topic and learning-session persistence.
10. Configure Docker Compose.
11. Document setup and execution.

## Deliverables

- Running frontend.
- Running FastAPI backend.
- PostgreSQL integration.
- Initial database schema.
- Docker Compose configuration.
- `.env.example`.
- Health endpoint.
- Structured logs.
- README with setup instructions.
- Basic automated tests.

## Acceptance Tests

- [x] Frontend starts successfully.
- [x] Backend starts successfully.
- [x] Frontend communicates with backend.
- [x] Database connection succeeds.
- [x] Migrations work from a clean database.
- [x] Health endpoint accurately reports service health.
- [x] Learner records can be created and retrieved.
- [x] Learning sessions can be created and retrieved.
- [x] Existing sessions can be resumed.
- [x] Automated tests pass.
- [x] No secrets are committed.
- [x] Documentation matches actual implementation.

## Phase Gate

Do not introduce Gemini, agents or pedagogy until Phase 0 is approved.

---

# PHASE 1 — Gemini Integration and Model Verification

## Objective

Verify which models are actually accessible with the configured Gemini API key and establish a controlled AI integration layer.

## Implementation

1. Create the provider abstraction.
2. Implement Gemini provider.
3. Implement mock provider.
4. Fetch available model information.
5. Test actual generation with candidate models.
6. Test structured output.
7. Measure latency and usage.
8. Implement timeout handling.
9. Implement bounded retry handling.
10. Implement usage tracking.
11. Implement internal budget enforcement.

## Deliverables

- Gemini provider.
- Provider interface.
- Mock provider.
- Model verification script.
- Model capability report.
- `GEMINI_MODEL_STRATEGY.md`.
- Usage tracker.
- Budget guard.
- Integration tests.

## Acceptance Tests

- [ ] API key is read only from backend configuration.
- [ ] Available model information is retrieved.
- [ ] Candidate models undergo actual generation tests.
- [ ] Structured output is validated.
- [ ] Model access failures are clearly classified.
- [ ] Timeout and network failures are handled.
- [ ] API keys never appear in logs.
- [ ] Usage is recorded.
- [ ] Budget guard blocks requests after the internal limit.
- [ ] Mock provider supports routine tests.
- [ ] Only verified models are marked as usable.

## Phase Gate

Do not start AI teaching workflows until model access, output validation and budget controls pass.

---

# PHASE 2 — Learner Intelligence

## Objective

Create a persistent representation of the learner's knowledge and learning history.

## Implementation

Create:

- Learner profile.
- Learning goals.
- Topic-level knowledge records.
- Learning preferences.
- Assessment history.
- Previous learning activities.
- Misconception records.
- Evidence and confidence metadata.

Distinguish:

**Observed:** Directly demonstrated by learner responses.

**Inferred:** Estimated from available evidence.

Do not treat inferred knowledge as confirmed fact.

## Deliverables

- Learner data model.
- Database migrations.
- Learner APIs.
- Knowledge history.
- Profile update functionality.
- Basic learner dashboard.
- Unit and integration tests.

## Acceptance Tests

- [ ] Learner profiles persist.
- [ ] Knowledge records are topic-specific.
- [ ] Assessment history is retained.
- [ ] Observed and inferred knowledge are distinguishable.
- [ ] Confidence information is persisted.
- [ ] Learner corrections update the profile.
- [ ] One learner cannot access another learner's records.
- [ ] Relevant history can be retrieved for a session.
- [ ] Restarting the application does not lose data.

## Phase Gate

Approve the learner data model before implementing diagnostics.

---

# PHASE 3 — Diagnostic Engine

## Objective

Determine what the learner understands before teaching.

## Implementation

1. Define learning objectives.
2. Define prerequisite concepts.
3. Generate targeted diagnostic questions.
4. Support different question formats.
5. Evaluate answers and reasoning separately.
6. Identify possible misconceptions.
7. Estimate confidence.
8. Save diagnostic evidence.

## Deliverables

- Diagnostic service.
- Learning objective schema.
- Question schema.
- Diagnostic prompts.
- Response evaluator.
- Misconception records.
- Diagnostic report.
- Benchmark scenarios.

## Acceptance Tests

- [ ] Diagnostic questions align with learning objectives.
- [ ] Beginner learners can be distinguished from partially knowledgeable learners.
- [ ] Answers and reasoning are evaluated separately.
- [ ] Partial understanding is recognized.
- [ ] Misconception hypotheses include supporting evidence.
- [ ] Uncertain conclusions remain uncertain.
- [ ] Invalid model output is rejected.
- [ ] Diagnostic results persist.
- [ ] Human-reviewed benchmark cases pass agreed thresholds.

## Phase Gate

Do not create learning plans until diagnostic outputs are reliable enough for the pilot.

---

# PHASE 4 — Learning Planner

## Objective

Create prerequisite-aware personalized learning plans.

## Implementation

1. Decompose topics into concepts.
2. Define learning objectives.
3. Define prerequisite relationships.
4. Identify the learner's starting point.
5. Build a learning sequence.
6. Define completion criteria.
7. Update the plan when new evidence appears.

## Deliverables

- Topic decomposition model.
- Prerequisite graph.
- Learning plan service.
- Learning activity model.
- Plan progress tracking.
- Progress UI.

## Acceptance Tests

- [ ] Every learning step has an objective.
- [ ] Prerequisites are respected.
- [ ] Missing prerequisite knowledge changes the starting point.
- [ ] Concepts are not skipped without supporting evidence.
- [ ] Invalid dependency cycles are detected.
- [ ] Plan progress is persisted.
- [ ] Plans can be revised after new diagnostic evidence.

## Phase Gate

Approve the planner before adding pedagogy selection.

---

# PHASE 5 — Research Library and Pedagogy Registry

## Objective

Build a versioned, evidence-linked library of teaching strategies.

## Implementation

1. Create research source schema.
2. Create strategy schema.
3. Add the initial P0 strategies.
4. Add source references.
5. Record limitations and suitable contexts.
6. Implement registry validation.
7. Implement strategy versioning.
8. Require human review.

Start with curated references, not unrestricted scraping.

## Deliverables

- Research source registry.
- Pedagogy strategy registry.
- Initial P0 strategy definitions.
- Registry validator.
- Source metadata.
- Research ingestion documentation.
- Human review checklist.

## Acceptance Tests

- [ ] Every P0 strategy has a stable ID.
- [ ] Every strategy has a version.
- [ ] Required fields are present.
- [ ] Source references resolve to valid registry entries.
- [ ] Bibliographic metadata is verified.
- [ ] Access and licensing information is recorded.
- [ ] Unreviewed strategies cannot be selected in production.
- [ ] Invalid entries fail validation.
- [ ] No unauthorized copyrighted content is stored.
- [ ] LLM-generated research summaries receive human review.

## Phase Gate

Do not implement the selector against an unstable strategy registry.

---

# PHASE 6 — Pedagogy Selection Engine

## Objective

Select teaching strategies based on learner context, learning objectives and available evidence.

## Implementation

1. Define typed selector inputs.
2. Implement eligibility checks.
3. Implement deterministic selection policies.
4. Implement strategy ranking.
5. Implement sequence generation.
6. Generate selection rationale.
7. Add safe fallback.
8. Record registry and policy versions.
9. Build benchmark scenarios.

## Deliverables

- Pedagogy selector.
- Eligibility engine.
- Selection policies.
- Ranking logic.
- Selection audit records.
- Benchmark dataset.
- Automated tests.

## Acceptance Tests

- [ ] Only registered strategies can be selected.
- [ ] Learner context affects selection.
- [ ] Ineligible strategies are rejected.
- [ ] Limitations are respected.
- [ ] Repeated failures trigger an alternative approach.
- [ ] Strong performance can reduce instructional support.
- [ ] Selection rationale is linked to evidence and learner context.
- [ ] Safe fallback exists.
- [ ] Selection is reproducible under unchanged inputs and policy versions.
- [ ] Selection decisions persist.

## Phase Gate

Review benchmark results before allowing the selector to control real teaching sessions.

---

# PHASE 7 — Teaching Engine

## Objective

Execute the selected teaching strategies through structured learning activities.

## Implementation

1. Generate structured lesson plans.
2. Generate concept explanations.
3. Generate concrete examples.
4. Generate worked examples.
5. Generate guided practice.
6. Add independent practice.
7. Add checks for understanding.
8. Add self-explanation activities.
9. Implement hint fading.
10. Persist teaching progress.

## Teaching Flow Example

```text
Learning Objective
        |
        v
Explain Prerequisite
        |
        v
Concrete Example
        |
        v
Worked Example
        |
        v
Guided Practice
        |
        v
Self-Explanation
        |
        v
Independent Practice
        |
        v
Evaluation
```

This is an example sequence. The selector should determine whether it is appropriate.

## Deliverables

- Teaching service.
- Lesson schema.
- Activity schema.
- Prompt templates.
- Teaching session UI.
- Hint system.
- Teaching history.
- Automated tests.

## Acceptance Tests

- [ ] Teaching content aligns with learning objectives.
- [ ] Selected strategies are actually executed.
- [ ] Activities are structured and not just conversational paragraphs.
- [ ] Explanations include relevant examples.
- [ ] Understanding checks occur during instruction.
- [ ] Hints do not reveal the complete answer immediately.
- [ ] Support can gradually fade.
- [ ] Learner struggles influence subsequent activities.
- [ ] Sessions persist and resume.
- [ ] Human reviewers evaluate factuality and teaching quality.

## Phase Gate

Approve teaching quality before integrating mastery decisions.

---

# PHASE 8 — Evaluation and Adaptation Engine

## Objective

Determine whether the learner genuinely understands the concept and adapt instruction accordingly.

## Implementation

1. Generate objective-aligned assessments.
2. Define evaluation rubrics.
3. Evaluate correctness.
4. Evaluate reasoning.
5. Support partial credit.
6. Identify misconceptions.
7. Provide actionable feedback.
8. Determine the next workflow state.
9. Select remediation when needed.
10. Reassess after remediation.

## Evaluation Dimensions

- Answer correctness.
- Reasoning quality.
- Conceptual understanding.
- Independent application.
- Transfer to unfamiliar problems.
- Confidence and uncertainty.

Confidence should not replace demonstrated understanding.

## Decision Logic

```text
Evaluation
    |
    +-- Strong evidence --> MASTERED
    |
    +-- Partial evidence --> REMEDIATION
    |
    +-- Weak reasoning --> FURTHER ASSESSMENT
    |
    +-- Ambiguous result --> NEEDS_REVIEW
```

## Deliverables

- Evaluation service.
- Assessment generator.
- Rubric definitions.
- Feedback generator.
- Adaptation policies.
- Mastery records.
- Human-reviewed evaluation benchmark.

## Acceptance Tests

- [ ] Correct answer with weak reasoning does not automatically prove mastery.
- [ ] Partial credit is supported.
- [ ] Feedback explains missing understanding.
- [ ] Misconception detection includes supporting evidence.
- [ ] Ambiguous evaluation does not force mastery.
- [ ] Remediation can choose a different teaching strategy.
- [ ] Reassessment is supported.
- [ ] State transitions are valid and persistent.
- [ ] Evaluation quality is compared with human raters.

## Phase Gate

Approve evaluation reliability before implementing retention scheduling.

---

# PHASE 9 — Retention and Learning Progress

## Objective

Ensure the system measures whether learners remember and can apply concepts over time.

## Implementation

1. Implement deterministic revision scheduling.
2. Identify due concepts.
3. Generate retrieval assessments.
4. Evaluate delayed recall.
5. Update mastery records.
6. Track retention history.
7. Support missed revisions.
8. Display upcoming revisions.
9. Support session resume.

## Deliverables

- Retention scheduler.
- Revision records.
- Delayed assessment workflow.
- Mastery history.
- Revision dashboard.
- Integration tests.

## Acceptance Tests

- [ ] Revision dates are calculated correctly.
- [ ] Due revisions are identifiable.
- [ ] Delayed assessments test previously learned objectives.
- [ ] Revision outcomes update mastery records.
- [ ] Failed revision triggers appropriate remediation.
- [ ] Missed revisions are handled.
- [ ] Timezone boundaries are tested.
- [ ] Revision history persists.
- [ ] Learners can resume revision sessions.

## Phase Gate

Approve the retention loop before beginning final product validation.

---

# PHASE 10 — End-to-End Validation and Pilot Release

## Objective

Validate that the complete product actually improves learning.

## Implementation

1. Integrate all modules.
2. Implement end-to-end tests.
3. Create fixed AI benchmark datasets.
4. Create strategy selection benchmarks.
5. Conduct human evaluation.
6. Measure latency.
7. Measure API usage and estimated cost.
8. Conduct security testing.
9. Complete deployment documentation.
10. Run a controlled pilot.

## Deliverables

- End-to-end test suite.
- AI benchmark report.
- Strategy benchmark report.
- Human evaluation report.
- Cost and latency report.
- Security checklist.
- Deployment guide.
- Pilot evaluation report.

## Acceptance Tests

- [ ] A new learner can complete the full learning journey.
- [ ] An unfinished session can be resumed.
- [ ] Diagnostics influence the learning plan.
- [ ] Learning plans influence teaching.
- [ ] Pedagogy selection influences actual teaching activities.
- [ ] Evaluation changes subsequent workflow behavior.
- [ ] Retention assessments can be completed.
- [ ] Learning progress persists.
- [ ] API budget protection works.
- [ ] Authentication and authorization are tested.
- [ ] Privacy and deletion requirements are tested.
- [ ] AI benchmark regressions are detected.
- [ ] Deployment instructions work from a clean environment.

---

# 13. End-to-End Benchmark Scenario

Use backpropagation as the initial fixed benchmark.

## Learner Profile

The learner:

- Understands basic functions.
- Understands basic derivatives.
- Has difficulty with the chain rule.
- Confuses loss and gradient.
- Has not learned backpropagation.

## Expected Workflow

### Step 1: Topic Selection

Learner selects:

`Backpropagation`

### Step 2: Diagnosis

The system identifies:

- Basic derivative knowledge.
- Chain rule weakness.
- Confusion between loss and gradient.

### Step 3: Learning Plan

The planner places chain-rule remediation before backpropagation.

### Step 4: Strategy Selection

The selector considers:

- Small-step instruction.
- Concrete examples.
- Worked examples.
- Guided practice.

### Step 5: Teaching

The learner receives:

- Prerequisite explanation.
- Worked examples.
- Practice questions.
- Self-explanation prompts.

### Step 6: Evaluation

The evaluator checks:

- Correctness.
- Reasoning.
- Application.
- Understanding of gradients.

### Step 7: Adaptation

If the learner struggles:

- Identify the specific misconception.
- Reduce complexity.
- Select an alternative teaching strategy.
- Reassess.

### Step 8: Mastery

The learner solves a new problem independently.

The system records mastery only when sufficient evidence exists.

### Step 9: Retention

The system schedules a later retrieval assessment.

### Step 10: Return

The learner returns and completes the delayed assessment.

The system updates retention and mastery records.

## Additional Benchmark Variants

- Complete beginner.
- Partial prerequisite knowledge.
- Correct answer but weak reasoning.
- Persistent misconception.
- Initial success followed by forgetting.
- Strong performance on unfamiliar problems.

---

# 14. Evaluation Framework

A functioning application does not automatically mean a functioning AI Teacher.

Evaluate it at three levels.

## 14.1 Technical Evaluation

| Metric | What it measures |
|---|---|
| Workflow completion | Whether the learning journey completes |
| Session recovery | Whether interrupted sessions resume |
| Schema validity | Whether model responses match required schemas |
| Failure rate | Model and application failures |
| Latency | Time taken for each operation |
| API cost | Estimated cost per learning session |

## 14.2 Teaching Quality Evaluation

| Metric | What it measures |
|---|---|
| Factuality | Accuracy of explanations |
| Objective alignment | Whether instruction addresses the objective |
| Strategy selection | Whether selected strategy fits the context |
| Strategy fidelity | Whether the strategy is actually executed |
| Feedback quality | Whether feedback helps the learner improve |
| Misconception precision | Whether identified misconceptions are correct |
| Human agreement | Agreement between AI and human evaluators |

## 14.3 Learning Outcome Evaluation

| Metric | What it measures |
|---|---|
| Pre-test score | Starting knowledge |
| Post-test score | Immediate learning |
| Transfer score | Application to new problems |
| Delayed retention | Knowledge retained after a delay |
| Misconception correction | Whether incorrect understanding changes |
| Completion rate | Whether learners complete learning activities |

## 14.4 Pilot Comparison

Compare:

**Group A:** Conventional LLM chatbot.

**Group B:** Adaptive AI Teacher.

Keep topics, starting levels, available time and assessments as comparable as possible.

Measure:

- Pre-test.
- Post-test.
- Novel problem transfer.
- Delayed retention.
- Learner-reported clarity.

Report sample size, participant characteristics, topics, assessment conditions and uncertainty.

A small pilot provides directional evidence, not proof of universal effectiveness.

---

# 15. Starter Research References

These are initial references for the research library. They are not a complete systematic review.

Verify each source's access conditions, relevance and bibliographic details before using it in production.

## 15.1 Learning Science

### 1. Teaching the Science of Learning

Weinstein, Y., Madan, C. R., & Sumeracki, M. A. (2018).

*Cognitive Research: Principles and Implications, 3*, 2.

Covers spacing, interleaving, retrieval practice, elaboration, concrete examples and dual coding.

- Article: https://link.springer.com/article/10.1186/s41235-017-0087-y
- DOI: https://doi.org/10.1186/s41235-017-0087-y
- PubMed: https://pubmed.ncbi.nlm.nih.gov/29399621/

### 2. Improving Students' Learning With Effective Learning Techniques

Dunlosky, J., et al. (2013).

*Psychological Science in the Public Interest, 14*(1), 4–58.

Reviews the effectiveness of several learning techniques.

- DOI: https://doi.org/10.1177/1529100612453266
- PubMed: https://pubmed.ncbi.nlm.nih.gov/26173288/

### 3. The Science of Effective Learning With Spacing and Retrieval Practice

Carpenter, S. K., Pan, S. C., & Butler, A. C. (2022).

*Nature Reviews Psychology, 1*, 496–511.

- Article: https://www.nature.com/articles/s44159-022-00089-1
- DOI: https://doi.org/10.1038/s44159-022-00089-1

## 15.2 Instruction and Scaffolding

### 4. Principles of Instruction: Research-Based Strategies That All Teachers Should Know

Rosenshine, B. (2012).

*American Educator, 36*(1), 12–19, 39.

- Article: https://www.aft.org/ae/spring2012/rosenshine
- PDF: https://www.aft.org/sites/default/files/Rosenshine.pdf

### 5. The Role of Tutoring in Problem Solving

Wood, D., Bruner, J. S., & Ross, G. (1976).

*Journal of Child Psychology and Psychiatry, 17*(2), 89–100.

- DOI: https://doi.org/10.1111/j.1469-7610.1976.tb00381.x
- PubMed: https://pubmed.ncbi.nlm.nih.gov/932126/

### 6. Cognitive Load During Problem Solving: Effects on Learning

Sweller, J. (1988).

*Cognitive Science, 12*(2), 257–285.

- DOI: https://doi.org/10.1207/s15516709cog1202_4
- Publisher: https://onlinelibrary.wiley.com/doi/10.1207/s15516709cog1202_4

## 15.3 Multimedia Learning

### 7. Multimedia Learning

Mayer, R. E. (2022).

*Oxford Handbook of Educational Psychology.*

- Reference: https://academic.oup.com/edited-volume/35466/chapter-abstract/337856136
- DOI: https://doi.org/10.1093/oxfordhb/9780199841332.013.18

### 8. The Cambridge Handbook of Multimedia Learning

Edited by Richard E. Mayer and related contributors.

- Book: https://www.cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/
- Multimedia Principle chapter: https://www.cambridge.org/core/books/abs/cambridge-handbook-of-multimedia-learning/multimedia-principle/D09A773C7C5C214FA19D4C9841FBC83B

## 15.4 Formative Assessment and Mastery

### 9. Assessment and Classroom Learning

Black, P., & Wiliam, D. (1998).

*Assessment in Education, 5*(1), 7–74.

- DOI: https://doi.org/10.1080/0969595980050102
- PDF: https://www.gla.ac.uk/t4/learningandteaching/files/PGCTHE/BlackandWiliam1998.pdf

### 10. How People Learn II: Learners, Contexts, and Cultures

National Academies of Sciences, Engineering, and Medicine (2018).

- Book: https://nap.nationalacademies.org/catalog/24783/how-people-learn-ii-learners-contexts-and-cultures
- DOI: https://doi.org/10.17226/24783

### 11. Learning for Mastery

Bloom, B. S. (1968).

*Evaluation Comment, 1*(2).

- ERIC: https://eric.ed.gov/?id=ED053419

---

# 16. Development Rules for Cursor Agent

The following instructions must be given to Cursor before implementation.

## Cursor Agent System Instructions

```text
You are the implementation engineer for the Research-Backed AI Teacher MVP.

Your responsibility is to build the product described in this roadmap.

STRICT DEVELOPMENT RULES:

1. Read the complete roadmap before implementing anything.

2. Inspect the existing repository before making changes.

3. Implement only the phase explicitly approved by the product owner.

4. Before coding, explain:
   - Existing architecture.
   - Proposed architecture.
   - Files to be created or modified.
   - Dependencies.
   - Database changes.
   - Acceptance tests.

5. Do not begin implementation until the proposed plan is reviewed.

6. Never silently skip acceptance criteria.

7. Never claim completion merely because code was generated.

8. Run actual tests and report exact commands and results.

9. Use mocks for routine AI tests.

10. Protect the USD $20 Gemini API budget.

11. Verify Gemini model availability using the actual configured API key.

12. Never expose API keys or secrets.

13. Validate all LLM outputs using typed schemas.

14. Never allow an LLM to invent strategy IDs, citations, DOIs or evidence.

15. Respect research access, licensing and copyright.

16. Do not scrape entire copyrighted books or paywalled papers.

17. Preserve research provenance and strategy versioning.

18. Use deterministic code for:
    - Database persistence.
    - State transitions.
    - Revision scheduling.
    - Authorization.
    - Budget enforcement.

19. Avoid unnecessary agents, frameworks and microservices.

20. Update documentation and migrations alongside implementation.

21. At the end of each phase, provide:
    - Deliverables completed.
    - Files changed.
    - Architecture decisions.
    - Exact tests executed.
    - Test results.
    - Acceptance checklist.
    - Known limitations.
    - API calls and estimated cost.
    - Reproducible demo instructions.
    - Remaining work.

22. STOP after completing a phase.

23. Wait for explicit product-owner approval before starting the next phase.

DO NOT IMPLEMENT THE ENTIRE ROADMAP IN ONE PASS.

YOUR FIRST TASK:

Inspect the repository and prepare a detailed implementation proposal for PHASE 0 ONLY.

Do not write implementation code until the proposal is approved.
```

---

# 17. Phase Approval Template

Use this template after every phase.

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

Do not begin the next phase without explicit approval.
```

---

# 18. Definition of MVP Complete

The AI Teacher MVP is complete only when all the following are demonstrated.

## Learner Intelligence

- [ ] Learners can create and resume learning journeys.
- [ ] Learner knowledge and history persist.
- [ ] Observed and inferred knowledge are distinguishable.

## Diagnosis and Planning

- [ ] The system diagnoses knowledge gaps.
- [ ] Misconceptions have supporting evidence.
- [ ] Learning plans respect prerequisites.
- [ ] Learning plans adapt to new evidence.

## Pedagogy

- [ ] P0 strategies have validated registry entries.
- [ ] Strategies have source references and limitations.
- [ ] The selector uses learner context.
- [ ] The selector avoids ineligible strategies.
- [ ] Strategy selection is auditable.

## Teaching and Evaluation

- [ ] Teaching executes selected strategies.
- [ ] Learners receive structured activities.
- [ ] Evaluation assesses reasoning and application.
- [ ] The system changes strategy when learners struggle.
- [ ] Mastery decisions use sufficient evidence.

## Retention

- [ ] Revision can be scheduled.
- [ ] Delayed assessments can be completed.
- [ ] Mastery and retention history persist.

## Engineering

- [ ] Gemini access is verified.
- [ ] API usage and costs are tracked.
- [ ] The $20 internal budget ceiling is enforced.
- [ ] Automated tests pass.
- [ ] End-to-end tests pass.
- [ ] Security and privacy requirements are tested.
- [ ] Documentation is complete.
- [ ] A controlled pilot has been conducted.

---

# 19. Immediate Starting Instructions

Do not start with model experimentation, multi-agent architecture or sophisticated pedagogy selection.

Start with Phase 0.

### Your first development session

1. Create the project repository.
2. Save this document as `AI_TEACHER_MVP_ROADMAP.md`.
3. Open the repository in Cursor.
4. Give Cursor the instructions from Section 16.
5. Ask it to inspect the repository.
6. Review its Phase 0 proposal.
7. Approve or request changes.
8. Implement Phase 0.
9. Run the acceptance tests.
10. Review the completion report.
11. Lock Phase 0 before moving to Phase 1.

**Development philosophy:**

Build a working system, not a collection of AI agents.

Every module must have a clear responsibility, measurable output and testable behavior.

Every phase must leave the application in a working state.

Every teaching decision should be explainable and auditable.

Most importantly, the final product must demonstrate that learners are actually learning—not merely that the AI is generating impressive explanations.

---

**END OF ROADMAP**
