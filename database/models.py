import datetime
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    Boolean,
    Date,
    LargeBinary,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Instrument(Base):
    __tablename__ = "instruments"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(200))
    can_measure_ph = Column(Boolean, default=False)
    can_measure_chlorine = Column(Boolean, default=False)
    can_measure_bromine = Column(Boolean, default=False)
    can_measure_alkalinity = Column(Boolean, default=False)
    can_measure_hardness = Column(Boolean, default=False)
    can_measure_cya = Column(Boolean, default=False)
    can_measure_salt = Column(Boolean, default=False)
    can_measure_oxygen = Column(Boolean, default=False)
    notes = Column(Text)


class Pool(Base):
    __tablename__ = "pools"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    volume_liter = Column(Float, nullable=False)
    pool_type = Column(String(20), default="chlorine")
    ph_min = Column(Float, default=7.2)
    ph_max = Column(Float, default=7.6)
    chlorine_min = Column(Float, default=0.5)
    chlorine_max = Column(Float, default=3.0)
    alkalinity_min = Column(Float, default=80)
    alkalinity_max = Column(Float, default=120)
    hardness_min = Column(Float, default=150)
    hardness_max = Column(Float, default=250)
    temperature_default = Column(Float, default=35)
    trinkwasser_id = Column(Integer, ForeignKey("trinkwasser.id"), nullable=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=True)
    shape = Column(String(10), default="rechteckig")
    inner_length_cm = Column(Float, nullable=True)
    inner_width_cm = Column(Float, nullable=True)
    inner_diameter_cm = Column(Float, nullable=True)
    min_fill_height_cm = Column(Float, default=35.0)
    max_fill_height_cm = Column(Float, default=45.0)
    auto_measurement_task_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.datetime.now)


class TaskTemplate(Base):
    __tablename__ = "task_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50), default="allgemein")
    interval_days = Column(Integer, default=7)
    default_follow_up_days = Column(Integer, default=0)
    pool_type = Column(String(20), default="all")
    icon = Column(String(10), default="📋")
    preferred_weekday = Column(Integer, nullable=True)
    product_name = Column(String(200), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    sort_order = Column(Integer, default=0)


class PoolTaskDefault(Base):
    __tablename__ = "pool_task_defaults"
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=False)
    active = Column(Boolean, default=True)
    custom_interval_days = Column(Integer, nullable=True)


class Trinkwasser(Base):
    __tablename__ = "trinkwasser"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    ph_default = Column(Float, default=7.5)
    alkalinity_default = Column(Float, default=145.0)
    calcium_hardness_default = Column(Float, default=185.0)
    notes = Column(Text)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    typ = Column(String(20), nullable=False)
    dosage_factor = Column(Float, default=0)
    unit = Column(String(20), default="g")
    active_chlorine_per_tab = Column(Float, nullable=True)
    interval_days = Column(Integer, default=0)
    notes = Column(Text)


class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    ph = Column(Float, nullable=False)
    chlorine = Column(Float, nullable=False)
    alkalinity = Column(Float, nullable=False)
    hardness = Column(Float, nullable=False)
    cya = Column(Float, default=0)
    temperature_c = Column(Float, nullable=False)
    lsi_value = Column(Float)
    rsi_value = Column(Float)
    csi_value = Column(Float)
    ccpp_value = Column(Float)
    dosing_recommendation = Column(Text)
    notes = Column(Text)


class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    reading_id = Column(Integer, ForeignKey("readings.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    image_path = Column(String(500))
    image_data = Column(LargeBinary, nullable=True)
    caption = Column(Text)


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=True)
    reading_id = Column(Integer, ForeignKey("readings.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("maintenance_tasks.id"), nullable=True)
    task_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    due_date = Column(Date)
    interval_days = Column(Integer, default=0)
    follow_up_days = Column(Integer, default=0)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=True)
    recommended_amount = Column(Float, nullable=True)
    recommended_unit = Column(String(20), nullable=True)
    actual_amount = Column(Float, nullable=True)
    actual_unit = Column(String(20), nullable=True)
    product_name = Column(String(200), nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    executed_notes = Column(Text, nullable=True)
