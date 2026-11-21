from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.resources import TopicCreate, TopicRead
from app.services import topics as topic_service

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("", response_model=TopicRead, status_code=201)
def create_topic(payload: TopicCreate, db: Session = Depends(get_db)) -> TopicRead:
    topic = topic_service.create_topic(db, payload.title, payload.slug, payload.description)
    return TopicRead.model_validate(topic)


@router.get("", response_model=list[TopicRead])
def list_topics(db: Session = Depends(get_db)) -> list[TopicRead]:
    return [TopicRead.model_validate(item) for item in topic_service.list_topics(db)]


@router.get("/{topic_id}", response_model=TopicRead)
def get_topic(topic_id: UUID, db: Session = Depends(get_db)) -> TopicRead:
    topic = topic_service.get_topic(db, topic_id)
    return TopicRead.model_validate(topic)
