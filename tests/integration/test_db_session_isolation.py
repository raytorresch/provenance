from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import get_sqlalchemy_url
from app.models.rag import Document


def test_commit_inside_session_does_not_escape_rollback() -> None:
    # Reproduces the db_session fixture by hand so we can inspect state
    # *after* its teardown, which the fixture itself can't do for us.
    engine = create_engine(get_sqlalchemy_url())
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    document = Document(
        adr_code="ADR-TEST-COMMIT-ESCAPE",
        title="Isolation test ADR",
        source_url="https://example.com/adr/commit-escape",
        content_hash="test-hash-commit-escape",
    )
    session.add(document)
    session.commit()  # mimics code under test committing mid-transaction

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()
    engine.dispose()

    verify_engine = create_engine(get_sqlalchemy_url())
    with verify_engine.connect() as verify_connection, Session(
        bind=verify_connection
    ) as verify_session:
        stmt = select(Document).where(Document.adr_code == "ADR-TEST-COMMIT-ESCAPE")
        assert verify_session.scalars(stmt).first() is None
    verify_engine.dispose()
