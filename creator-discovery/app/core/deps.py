from typing import Generator

from sqlmodel import Session

from app.db.session import get_session as _get_session


def get_db() -> Generator[Session, None, None]:
    yield from _get_session()
