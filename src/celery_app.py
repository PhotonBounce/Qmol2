from __future__ import annotations
import os

try:
    from celery import Celery
    _celery_available = True
except ModuleNotFoundError:
    _celery_available = False

    class _DummyCelery:
        """Dummy Celery app that provides a pass-through task decorator."""

        @staticmethod
        def task(*args, **kwargs):
            bind = kwargs.get('bind', False)
            def decorator(func):
                if bind:
                    class _MockSelf:
                        class request:
                            retries = 0
                            is_eager = True
                    def wrapper(*args, **kwargs):
                        return func(_MockSelf(), *args, **kwargs)
                    wrapper.delay = wrapper
                    wrapper.apply_async = wrapper
                    wrapper.apply = lambda args=None, kwargs=None, **kw: func(_MockSelf(), *(args or ()), **(kwargs or {}))
                    return wrapper
                else:
                    func.delay = func
                    func.apply_async = func
                    func.apply = lambda args=None, kwargs=None, **kw: func(*(args or ()), **(kwargs or {}))
                    return func
            if args and callable(args[0]):
                return decorator(args[0])
            return decorator

        def send_task(self, *args, **kwargs):
            raise RuntimeError("Celery is not configured")

        @property
        def tasks(self):
            return {}

    app = _DummyCelery()  # type: ignore


def _configure_for_testing():
    """Configure the Celery app for synchronous test execution (no broker)."""
    if _celery_available:
        try:
            app.conf.task_always_eager = True
            app.conf.task_store_eager_result = True
        except Exception:
            pass


if _celery_available:
    import config

    app = Celery(
        "qmol",
        broker=config.REDIS_URL,
        backend=config.REDIS_URL,
        include=["src.tasks"],
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "3600")),
        task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "3300")),
        worker_prefetch_multiplier=1,
        result_expires=86400,
        broker_connection_retry_on_startup=True,
    )
