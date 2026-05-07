from __future__ import annotations

import asyncio
from collections import defaultdict

from models.behavior import BehaviorSnapshot


class RealtimeHub:
    """Session-scoped pub/sub for pushing live updates to websocket clients."""

    def __init__(self, queue_size: int = 32) -> None:
        self._queue_size = queue_size
        self._listeners: dict[str, set[asyncio.Queue[BehaviorSnapshot]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: str) -> asyncio.Queue[BehaviorSnapshot]:
        queue: asyncio.Queue[BehaviorSnapshot] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._listeners[session_id].add(queue)
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue[BehaviorSnapshot]) -> None:
        async with self._lock:
            listeners = self._listeners.get(session_id, set())
            listeners.discard(queue)
            if not listeners and session_id in self._listeners:
                del self._listeners[session_id]

    async def publish(self, session_id: str, snapshot: BehaviorSnapshot) -> None:
        async with self._lock:
            listeners = list(self._listeners.get(session_id, set()))

        for queue in listeners:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(snapshot)
            except asyncio.QueueFull:
                # If still full under contention, drop oldest signal.
                continue

