from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.session import get_db
from app.models import User
from app.schemas.learner import (
    ActivityCreate,
    ActivityRead,
    AssessmentCreate,
    AssessmentRead,
    GoalCreate,
    GoalRead,
    GoalUpdate,
    KnowledgeCorrection,
    KnowledgeCreate,
    KnowledgeRead,
    LearnerDashboard,
    MisconceptionCorrection,
    MisconceptionCreate,
    MisconceptionRead,
    PreferenceRead,
    PreferenceWrite,
    ProfileRead,
    ProfileUpdate,
)
from app.services import learner_intelligence as intelligence

router = APIRouter(prefix="/learner", tags=["learner"])


def _learner_id(user: User) -> UUID:
    return user.profile.id


@router.get("", response_model=LearnerDashboard)
def get_dashboard(db: Session = Depends(get_db), user: User = Depends(require_user)) -> LearnerDashboard:
    return intelligence.dashboard(db, user.profile)


@router.patch("/profile", response_model=ProfileRead)
def patch_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ProfileRead:
    profile = intelligence.update_profile(db, user.profile, payload)
    return ProfileRead.model_validate(profile)


@router.put("/preferences", response_model=PreferenceRead)
def put_preferences(
    payload: PreferenceWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> PreferenceRead:
    row = intelligence.save_preferences(db, _learner_id(user), payload)
    return PreferenceRead.model_validate(row)


@router.post("/goals", response_model=GoalRead, status_code=201)
def post_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> GoalRead:
    return GoalRead.model_validate(intelligence.create_goal(db, _learner_id(user), payload))


@router.patch("/goals/{goal_id}", response_model=GoalRead)
def patch_goal(
    goal_id: UUID,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> GoalRead:
    return GoalRead.model_validate(intelligence.update_goal(db, _learner_id(user), goal_id, payload))


@router.get("/knowledge", response_model=list[KnowledgeRead])
def get_knowledge(
    history: bool = Query(default=False),
    topic_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> list[KnowledgeRead]:
    rows = intelligence.list_knowledge(db, _learner_id(user), topic_id=topic_id, history=history)
    return [KnowledgeRead.model_validate(item) for item in rows]


@router.post("/knowledge", response_model=KnowledgeRead, status_code=201)
def post_knowledge(
    payload: KnowledgeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> KnowledgeRead:
    return KnowledgeRead.model_validate(intelligence.record_knowledge(db, _learner_id(user), payload))


@router.patch("/knowledge/{knowledge_id}", response_model=KnowledgeRead)
def patch_knowledge(
    knowledge_id: UUID,
    payload: KnowledgeCorrection,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> KnowledgeRead:
    row = intelligence.correct_knowledge(db, _learner_id(user), knowledge_id, payload)
    return KnowledgeRead.model_validate(row)


@router.get("/misconceptions", response_model=list[MisconceptionRead])
def get_misconceptions(
    history: bool = Query(default=False),
    topic_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> list[MisconceptionRead]:
    rows = intelligence.list_misconceptions(db, _learner_id(user), topic_id=topic_id, history=history)
    return [MisconceptionRead.model_validate(item) for item in rows]


@router.post("/misconceptions", response_model=MisconceptionRead, status_code=201)
def post_misconception(
    payload: MisconceptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> MisconceptionRead:
    return MisconceptionRead.model_validate(intelligence.record_misconception(db, _learner_id(user), payload))


@router.patch("/misconceptions/{misconception_id}", response_model=MisconceptionRead)
def patch_misconception(
    misconception_id: UUID,
    payload: MisconceptionCorrection,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> MisconceptionRead:
    row = intelligence.correct_misconception(db, _learner_id(user), misconception_id, payload)
    return MisconceptionRead.model_validate(row)


@router.get("/assessments", response_model=list[AssessmentRead])
def get_assessments(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> list[AssessmentRead]:
    return [AssessmentRead.model_validate(item) for item in intelligence.list_assessments(db, _learner_id(user))]


@router.post("/assessments", response_model=AssessmentRead, status_code=201)
def post_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> AssessmentRead:
    return AssessmentRead.model_validate(intelligence.record_assessment(db, _learner_id(user), payload))


@router.get("/activities", response_model=list[ActivityRead])
def get_activities(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> list[ActivityRead]:
    return [ActivityRead.model_validate(item) for item in intelligence.list_activities(db, _learner_id(user))]


@router.post("/activities", response_model=ActivityRead, status_code=201)
def post_activity(
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ActivityRead:
    return ActivityRead.model_validate(intelligence.record_activity(db, _learner_id(user), payload))
