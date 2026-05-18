from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import ChatMessage, Reminder, User
from app.services.llm import llm_service
from app.services.scheduler import schedule_reminder, snooze_reminder, remove_reminder_schedule
from app.routers.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    timezone: Optional[str] = "Asia/Shanghai"


class ChatResponse(BaseModel):
    reply: str
    action: Optional[str] = None  # created_reminder / snoozed / cancelled / none
    reminder_id: Optional[int] = None


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    now = datetime.now().astimezone()
    
    # 1. 用LLM解析用户意图
    parsed = await llm_service.parse_time_intent(
        user_message=req.message,
        current_time=now.isoformat(),
        timezone=req.timezone
    )
    
    intent = parsed.get("intent", "chat")
    confidence = parsed.get("confidence", 0.0)
    
    # 2. 根据意图执行操作
    if intent == "create_reminder" and confidence > 0.5:
        trigger_at_str = parsed.get("trigger_at")
        if trigger_at_str:
            try:
                trigger_at = datetime.fromisoformat(trigger_at_str)
            except ValueError:
                trigger_at = now + timedelta(minutes=5)
        else:
            trigger_at = now + timedelta(minutes=5)
        
        # 确保时间在未来
        if trigger_at < now:
            trigger_at = now + timedelta(minutes=1)
        
        reminder = Reminder(
            user_id=user_id,
            title=parsed.get("title", "提醒"),
            description=parsed.get("description"),
            trigger_at=trigger_at,
            timezone=req.timezone,
            repeat_rule=parsed.get("repeat_rule"),
            repeat_end_at=datetime.fromisoformat(parsed["repeat_end_at"]) if parsed.get("repeat_end_at") else None,
            original_message=req.message,
            parsed_data=parsed
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        
        # 加入调度器
        schedule_reminder(reminder.id, reminder.trigger_at)
        
        # 保存聊天记录
        db.add(ChatMessage(user_id=user_id, role="user", content=req.message))
        db.add(ChatMessage(user_id=user_id, role="assistant", content=parsed.get("reply_message", "已创建提醒")))
        await db.commit()
        
        return ChatResponse(
            reply=parsed.get("reply_message", "已为您创建提醒"),
            action="created_reminder",
            reminder_id=reminder.id
        )
    
    elif intent == "snooze" and confidence > 0.5:
        minutes = parsed.get("snooze_minutes", 10)
        
        # 找到用户最近的一个活跃提醒
        result = await db.execute(
            select(Reminder).where(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.is_active == True
                )
            ).order_by(desc(Reminder.trigger_at)).limit(1)
        )
        reminder = result.scalar_one_or_none()
        
        if reminder:
            success = await snooze_reminder(reminder.id, minutes)
            reply = parsed.get("reply_message", f"已推迟{minutes}分钟")
            
            db.add(ChatMessage(user_id=user_id, role="user", content=req.message))
            db.add(ChatMessage(user_id=user_id, role="assistant", content=reply))
            await db.commit()
            
            return ChatResponse(
                reply=reply,
                action="snoozed",
                reminder_id=reminder.id
            )
        else:
            return ChatResponse(reply="没有找到可以推迟的提醒")
    
    elif intent == "cancel" and confidence > 0.5:
        # 找到最近一个活跃提醒并取消
        result = await db.execute(
            select(Reminder).where(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.is_active == True
                )
            ).order_by(desc(Reminder.created_at)).limit(1)
        )
        reminder = result.scalar_one_or_none()
        
        if reminder:
            reminder.is_active = False
            remove_reminder_schedule(reminder.id)
            await db.commit()
            
            reply = parsed.get("reply_message", "已取消提醒")
            db.add(ChatMessage(user_id=user_id, role="user", content=req.message))
            db.add(ChatMessage(user_id=user_id, role="assistant", content=reply))
            await db.commit()
            
            return ChatResponse(
                reply=reply,
                action="cancelled",
                reminder_id=reminder.id
            )
        else:
            return ChatResponse(reply="没有找到可以取消的提醒")
    
    elif intent == "query":
        # 查询待办事项
        result = await db.execute(
            select(Reminder).where(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.is_active == True
                )
            ).order_by(Reminder.trigger_at)
        )
        reminders = result.scalars().all()
        
        if reminders:
            items = []
            for r in reminders:
                time_str = r.trigger_at.strftime("%m月%d日 %H:%M")
                repeat = ""
                if r.repeat_rule == "daily":
                    repeat = " [每天]"
                elif r.repeat_rule == "weekly":
                    repeat = " [每周]"
                elif r.repeat_rule == "weekdays":
                    repeat = " [工作日]"
                items.append(f"• {r.title}{repeat} - {time_str}")
            reply = "您的待办提醒：\n" + "\n".join(items)
        else:
            reply = "您当前没有待办提醒"
        
        db.add(ChatMessage(user_id=user_id, role="user", content=req.message))
        db.add(ChatMessage(user_id=user_id, role="assistant", content=reply))
        await db.commit()
        
        return ChatResponse(reply=reply, action="query")
    
    else:
        # 普通聊天 - 保留上下文
        # 获取最近20条聊天记录
        result = await db.execute(
            select(ChatMessage).where(
                ChatMessage.user_id == user_id
            ).order_by(desc(ChatMessage.created_at)).limit(20)
        )
        history = result.scalars().all()
        history.reverse()
        
        messages = []
        for h in history:
            messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": req.message})
        
        system_prompt = (
            "你是一个贴心的生活助手，可以帮助用户管理提醒、聊天解闷。"
            "当前时间：" + now.strftime("%Y-%m-%d %H:%M:%S") + 
            "\n如果用户提到时间相关的需求，请引导他们使用'提醒我...'的格式。"
        )
        
        reply = await llm_service.generate_chat_reply(messages, system_prompt)
        
        db.add(ChatMessage(user_id=user_id, role="user", content=req.message))
        db.add(ChatMessage(user_id=user_id, role="assistant", content=reply))
        await db.commit()
        
        return ChatResponse(reply=reply, action="none")


@router.get("/history")
async def get_chat_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ChatMessage).where(
            ChatMessage.user_id == current_user.id
        ).order_by(desc(ChatMessage.created_at)).limit(limit)
    )
    messages = result.scalars().all()
    messages.reverse()
    return [
        {"role": m.role, "content": m.content, "time": m.created_at.isoformat()}
        for m in messages
    ]
