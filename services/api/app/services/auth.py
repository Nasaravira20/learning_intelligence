from __future__ import annotations

import logging
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError, ConflictError
from app.core.logging import log_event
from app.core.security import hash_password, hash_token, new_session_token, verify_password
from app.core.security import SESSION_DAYS
from app.core.time import utcnow
from app.db.errors import translate_integrity_error
from app.models import AuthSession, LearnerProfile, User
from app.schemas.auth import AccountRead

logger = logging.getLogger(__name__)

_DUMMY_PASSWORD_HASH = hash_password("dummy-password-not-used")


def to_account(user: User) -> AccountRead:
    profile = user.profile
    return AccountRead(
        user_id=user.id,
        email=user.email or "",
        learner_id=profile.id,
        display_name=profile.display_name,
        created_at=user.created_at,
    )


def signup(session: Session, display_name: str, email: str, password: str) -> User:
    existing = session.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        log_event(logger, logging.WARNING, "signup_email_taken")
        raise ConflictError("email_taken", "An account with this email already exists.")

    user = User(id=uuid4(), email=email, password_hash=hash_password(password))
    profile = LearnerProfile(id=uuid4(), user_id=user.id, display_name=display_name)
    user.profile = profile
    session.add(user)
    session.add(profile)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        translated = translate_integrity_error(exc)
        log_event(logger, logging.WARNING, "signup_conflict", code=translated.code)
        raise translated from exc
    log_event(logger, logging.INFO, "account_created", user_id=user.id, learner_id=profile.id)
    return user


def signin(session: Session, email: str, password: str) -> User:
    user = session.scalar(
        select(User).options(joinedload(User.profile)).where(User.email == email)
    )
    password_hash = user.password_hash if user is not None and user.password_hash else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, password_hash)
    if user is None or user.password_hash is None or user.profile is None or not password_matches:
        log_event(logger, logging.WARNING, "signin_failed")
        raise AppError("invalid_credentials", "The email or password is incorrect.", 401)
    log_event(logger, logging.INFO, "signin_succeeded", user_id=user.id)
    return user


def open_auth_session(session: Session, user_id: UUID) -> str:
    token = new_session_token()
    auth_session = AuthSession(
        id=uuid4(),
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=utcnow() + timedelta(days=SESSION_DAYS),
    )
    session.add(auth_session)
    session.flush()
    log_event(logger, logging.INFO, "auth_session_opened", user_id=user_id)
    return token


def revoke_auth_session(session: Session, token: str) -> None:
    token_hash = hash_token(token)
    auth_session = session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if auth_session is None:
        return
    user_id = auth_session.user_id
    session.delete(auth_session)
    session.flush()
    log_event(logger, logging.INFO, "auth_session_revoked", user_id=user_id)


def account_for_token(session: Session, token: str) -> User | None:
    if not token:
        return None
    auth_session = session.scalar(
        select(AuthSession)
        .options(joinedload(AuthSession.user).joinedload(User.profile))
        .where(AuthSession.token_hash == hash_token(token))
    )
    if auth_session is None:
        return None
    if auth_session.expires_at <= utcnow():
        session.delete(auth_session)
        session.flush()
        log_event(logger, logging.INFO, "auth_session_expired", user_id=auth_session.user_id)
        return None
    user = auth_session.user
    if user.profile is None:
        return None
    return user
