from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from core.auth import require_ws_token
from dependencies import behavior_sessions, realtime_hub

router = APIRouter(tags=["websockets"])
logger = logging.getLogger(__name__)


@router.websocket("/emotion/{session_id}")
async def emotion_stream(
    websocket: WebSocket, session_id: str, _: None = Depends(require_ws_token)
) -> None:
    await websocket.accept()
    queue = await realtime_hub.subscribe(session_id)
    try:
        # Send the latest known state immediately after connect.
        await websocket.send_json(
            {
                "type": "emotion_update",
                "payload": behavior_sessions.current(session_id).model_dump(mode="json"),
            }
        )

        while True:
            try:
                snapshot = await asyncio.wait_for(queue.get(), timeout=15)
                await websocket.send_json(
                    {"type": "emotion_update", "payload": snapshot.model_dump(mode="json")}
                )
            except asyncio.TimeoutError:
                # Keepalive message so intermediaries do not close idle sockets.
                await websocket.send_json({"type": "heartbeat", "payload": {"session_id": session_id}})
    except WebSocketDisconnect:
        logger.info("websocket_disconnected session_id=%s", session_id)
    finally:
        await realtime_hub.unsubscribe(session_id, queue)

