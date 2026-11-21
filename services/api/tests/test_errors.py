from sqlalchemy.exc import IntegrityError

from app.core.errors import error_payload
from app.core.request_context import reset_request_id, set_request_id
from app.db.errors import translate_integrity_error


class FakeOrig(Exception):
    def __init__(self, sqlstate: str, constraint: str | None) -> None:
        super().__init__("constraint failed")
        self.sqlstate = sqlstate
        self.diag = type("Diag", (), {"constraint_name": constraint})()


def _integrity(sqlstate: str, constraint: str | None) -> IntegrityError:
    return IntegrityError("INSERT INTO learning_topics (slug) VALUES (%(slug)s)", {"slug": "hidden-slug"}, FakeOrig(sqlstate, constraint))


def test_unique_slug_conflict_hides_the_statement() -> None:
    error = translate_integrity_error(_integrity("23505", "uq_learning_topics_slug"))
    assert error.code == "topic_slug_taken"
    assert error.status_code == 409
    assert "hidden-slug" not in error.message


def test_foreign_key_becomes_not_found() -> None:
    error = translate_integrity_error(_integrity("23503", "fk_learning_sessions_learner_id"))
    assert error.code == "related_record_missing"
    assert error.status_code == 404


def test_check_constraint_becomes_validation() -> None:
    error = translate_integrity_error(_integrity("23514", "ck_learner_display_name_not_blank"))
    assert error.code == "validation_error"
    assert error.status_code == 422


def test_error_payload_includes_request_id() -> None:
    token = set_request_id("req-payload")
    try:
        payload = error_payload("learner_not_found", "Learner was not found.")
    finally:
        reset_request_id(token)
    assert payload == {
        "error": {
            "code": "learner_not_found",
            "message": "Learner was not found.",
            "request_id": "req-payload",
        }
    }
