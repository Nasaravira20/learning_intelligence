from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import clear_session_cookie, require_user, set_session_cookie
from app.core.security import COOKIE_NAME
from app.db.session import get_db
from app.models import User
from app.schemas.auth import AccountRead, SigninRequest, SignupRequest
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AccountRead, status_code=201)
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)) -> AccountRead:
    user = auth_service.signup(db, payload.display_name, payload.email, payload.password)
    token = auth_service.open_auth_session(db, user.id)
    set_session_cookie(response, token)
    return auth_service.to_account(user)


@router.post("/signin", response_model=AccountRead)
def signin(payload: SigninRequest, response: Response, db: Session = Depends(get_db)) -> AccountRead:
    user = auth_service.signin(db, payload.email, payload.password)
    token = auth_service.open_auth_session(db, user.id)
    set_session_cookie(response, token)
    return auth_service.to_account(user)


@router.post("/signout")
def signout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    token = request.cookies.get(COOKIE_NAME, "")
    if token:
        auth_service.revoke_auth_session(db, token)
    clear_session_cookie(response)
    return {"status": "signed_out"}


@router.delete("/account")
def delete_account(response: Response, db: Session = Depends(get_db), user: User = Depends(require_user)) -> dict[str, str]:
    auth_service.delete_account(db, user)
    clear_session_cookie(response)
    return {"status": "deleted"}


@router.get("/me", response_model=AccountRead)
def me(user: User = Depends(require_user)) -> AccountRead:
    return auth_service.to_account(user)
