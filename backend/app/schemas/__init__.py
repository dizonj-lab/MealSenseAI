from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

DiabetesStatus = Literal["none", "prediabetes", "type1", "type2", "gestational", "prefer_not_to_disclose"]
Goal = Literal["carb_awareness", "calorie_awareness", "weight_management", "balanced_nutrition", "diabetes_friendly"]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileIn(BaseModel):
    health_consent: bool = False
    age: int | None = Field(default=None, ge=1, le=120)
    sex: Literal["female", "male", "other", "prefer_not_to_say"] | None = None
    height_cm: float | None = Field(default=None, ge=50, le=260)
    weight_kg: float | None = Field(default=None, ge=10, le=400)
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"] | None = None
    diet_preferences: list[str] = []
    diabetes_status: DiabetesStatus | None = None
    allergies: list[str] = []
    restrictions: list[str] = []
    glucose_unit: Literal["mmol/L", "mg/dL"] = "mmol/L"
    known_readings: str | None = Field(default=None, max_length=1000)
    hba1c: float | None = Field(default=None, ge=3, le=20)
    has_cgm: bool | None = None
    clinician_targets: str | None = Field(default=None, max_length=1000)
    goals: list[Goal] = []
    calorie_goal: float | None = Field(default=None, ge=500, le=6000)
    carb_goal_g: float | None = Field(default=None, ge=20, le=800)
    protein_goal_g: float | None = Field(default=None, ge=10, le=400)


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    updated_at: datetime | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    onboarded: bool
    created_at: datetime
    profile: ProfileOut | None = None


class AnalyzeIn(BaseModel):
    meal_id: int


class FoodUpdateIn(BaseModel):
    nutrition_key: str | None = None
    label: str | None = Field(default=None, max_length=200)
    grams: float | None = Field(default=None, gt=0, le=5000)
    confirmed: bool | None = None


class FoodAddIn(BaseModel):
    nutrition_key: str | None = None
    label: str | None = Field(default=None, max_length=200)
    grams: float | None = Field(default=None, gt=0, le=5000)
    servings: float = Field(default=1.0, gt=0, le=20)


class ConfirmIn(BaseModel):
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] | None = None
    eaten_at: datetime | None = None


class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    origin: str
    label: str
    nutrition_key: str | None
    mapping_quality: str
    original_prediction: dict | None
    grams: float
    portion: dict
    nutrients: dict
    nutrition_source: dict | None
    confirmed: bool
    user_corrected: bool
    removed: bool


class MealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    meal_type: str | None
    description: str | None
    reference_object: str | None
    serving_note: str | None
    images: list[dict]
    totals: dict
    insights: dict
    model_info: dict
    stages: list[dict]
    eaten_at: datetime
    created_at: datetime
    updated_at: datetime
    foods: list[FoodOut]


class MealSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    meal_type: str | None
    eaten_at: datetime
    totals: dict
    labels: list[str] = []
    glucose_level: str | None = None
    has_image: bool = False


class DaySummary(BaseModel):
    date: str
    calories_kcal: float
    carbs_g: float
    protein_g: float
    fat_g: float
    meals: int


class HistoryOut(BaseModel):
    meals: list[MealSummary]
    days: list[DaySummary]
