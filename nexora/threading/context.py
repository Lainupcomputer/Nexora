from __future__ import annotations

import threading
from enum import Enum


class ThreadType(Enum):
    MAIN = "main"
    WORKER = "worker"
    UNKNOWN = "unknown"


class NexoraThreadError(RuntimeError):
    """
    Raised when an operation is executed from an invalid thread.
    """


class ThreadContext:
    """
    Provides information about the current Nexora thread.
    """

    _main_thread_id: int | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Register the current thread as the Nexora main thread.
        """

        if cls._main_thread_id is None:
            cls._main_thread_id = threading.get_ident()

    @classmethod
    def initialize_worker(cls) -> None:
        """
        Mark the current thread as a Nexora worker.

        Worker identification is based on the NexoraWorker- thread name.
        """
        return

    @classmethod
    def current_type(cls) -> ThreadType:
        """
        Return the type of the current thread.
        """

        current_id = threading.get_ident()

        if cls._main_thread_id == current_id:
            return ThreadType.MAIN

        if threading.current_thread().name.startswith(
            "NexoraWorker-"
        ):
            return ThreadType.WORKER

        return ThreadType.UNKNOWN

    @classmethod
    def is_main_thread(cls) -> bool:
        return cls.current_type() == ThreadType.MAIN

    @classmethod
    def is_worker_thread(cls) -> bool:
        return cls.current_type() == ThreadType.WORKER

    @classmethod
    def assert_main_thread(
        cls,
        operation: str = "This operation",
    ) -> None:

        if not cls.is_main_thread():
            raise NexoraThreadError(
                f'{operation} must run on the main thread.'
            )

    @classmethod
    def assert_worker_thread(
        cls,
        operation: str = "This operation",
    ) -> None:

        if not cls.is_worker_thread():
            raise NexoraThreadError(
                f'{operation} must run on a Nexora worker thread.'
            )

    @classmethod
    def thread_name(cls) -> str:
        return threading.current_thread().name