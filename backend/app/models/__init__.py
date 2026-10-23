from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    profile: Mapped["HealthProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    health_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(20))
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    activity_level: Mapped[str | None] = mapped_column(String(20))
    diet_preferences: Mapped[list] = mapped_column(JSON, default=list)
    diabetes_status: Mapped[str | None] = mapped_column(String(30))
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    restrictions: Mapped[list] = mapped_column(JSON, default=list)
    glucose_unit: Mapped[str] = mapped_column(String(10), default="mmol/L")
    known_readings: Mapped[str | None] = mapped_column(Text)
    hba1c: Mapped[float | None] = mapped_column(Float)
    has_cgm: Mapped[bool | None] = mapped_column(Boolean)
    clinician_targets: Mapped[str | None] = mapped_column(Text)
    goals: Mapped[list] = mapped_column(JSON, default=list)
    calorie_goal: Mapped[float | None] = mapped_column(Float)
    carb_goal_g: Mapped[float | None] = mapped_column(Float)
    protein_goal_g: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user: Mapped[User] = relationship(back_populates="profile")


class Meal(Base):
    __tablename__ = "meals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="captured")  # captured|analyzed|confirmed
    meal_type: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    reference_object: Mapped[str | None] = mapped_column(String(40))
    serving_note: Mapped[str | None] = mapped_column(Text)
    images: Mapped[list] = mapped_column(JSON, default=list)
    totals: Mapped[dict] = mapped_column(JSON, default=dict)
    insights: Mapped[dict] = mapped_column(JSON, default=dict)
    model_info: Mapped[dict] = mapped_column(JSON, default=dict)
    stages: Mapped[list] = mapped_column(JSON, default=list)
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    foods: Mapped[list["MealFood"]] = relationship(back_populates="meal", cascade="all, delete-orphan",
                                                   order_by="MealFood.id")


class MealFood(Base):
    __tablename__ = "meal_foods"
    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(20))  # model|description|manual|slm
    label: Mapped[str] = mapped_column(String(200))
    taxonomy_class: Mapped[str | None] = mapped_column(String(120))  # EXP-002 class finally chosen (model or user)
    nutrition_key: Mapped[str | None] = mapped_column(String(80))
    mapping_quality: Mapped[str] = mapped_column(String(20), default="none")  # exact|proxy|fuzzy|provisional|none
    original_prediction: Mapped[dict | None] = mapped_column(JSON)
    grams: Mapped[float] = mapped_column(Float, default=0)
    portion: Mapped[dict] = mapped_column(JSON, default=dict)  # method, uncertainty, range, notes
    nutrients: Mapped[dict] = mapped_column(JSON, default=dict)
    nutrition_source: Mapped[dict | None] = mapped_column(JSON)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    user_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    removed: Mapped[bool] = mapped_column(Boolean, default=False)
    meal: Mapped[Meal] = relationship(back_populates="foods")


class Correction(Base):
    __tablename__ = "corrections"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[int | None] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))  # edit_food|edit_portion|remove|add|confirm
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    model_name: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InferenceLog(Base):
    __tablename__ = "inference_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int | None] = mapped_column(Integer, index=True)
    model_name: Mapped[str] = mapped_column(String(80), index=True)
    model_version: Mapped[str] = mapped_column(String(80))
    task: Mapped[str] = mapped_column(String(40))
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    latency_ms: Mapped[float] = mapped_column(Float)
    tokens: Mapped[int | None] = mapped_column(Integer)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Experiment(Base):
    """Offline evaluation runs. Accuracy metrics are stored only when labeled ground truth was used."""
    __tablename__ = "experiments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    model_name: Mapped[str] = mapped_column(String(80))
    dataset: Mapped[str] = mapped_column(String(200))
    n_samples: Mapped[int] = mapped_column(Integer)
    has_ground_truth: Mapped[bool] = mapped_column(Boolean)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
