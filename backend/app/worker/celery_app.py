"""Celery application instance (broker/result backend from settings)."""
from __future__ import annotations

import ssl

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "codeatreus",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

# TLS brokers (rediss://, e.g. Upstash) require explicit SSL options or Celery
# refuses to start. Only applied when the URL actually uses TLS.
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
_conf: dict[str, object] = {
    "task_track_started": True,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "broker_connection_retry_on_startup": True,
    "worker_prefetch_multiplier": 1,
}
if settings.celery_broker_url.startswith("rediss://"):
    _conf["broker_use_ssl"] = _ssl_opts
if settings.celery_result_backend.startswith("rediss://"):
    _conf["redis_backend_use_ssl"] = _ssl_opts

celery_app.conf.update(_conf)
