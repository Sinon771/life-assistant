from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import Reminder, User
from app.routers.auth import get_current_user
from app.services.scheduler import schedule_reminder, remove_reminder_schedule, snooze_reminder

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    trigger_at: datetime
    repeat_rule: Optional[str] = None
    repeat_end_at: Optional[datetime] = None


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    trigger_at: Optional[datetime] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_reminders(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Reminder).where(Reminder.user_id == current_user.id)
    if active_only:
        query = query.where(Reminder.is_active == True)
    query = query.order_by(desc(Reminder.created_at))
    
    result = await db.execute(query)
    reminders = result.scalars().all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "trigger_at": r.trigger_at.isoformat(),
            "repeat_rule": r.repeat_rule,
            "is_active": r.is_active,
            "is_completed": r.is_completed,
            "snooze_count": r.snooze_count,
            "created_at": r.created_at.isoformat()
        }
        for r in reminders
    ]


@router.post("")
async def create_reminder(
    req: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reminder = Reminder(
        user_id=current_user.id,
        title=req.title,
        description=req.description,
        trigger_at=req.trigger_at,
        repeat_rule=req.repeat_rule,
        repeat_end_at=req.repeat_end_at
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    
    schedule_reminder(reminder.id, reminder.trigger_at)
    return {"id": reminder.id, "message": "提醒已创建"}


@router.get("/{reminder_id}")
async def get_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Reminder).where(
            and_(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="提醒不存在")
    return {
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "trigger_at": r.trigger_at.isoformat(),
        "repeat_rule": r.repeat_rule,
        "is_active": r.is_active,
        "is_completed": r.is_completed
    }


@router.put("/{reminder_id}")
async def update_reminder(
    reminder_id: int,
    req: ReminderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Reminder).where(
            and_(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="提醒不存在")
    
    if req.title is not None:
        r.title = req.title
    if req.description is not None:
        r.description = req.description
    if req.trigger_at is not None:
        r.trigger_at = req.trigger_at
        schedule_reminder(r.id, r.trigger_at)
    if req.is_active is not None:
        r.is_active = req.is_active
        if not r.is_active:
            remove_reminder_schedule(r.id)
    
    await db.commit()
    return {"message": "提醒已更新"}


@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Reminder).where(
            and_(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="提醒不存在")
    
    remove_reminder_schedule(r.id)
    await db.delete(r)
    await db.commit()
    return {"message": "提醒已删除"}


@router.post("/{reminder_id}/snooze")
async def snooze_reminder_endpoint(
    reminder_id: int,
    minutes: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Reminder).where(
            and_(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="提醒不存在")
    
    success = await snooze_reminder(reminder_id, minutes)
    if success:
        return {"message": f"已推迟{minutes}分钟", "new_trigger_at": r.trigger_at.isoformat()}
    else:
        raise HTTPException(status_code=500, detail="推迟失败")


@router.post("/{reminder_id}/complete")
async def complete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Reminder).where(
            and_(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="提醒不存在")
    
    r.is_active = False
    r.is_completed = True
    remove_reminder_schedule(reminder_id)
    await db.commit()
    return {"message": "提醒已完成"}
