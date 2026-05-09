from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from core.auth import require_ws_token
from dependencies import adaptation_rl_service, adaptation_service, behavior_sessions, realtime_hub

router = APIRouter(tags=["websockets"])
logger = logging.getLogger(__name__)


@router.websocket("/adaptation/{session_id}")
async def adaptation_stream(
    websocket: WebSocket, session_id: str, _: None = Depends(require_ws_token)
) -> None:
    await websocket.accept()
    queue = await realtime_hub.subscribe(session_id)
    try:
        # Send current adaptation config immediately on connect.
        snapshot = behavior_sessions.current(session_id)
        decision = adaptation_rl_service.select_action(session_id=session_id, snapshot=snapshot)
        config = adaptation_service.config_for_snapshot(snapshot=snapshot, decision=decision)
        await websocket.send_json(
            {
                "type": "adaptation_update",
                "payload": config.model_dump(mode="json"),
            }
        )

        while True:
            try:
                snapshot = await asyncio.wait_for(queue.get(), timeout=15)
                decision = adaptation_rl_service.select_action(
                    session_id=session_id, snapshot=snapshot,
                )
                config = adaptation_service.config_for_snapshot(
                    snapshot=snapshot, decision=decision,
                )
                await websocket.send_json(
                    {
                        "type": "adaptation_update",
                        "payload": config.model_dump(mode="json"),
                    }
                )
            except asyncio.TimeoutError:
                await websocket.send_json(
                    {"type": "heartbeat", "payload": {"session_id": session_id}}
                )
    except WebSocketDisconnect:
        logger.info("adaptation_ws_disconnected session_id=%s", session_id)
    finally:
        await realtime_hub.unsubscribe(session_id, queue)
