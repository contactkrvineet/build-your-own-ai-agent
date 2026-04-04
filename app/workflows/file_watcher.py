"""
Watchdog-based file watcher — monitors the documents folder and
triggers hot-reload indexing whenever a file is created or modified.
"""

from __future__ import annotations

import time
from pathlib import Path
from threading import Thread
from typing import Optional

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config.settings import get_settings
from app.rag.ingestion import SUPPORTED_EXTENSIONS
from app.utils.logger import logger

_observer: Optional[Observer] = None
_handler: Optional[_DocumentHandler] = None


# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------

class _DocumentHandler(FileSystemEventHandler):
    """Watchdog handler — queues supported files for indexing."""

    def __init__(self, debounce_seconds: float = 5.0) -> None:
        super().__init__()
        self._debounce = debounce_seconds
        self._pending: dict[str, float] = {}   # path → timestamp
        self._skip: set[str] = set()           # paths to skip (already indexed by upload route)

    def skip_next(self, path: str) -> None:
        """Mark a path to be skipped once (upload route already indexed it)."""
        self._skip.add(str(Path(path).resolve()))

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory:
            self._queue(event.src_path)

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory:
            self._queue(event.src_path)

    def _queue(self, path: str) -> None:
        file = Path(path)
        if file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        resolved = str(file.resolve())
        if resolved in self._skip:
            self._skip.discard(resolved)
            logger.debug(f"File watcher: skipping {file.name} (already indexed by upload)")
            return
        self._pending[path] = time.monotonic()
        logger.debug(f"File watcher: queued {file.name}")
        # Debounce in a background thread
        Thread(target=self._debounce_index, args=(path,), daemon=True).start()

    def _debounce_index(self, path: str) -> None:
        time.sleep(self._debounce)
        # Only process if this is still the latest event for this path
        queued_at = self._pending.get(path, 0)
        if time.monotonic() - queued_at < self._debounce:
            return  # A newer event will handle it
        self._pending.pop(path, None)
        _index_file(path)


# ---------------------------------------------------------------------------
# Hot-index helper
# ---------------------------------------------------------------------------

def _index_file(path: str) -> None:
    logger.info(f"Hot-reloading new/modified document: {Path(path).name}")
    try:
        from app.agent.core import get_agent

        agent = get_agent()
        agent.add_document(path)
    except Exception as e:
        logger.error(f"Hot-reload failed for {path}: {e}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_file_watcher() -> Optional[Observer]:
    global _observer, _handler

    s = get_settings()
    if not s.file_watcher_enabled:
        logger.info("File watcher disabled in config.")
        return None

    watch_path = Path(s.rag_documents_path)
    watch_path.mkdir(parents=True, exist_ok=True)

    _handler = _DocumentHandler(debounce_seconds=5.0)
    _observer = Observer()
    _observer.schedule(_handler, str(watch_path), recursive=False)
    _observer.start()

    logger.info(f"File watcher started on: {watch_path.resolve()}")
    return _observer


def skip_file_watcher(path: str) -> None:
    """Tell the file watcher to skip the next event for this path."""
    if _handler:
        _handler.skip_next(path)


def stop_file_watcher() -> None:
    global _observer
    if _observer and _observer.is_alive():
        _observer.stop()
        _observer.join()
        logger.info("File watcher stopped.")
