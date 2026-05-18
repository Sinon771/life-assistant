import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class PushService:
    """WebSocket推送服务 - 维护用户到WebSocket连接的映射"""
    
    def __init__(self):
        # user_id -> set of WebSocket connections
        self.connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            if user_id not in self.connections:
                self.connections[user_id] = set()
            self.connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected, total connections: {len(self.connections.get(user_id, set()))}")
    
    async def disconnect(self, user_id: int, websocket: WebSocket):
        async with self._lock:
            if user_id in self.connections:
                self.connections[user_id].discard(websocket)
                if not self.connections[user_id]:
                    del self.connections[user_id]
        logger.info(f"User {user_id} disconnected")
    
    async def send_to_user(self, user_id: int, message: dict):
        """向指定用户发送消息"""
        async with self._lock:
            sockets = self.connections.get(user_id, set()).copy()
        
        dead_sockets = set()
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.add(ws)
        
        # 清理断开的连接
        if dead_sockets:
            async with self._lock:
                if user_id in self.connections:
                    for ws in dead_sockets:
                        self.connections[user_id].discard(ws)
    
    async def send_reminder(self, user_id: int, reminder_id: int, title: str, body: str):
        """发送提醒通知"""
        await self.send_to_user(user_id, {
            "type": "reminder",
            "reminder_id": reminder_id,
            "title": title,
            "body": body,
            "timestamp": json.dumps({}),  # 占位
            "actions": ["完成", "推迟5分钟", "推迟10分钟"]
        })
        logger.info(f"Sent reminder {reminder_id} to user {user_id}")
    
    async def broadcast(self, message: dict):
        """广播消息（用于系统通知）"""
        all_sockets = []
        async with self._lock:
            for sockets in self.connections.values():
                all_sockets.extend(sockets)
        
        for ws in all_sockets:
            try:
                await ws.send_json(message)
            except Exception:
                pass


push_service = PushService()
