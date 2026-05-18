from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    device_token = Column(String(255), nullable=True)  # 设备标识，用于推送
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # 时间相关
    trigger_at = Column(DateTime(timezone=True), nullable=False)  # 下次触发时间
    timezone = Column(String(50), default="Asia/Shanghai")
    
    # 重复规则: None=不重复, "daily", "weekly", "custom:cron表达式"
    repeat_rule = Column(String(100), nullable=True)
    repeat_end_at = Column(DateTime(timezone=True), nullable=True)
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    snooze_count = Column(Integer, default=0)  # 推迟次数
    
    # 原始消息记录
    original_message = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)  # AI解析的原始结果
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
