from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models import Reminder
from app.services.push import push_service
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def execute_reminder(reminder_id: int):
    """执行提醒任务"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = result.scalar_one_or_none()
        
        if not reminder or not reminder.is_active:
            return
        
        # 发送推送
        await push_service.send_reminder(
            user_id=reminder.user_id,
            reminder_id=reminder.id,
            title=reminder.title,
            body=reminder.description or "您有一个提醒"
        )
        
        now = datetime.now().astimezone()
        
        # 处理重复规则
        if reminder.repeat_rule and (not reminder.repeat_end_at or now < reminder.repeat_end_at):
            # 计算下次触发时间
            next_trigger = calculate_next_trigger(reminder.trigger_at, reminder.repeat_rule)
            if next_trigger and (not reminder.repeat_end_at or next_trigger < reminder.repeat_end_at):
                reminder.trigger_at = next_trigger
                reminder.snooze_count = 0
                await session.commit()
                
                # 重新调度
                schedule_reminder(reminder.id, next_trigger)
            else:
                reminder.is_active = False
                await session.commit()
        else:
            # 非重复任务，标记为完成
            reminder.is_active = False
            reminder.is_completed = True
            await session.commit()
        
        logger.info(f"Reminder {reminder_id} executed at {now}")


def calculate_next_trigger(current_trigger: datetime, repeat_rule: str) -> Optional[datetime]:
    """计算下次触发时间"""
    if repeat_rule == "daily":
        return current_trigger + timedelta(days=1)
    elif repeat_rule == "weekly":
        return current_trigger + timedelta(weeks=1)
    elif repeat_rule == "weekdays":
        # 找到下一个工作日
        next_day = current_trigger + timedelta(days=1)
        while next_day.weekday() >= 5:  # 5=周六, 6=周日
            next_day += timedelta(days=1)
        return next_day
    elif repeat_rule == "weekends":
        next_day = current_trigger + timedelta(days=1)
        while next_day.weekday() < 5:
            next_day += timedelta(days=1)
        return next_day
    elif repeat_rule.startswith("custom:"):
        # 对于自定义cron，简单加一天（实际应由croniter精确计算）
        from croniter import croniter
        itr = croniter(repeat_rule[7:], current_trigger)
        return itr.get_next(datetime)
    return None


def schedule_reminder(reminder_id: int, trigger_at: datetime):
    """将提醒加入调度器"""
    job_id = f"reminder_{reminder_id}"
    
    # 如果已存在，先移除
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    scheduler.add_job(
        execute_reminder,
        trigger=DateTrigger(run_date=trigger_at),
        id=job_id,
        args=[reminder_id],
        replace_existing=True,
        misfire_grace_time=300  # 5分钟内允许补偿执行
    )
    logger.info(f"Scheduled reminder {reminder_id} at {trigger_at}")


def remove_reminder_schedule(reminder_id: int):
    """移除提醒调度"""
    job_id = f"reminder_{reminder_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed schedule for reminder {reminder_id}")


async def load_active_reminders():
    """启动时加载所有活跃的提醒"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Reminder).where(
                and_(
                    Reminder.is_active == True,
                    Reminder.trigger_at > datetime.now().astimezone()
                )
            )
        )
        reminders = result.scalars().all()
        
        for r in reminders:
            schedule_reminder(r.id, r.trigger_at)
        
        logger.info(f"Loaded {len(reminders)} active reminders")


async def snooze_reminder(reminder_id: int, minutes: int) -> bool:
    """推迟提醒"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = result.scalar_one_or_none()
        
        if not reminder:
            return False
        
        new_trigger = datetime.now().astimezone() + timedelta(minutes=minutes)
        reminder.trigger_at = new_trigger
        reminder.snooze_count += 1
        await session.commit()
        
        schedule_reminder(reminder_id, new_trigger)
        return True
