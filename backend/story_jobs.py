"""Bounded, deduplicated local rendering; callers poll instead of holding HTTP open."""
import asyncio
import logging

_jobs = {}
_slots = asyncio.Semaphore(1)
logger = logging.getLogger(__name__)


async def ensure_story(path, render, *args):
    key = str(path)
    if path.exists() and path.stat().st_size:
        return True
    task = _jobs.get(key)
    if task is not None and task.done():
        _jobs.pop(key, None)
        task.result()  # Surface rendering failures; a later request may retry.
        return path.exists() and path.stat().st_size > 0
    if task is None:
        for previous_key, previous_task in list(_jobs.items()):
            if previous_task.done():
                _jobs.pop(previous_key, None)
        if len(_jobs) >= 8:
            from fastapi import HTTPException
            raise HTTPException(429, "Geração de vídeos ocupada. Tente novamente mais tarde.")
        async def work():
            async with _slots:
                await asyncio.to_thread(render, path, *args)
        task = asyncio.create_task(work())
        _jobs[key] = task
        def finished(done):
            # Keep failed jobs for the next request to report, but retrieve errors
            # immediately and free successful slots even if the caller leaves.
            if done.cancelled():
                _jobs.pop(key, None)
            elif done.exception() is None:
                _jobs.pop(key, None)
            else:
                logger.error("Story rendering failed: %s", type(done.exception()).__name__)
        task.add_done_callback(finished)
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=0.15)
    except asyncio.TimeoutError:
        return False
    return path.exists() and path.stat().st_size > 0
