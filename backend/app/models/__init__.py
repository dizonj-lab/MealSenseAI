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
    training_consent: Mapped[bool] = mapped_column(Boolean, default=False)  # corrected photo regions may be exported for training
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)          # granted only by `python -m app.tools.admin grant`
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contributor_status: Mapped[str] = mapped_column(String(20), default="active")   # active | suspended (training only)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    profile: Mapped["HealthProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    health_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    age: Mapped[int | None] = mapped_column(Integer)
    age_range: Mapped[str | None] = mapped_column(String(10))
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
    other_goal: Mapped[str | None] = mapped_column(String(200))
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
    origin: Mapped[str] = mapped_column(String(20))  # model|memory|description|manual|slm|drawn (a region the user drew)
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
    kind: Mapped[str] = mapped_column(String(20))  # edit_food|edit_portion|remove|add|confirm|merge
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


class GlucoseReading(Base):
    """A glucose value the user measured (meter/CGM) and entered. Stored in mmol/L. Never generated by the app."""
    __tablename__ = "glucose_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meal_id: Mapped[int | None] = mapped_column(ForeignKey("meals.id", ondelete="SET NULL"), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    value_mmol: Mapped[float] = mapped_column(Float)
    entered_unit: Mapped[str] = mapped_column(String(10))         # mmol/L | mg/dL as typed by the user
    context: Mapped[str] = mapped_column(String(20), default="other")  # fasting | before_meal | after_meal | other
    source: Mapped[str] = mapped_column(String(20), default="meter")   # meter | cgm
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CustomFood(Base):
    """A food the user defined (not in the reference table). Missing nutrient values stay null."""
    __tablename__ = "custom_foods"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    serving_g: Mapped[float] = mapped_column(Float)
    serving_desc: Mapped[str] = mapped_column(String(80), default="1 serving")
    per_100g: Mapped[dict] = mapped_column(JSON)            # NUTRIENTS -> value or null
    glycemic_index: Mapped[float | None] = mapped_column(Float)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class TrainingSample(Base):
    """A photo region with a user-given or user-confirmed label: personal memory for future meals and,
    with consent, labelled data for the next training cycle (app/tools/export_dataset.py, from a frozen dataset version)."""
    __tablename__ = "training_samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meal_id: Mapped[int | None] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    view: Mapped[str] = mapped_column(String(10))
    image_path: Mapped[str] = mapped_column(String(500))
    bbox: Mapped[dict | None] = mapped_column(JSON)        # normalised x,y,w,h; null = whole photo
    label: Mapped[str] = mapped_column(String(120))
    nutrition_key: Mapped[str | None] = mapped_column(String(80))
    taxonomy_class: Mapped[str | None] = mapped_column(String(120))   # set when the label is an EXP-002 class
    custom_food_id: Mapped[int | None] = mapped_column(ForeignKey("custom_foods.id", ondelete="SET NULL"))
    model_label: Mapped[str | None] = mapped_column(String(120))      # what the model said (top-1), for error analysis
    model_score: Mapped[float | None] = mapped_column(Float)
    fingerprint: Mapped[list] = mapped_column(JSON)       # sqrt of EXP-002 class probabilities (unit length)
    source: Mapped[str] = mapped_column(String(20))       # named | corrected | confirmed
    model_version: Mapped[str | None] = mapped_column(String(80))
    model_candidates: Mapped[list] = mapped_column(JSON, default=list)   # the model's top-3: label, nutrition_key, score
    # Governance (services/screening.py): shared only with consent at the time, until withdrawn; screened, then
    # passed / flagged / rejected automatically, and approved / rejected by an admin.
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    audit: Mapped[bool] = mapped_column(Boolean, default=False)          # picked for the random audit
    image_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    phash: Mapped[str | None] = mapped_column(String(16))
    screened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AuditLog(Base):
    """Every admin action and every consent change, newest first in the admin's audit page."""
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    target_type: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class DatasetVersion(Base):
    """A frozen set of approved user samples for one training cycle. Its manifest lists the sample ids, so the
    export is reproducible; withdrawals after freezing are honoured at export time."""
    __tablename__ = "dataset_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="frozen")    # frozen | superseded
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("dataset_versions.id", ondelete="SET NULL"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(String(500))
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ModelCandidate(Base):
    """A trained model waiting at the gate: its evaluation report (made offline on the fixed test set), the gate's
    checks, shadow-mode agreement with the live model, and the admin's decision."""
    __tablename__ = "model_candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    dataset_version_id: Mapped[int | None] = mapped_column(ForeignKey("dataset_versions.id", ondelete="SET NULL"))
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    gate: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="candidate")  # candidate | shadow | promoted | rejected | retired
    shadow: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppSetting(Base):
    """An admin's override of a tunable setting (services/tuning.py holds the registry and the defaults)."""
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[object] = mapped_column(JSON)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PromptVersion(Base):
    """A saved version of one of the local model's prompts. At most one active version per key; none active means
    the built-in default in services/tuning.py is used."""
    __tablename__ = "prompt_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), index=True)
    version: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(String(300))
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ChatThread(Base):
    """A Meal Advisor conversation, owned by one user and optionally about one meal. Kept 30 days after last use."""
    __tablename__ = "chat_threads"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meal_id: Mapped[int | None] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, index=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))            # user | assistant
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)   # source, evidence, validation, latency, follow-ups
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ContactMessage(Base):
    """A message from the public contact form. email_status: sent | not_configured | failed."""
    __tablename__ = "contact_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    email_status: Mapped[str] = mapped_column(String(20), default="not_configured")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
