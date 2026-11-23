"""
AeroGuard — Re-indexación Periódica del Corpus RAG con APScheduler

Sustituye a Apache Airflow en el servidor de Oracle (<= 4 GiB RAM / 2 vCPU)
evitando contenedores extra y manteniendo el índice Qdrant sincronizado.
"""

from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.services.agent_rag_service import agent_rag_service

logger = structlog.get_logger(__name__)

_rag_scheduler: AsyncIOScheduler | None = None


def _run_rag_reindex_job() -> None:
    try:
        info = agent_rag_service.reindex_corpus()
        logger.info("Re-indexación periódica RAG completada", **info)
    except Exception as exc:
        logger.warning("Error en re-indexación periódica RAG", error=str(exc))


def start_rag_scheduler() -> AsyncIOScheduler:
    """Inicia el job periódico liviano de actualización vectorial en APScheduler."""
    global _rag_scheduler
    if _rag_scheduler is not None and _rag_scheduler.running:
        return _rag_scheduler

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _run_rag_reindex_job,
        trigger=IntervalTrigger(minutes=max(1, settings.RAG_REINDEX_INTERVAL_MINUTES)),
        id="aeroguard_rag_reindex",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    _rag_scheduler = scheduler
    logger.info(
        "Scheduler RAG APScheduler activo",
        interval_minutes=settings.RAG_REINDEX_INTERVAL_MINUTES,
    )
    return scheduler


def stop_rag_scheduler() -> None:
    """Detiene de forma limpia el scheduler RAG al cerrar el backend."""
    global _rag_scheduler
    if _rag_scheduler is not None:
        try:
            _rag_scheduler.shutdown(wait=False)
        except Exception as exc:
            logger.debug("Cierre de scheduler RAG", error=str(exc))
        _rag_scheduler = None
