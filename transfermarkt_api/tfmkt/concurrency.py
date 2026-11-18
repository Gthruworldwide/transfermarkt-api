"""Ordered fan-out with cleanup before failures leave the SDK."""

import asyncio
from collections.abc import Awaitable
from inspect import iscoroutine
from typing import Any

MAX_FAN_OUT_TASKS = 1_000


async def gather(*awaitables: Awaitable[Any]) -> list[Any]:
    """Return results in input order, cancelling and awaiting siblings on any failure."""
    if len(awaitables) > MAX_FAN_OUT_TASKS:
        # Never leave a rejected batch of coroutine objects un-awaited.
        for awaitable in awaitables:
            if iscoroutine(awaitable):
                awaitable.close()
        raise ValueError(f"fan-out exceeds {MAX_FAN_OUT_TASKS} tasks")

    tasks = [asyncio.ensure_future(awaitable) for awaitable in awaitables]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
