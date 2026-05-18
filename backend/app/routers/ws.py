import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User
from app.routers.auth import decode_token
from app.services.push import push_service

router = APIRouter(prefix="/ws", tags=["websocket"])


async def get_user_from_token(token: str) -> User:
    async with AsyncSessionLocal() as db:
        user_id = decode_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user


@router.websocket("/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        user = await get_user_from_token(token)
    except HTTPException:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    await push_service.connect(user.id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "time": msg.get("time")})
                elif msg_type == "ack":
                    # 客户端确认收到提醒
                    pass
                else:
                    await websocket.send_json({"type": "error", "message": "Unknown message type"})
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    
    except WebSocketDisconnect:
        await push_service.disconnect(user.id, websocket)
    except Exception:
        await push_service.disconnect(user.id, websocket)
