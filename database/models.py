import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, Boolean, Date
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    ph = Column(Float, nullable=False)
    chlorine = Column(Float, nullable=False)
    alkalinity = Column(Float, nullable=False)
    hardness = Column(Float, nullable=False)
    temperature_c = Column(Float, nullable=False)
    lsi_value = Column(Float)
    rsi_value = Column(Float)
    dosing_recommendation = Column(Text)
    notes = Column(Text)


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    id = Column(Integer, primary_key=True)
    task_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    due_date = Column(Date)
    interval_days = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)


class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    image_path = Column(String(500), nullable=False)
    caption = Column(Text)
