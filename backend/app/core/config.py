import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CrowdShield API"
    VERSION: str = "1.0.0"
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Supabase credentials (loaded from environment / .env file)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    # Ingestion & Telemetry Settings
    SENSOR_MODE: str = "synthetic"  # "synthetic" or "live"
    RTSP_STREAM_TIMEOUT_SEC: int = 5
    GPS_STALE_THRESHOLD_SEC: int = 30
    CV_MODEL_TYPE: str = "csrnet_yolo_hybrid"

    # Computer Vision Pipeline Settings (Addendum Prompt 1)
    FRAME_SAMPLE_RATE: int = 5  # Target FPS processed from native 30 FPS stream (5-10 FPS recommended)
    CV_OCCLUSION_DENSITY_THRESHOLD: float = 2.5  # Density threshold (peds/m2) to trigger Dense Crowd Fallback
    CV_TRACKER_TYPE: str = "bytetrack"  # "bytetrack" (preferred for speed) or "deepsort"

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
            ".env",
            "backend/.env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )



settings = Settings()
