from __future__ import annotations
import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
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
    worker_prefetch_multiplier=1, # Fair scheduling
    result_expires=86400,         # Results expire after 24h
    broker_connection_retry_on_startup=True,
)
