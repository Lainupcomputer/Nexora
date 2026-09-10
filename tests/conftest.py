from __future__ import annotations

import pytest

from nexora.threading import TaskScheduler, ThreadContext


@pytest.fixture(autouse=True)
def initialize_thread_context():
    ThreadContext.initialize()


@pytest.fixture
def scheduler():
    scheduler = TaskScheduler(workers=4)

    try:
        yield scheduler
    finally:
        if not scheduler.shutdown_requested:
            scheduler.shutdown(wait=True)