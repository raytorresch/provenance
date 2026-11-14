from __future__ import annotations

from typing import Self

from app.repositories.health_repository import HealthRepository


class _FakeCursor:
    def __init__(self, result: tuple[int] | None) -> None:
        self._result = result

    async def execute(self, query: str) -> None:
        pass

    async def fetchone(self) -> tuple[int] | None:
        return self._result

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class _FakeConnection:
    def __init__(self, result: tuple[int] | None) -> None:
        self._result = result

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self._result)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class _FailingConnection:
    async def __aenter__(self) -> Self:
        raise RuntimeError("connection failed")

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class _FakePool:
    def __init__(self, result: tuple[int] | None = (1,), fail: bool = False) -> None:
        self._result = result
        self._fail = fail

    def connection(self) -> _FakeConnection | _FailingConnection:
        if self._fail:
            return _FailingConnection()
        return _FakeConnection(self._result)


async def test_ping_returns_false_when_pool_is_not_initialized() -> None:
    repository = HealthRepository(pool=None)

    assert await repository.ping() is False


async def test_ping_returns_true_when_query_succeeds() -> None:
    repository = HealthRepository(pool=_FakePool(result=(1,)))

    assert await repository.ping() is True


async def test_ping_returns_false_when_result_is_unexpected() -> None:
    repository = HealthRepository(pool=_FakePool(result=None))

    assert await repository.ping() is False


async def test_ping_returns_false_when_connection_fails() -> None:
    repository = HealthRepository(pool=_FakePool(fail=True))

    assert await repository.ping() is False
