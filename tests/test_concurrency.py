import asyncio

import pytest

from transfermarkt_api.tfmkt.concurrency import MAX_FAN_OUT_TASKS, gather

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio."""
    return "asyncio"


async def noop() -> str:
    """A trivially successful unit of work."""
    return "ok"


async def test_gather_preserves_input_order() -> None:
    """Results follow input order even when completion order differs."""

    async def delayed(value: int) -> int:
        await asyncio.sleep(0)
        return value

    assert await gather(*(delayed(value) for value in range(5))) == list(range(5))


async def test_gather_rejects_oversized_fan_out() -> None:
    """A batch above the cap fails before scheduling any tasks."""
    with pytest.raises(ValueError, match="fan-out exceeds 1000 tasks"):
        await gather(*(noop() for _ in range(MAX_FAN_OUT_TASKS + 1)))


async def test_gather_accepts_batch_at_the_cap() -> None:
    """A batch exactly at the cap still completes."""
    results = await gather(*(noop() for _ in range(MAX_FAN_OUT_TASKS)))
    assert results == ["ok"] * MAX_FAN_OUT_TASKS
