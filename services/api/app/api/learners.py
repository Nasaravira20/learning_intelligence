from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.resources import LearnerCreate, LearnerRead
from app.services import learners as learner_service

router = APIRouter(prefix="/learners", tags=["learners"])


@router.post("", response_model=LearnerRead, status_code=201)
def create_learner(payload: LearnerCreate, db: Session = Depends(get_db)) -> LearnerRead:
    profile = learner_service.create_learner(db, payload.display_name)
    return LearnerRead.model_validate(profile)


@router.get("", response_model=list[LearnerRead])
def list_learners(db: Session = Depends(get_db)) -> list[LearnerRead]:
    return [LearnerRead.model_validate(item) for item in learner_service.list_learners(db)]


@router.get("/{learner_id}", response_model=LearnerRead)
def get_learner(learner_id: UUID, db: Session = Depends(get_db)) -> LearnerRead:
    profile = learner_service.get_learner(db, learner_id)
    return LearnerRead.model_validate(profile)
