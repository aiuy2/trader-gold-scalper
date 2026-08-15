"""server.py - the /ws endpoint. Authenticates via a ?token= query param
(browsers/React-Native can't set custom headers on the WS handshake), then
keeps the connection open and handles two kinds of inbound messages:

  {"subscribe": [...]}  - a viewer (the web app) picking which channels
                           it wants (see subscriptions.py)
  {"report": {...}}      - local-client/ws_client.py relaying one trading
                           outcome from an engine running on the user's
                           own machine (see services/report_sync.py)

Both share this one endpoint/connection type on purpose - a local-client
session is just a connection that happens to send "report" messages
instead of "subscribe" ones, so no separate auth/route is needed."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.security import decode_access_token
from database.database import SessionLocal
from database.repositories import users as users_repo
from websocket.connection_manager import manager
from websocket.subscriptions import subscriptions
from services.report_sync import LocalClientSession, handle_report, end_session

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
    session = LocalClientSession(user.id)
    try:
        while True:
            message = await websocket.receive_json()
            if "subscribe" in message:
                subscriptions.subscribe(websocket, message["subscribe"])
            elif "report" in message:
                handle_report(session, message["report"])
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
        subscriptions.drop(websocket)
        end_session(session)
