"""Модели базы данных для coach_bot"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class CoachUser(Base):
    """Пользователь coach_bot"""
    __tablename__ = 'coach_users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    status = Column(String(20), default='free')  # free | trial | paid | premium
    stage = Column(String(20), default='welcome')  # welcome | reflection | planning | tracking
    
    # Подписка
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    
    # Модель и ключ
    preferred_model = Column(String(20), default='deepseek')  # deepseek | openai | claude | custom
    api_key = Column(String(255), nullable=True)  # пользовательский API ключ (зашифрованный)
    api_key_provider = Column(String(50), nullable=True)  # openai | anthropic | deepseek
    
    # Статистика
    messages_count = Column(Integer, default=0)
    daily_messages = Column(Integer, default=0)
    last_message_date = Column(Date, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    goals = relationship("CoachGoal", back_populates="user")
    checkins = relationship("CoachCheckin", back_populates="user")
    messages = relationship("CoachMessage", back_populates="user")


class CoachGoal(Base):
    """Цели пользователя"""
    __tablename__ = 'coach_goals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('coach_users.user_id'))
    goal_text = Column(Text, nullable=False)
    priority = Column(Integer, default=1)
    status = Column(String(20), default='active')  # active | completed | archived
    progress = Column(Integer, default=0)  # 0-100
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("CoachUser", back_populates="goals")


class CoachCheckin(Base):
    """Ежедневные чекины"""
    __tablename__ = 'coach_checkins'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('coach_users.user_id'))
    date = Column(Date, nullable=False)
    mood = Column(Integer, nullable=True)  # 1-5
    progress = Column(Text, nullable=True)
    blocked_by = Column(Text, nullable=True)
    plan_for_tomorrow = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("CoachUser", back_populates="checkins")


class CoachMessage(Base):
    """История диалогов"""
    __tablename__ = 'coach_messages'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('coach_users.user_id'))
    role = Column(String(20), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    model = Column(String(20), nullable=True)  # какая модель использовалась
    tokens_used = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("CoachUser", back_populates="messages")


class CoachPayment(Base):
    """Платежи"""
    __tablename__ = 'coach_payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('coach_users.user_id'))
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='RUB')
    payment_id = Column(String(100), unique=True, nullable=False)  # ID платежа в системе
    status = Column(String(20), default='pending')  # pending | success | failed | refunded
    plan = Column(String(20), nullable=True)  # monthly | yearly | premium
    
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)


class CoachInsight(Base):
    """Сохранённые инсайты пользователя"""
    __tablename__ = 'coach_insights'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('coach_users.user_id'))
    content = Column(Text, nullable=False)
    source_message_id = Column(Integer, nullable=True)  # из какого сообщения взят инсайт
    is_verified = Column(Boolean, default=False)  # подтвердил ли пользователь
    
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
