import asyncio
import threading
from pathlib import Path
import story_jobs


def test_slow_render_returns_pending_deduplicates_and_publishes(tmp_path):
    async def scenario():
        story_jobs._jobs.clear()
        gate = threading.Event()
        calls = []
        out = tmp_path / 'story.mp4'
        def render(path):
            calls.append(path)
            gate.wait(3)
            path.write_bytes(b'video')
        assert await story_jobs.ensure_story(out, render) is False
        assert await story_jobs.ensure_story(out, render) is False
        assert len(calls) == 1
        gate.set()
        await asyncio.gather(*list(story_jobs._jobs.values()))
        assert await story_jobs.ensure_story(out, render) is True
        assert len(calls) == 1
    asyncio.run(scenario())


def test_render_failure_does_not_publish_a_cached_video(tmp_path):
    async def scenario():
        story_jobs._jobs.clear()
        def fail(path): raise RuntimeError('encoder failure')
        try:
            await story_jobs.ensure_story(tmp_path / 'fail.mp4', fail)
        except RuntimeError:
            pass
        else:
            raise AssertionError('failed encoder must surface')
        assert not (tmp_path / 'fail.mp4').exists()
        story_jobs._jobs.clear()
    asyncio.run(scenario())


def test_atomic_output_preserves_cache_after_failed_encoder(tmp_path, monkeypatch):
    import story_video
    output = tmp_path / 'atomic.mp4'
    def fail(path, *args, **kwargs):
        path.write_bytes(b'incomplete')
        raise RuntimeError('ffmpeg failed')
    monkeypatch.setattr(story_video, '_render_story', fail)
    try:
        story_video.render_story(output)
    except RuntimeError:
        pass
    assert not output.exists()
    assert not list(tmp_path.glob('tmp*'))


def test_story_route_returns_202_while_processing(tmp_path, monkeypatch):
    import os
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
    os.environ.setdefault('DB_NAME', 'rrclub_test')
    import routes_ops, story_video
    monkeypatch.setattr(story_video, 'MEDIA_DIR', tmp_path)
    monkeypatch.setattr(story_jobs, 'ensure_story', AsyncMock(return_value=False))
    monkeypatch.setattr(routes_ops, 'db', SimpleNamespace(
        campaigns=SimpleNamespace(find_one=AsyncMock(return_value={'cupom': 'TEST', 'desconto': 5})),
        partners=SimpleNamespace(find_one=AsyncMock(return_value={})),
        influencers=SimpleNamespace(find_one=AsyncMock(return_value={}))))
    response = asyncio.run(routes_ops.story_video('campaign', {'influencer_id': 'i', 'nome': 'Teste'}))
    assert response.status_code == 202
    assert response.headers['retry-after'] == '2'


def test_story_route_does_not_render_another_influencers_campaign(monkeypatch):
    import routes_ops
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from fastapi import HTTPException
    lookup = AsyncMock(return_value=None)
    monkeypatch.setattr(routes_ops, 'db', SimpleNamespace(campaigns=SimpleNamespace(find_one=lookup)))
    try:
        asyncio.run(routes_ops.story_video('other-campaign', {'influencer_id': 'i', 'nome': 'Teste'}))
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError('foreign campaign should not render')
    assert lookup.call_args.args[0]['influencer_id'] == 'i'
