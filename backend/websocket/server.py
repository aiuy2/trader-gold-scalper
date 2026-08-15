"""server.py - the /ws endpoint. Authenticates via a ?token= query param
(browsers/React-Native can't set custom headers on the WS handshake), then
keeps the connection open and handles inbound {"subscribe": [...]} messages."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.security import decode_access_token
from database.database import SessionLocal
from database.repositories import users as users_repo
from websocket.connection_manager import manager
from websocket.subscriptions import subscriptions

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    email = decode_access_token(token)
    if not email:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        user = users_repo.get_by_email(db, email)
    finally:
        db.close()
    if not user:
        await websocket.close(code=4401)
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            message = await websocket.receive_json()
            if "subscribe" in message:
                subscriptions.subscribe(websocket, message["subscribe"])
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
        subscriptions.drop(websocket)
