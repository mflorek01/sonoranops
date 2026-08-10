from app.chat_limiter import ChatLimiter


def test_limiter_denies_ninth_request_and_releases_concurrency() -> None:
    limiter = ChatLimiter(per_hour=8, max_concurrent=9)
    for _ in range(8):
        assert limiter.acquire("203.0.113.4") is not None
        limiter.release()
    assert limiter.acquire("203.0.113.4") is None


def test_limiter_caps_active_requests() -> None:
    limiter = ChatLimiter(per_hour=8, max_concurrent=2)
    assert limiter.acquire("203.0.113.4") is not None
    assert limiter.acquire("203.0.113.5") is not None
    assert limiter.acquire("203.0.113.6") is None
    limiter.release()
    assert limiter.acquire("203.0.113.6") is not None


def test_limiter_has_process_local_daily_cap() -> None:
    limiter = ChatLimiter(per_hour=8, max_concurrent=2, daily_cap=2)
    for client in ("203.0.113.4", "203.0.113.5"):
        assert limiter.acquire(client) is not None
        limiter.release()
    assert limiter.acquire("203.0.113.6") is None
