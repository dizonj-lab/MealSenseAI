from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_name: str = "MealSenseAI"
    database_url: str = "postgresql+psycopg://mealsense:mealsense@localhost:5432/mealsenseai"
    redis_url: str = ""  # optional; empty = in-process cache
    jwt_secret: str = "change-me-in-env"
    jwt_expire_minutes: int = 60 * 24 * 7
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = ""  # empty = auto-pick an installed text model
    ollama_timeout_s: float = 15.0  # per call; the SLM is optional, so never let it stall an analysis
    data_dir: Path = ROOT / "data"
    models_dir: Path = ROOT / "ml" / "models"
    nutrition_db: Path = ROOT / "datasets" / "nutrition" / "foods.json"
    frontend_dist: Path = ROOT / "frontend" / "dist"
    max_upload_mb: int = 12
    # contact form: messages are always stored; they are also emailed to contact_to when smtp_host is set
    contact_to: str = "joel.dizon@live.com"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""   # defaults to smtp_user


settings = Settings()
