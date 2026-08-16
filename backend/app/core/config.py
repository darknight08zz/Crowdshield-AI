import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CrowdShield API"
    VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/application.log"
    REALTIME_ENABLED: bool = True

    # Supabase credentials (loaded from environment / .env file)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    # Security & CORS
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://localhost:19006"

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.CORS_ALLOWED_ORIGINS:
            return ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000"]
        origins = [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
        return origins if origins else ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000"]

    # Ingestion & Telemetry Settings
    SENSOR_MODE: str = "synthetic"  # "synthetic" or "live"
    RTSP_STREAM_TIMEOUT_SEC: int = 5
    GPS_STALE_THRESHOLD_SEC: int = 30
    CV_MODEL_TYPE: str = "csrnet_yolo_hybrid"

    # Computer Vision Pipeline Settings (Addendum Prompt 1)
    FRAME_SAMPLE_RATE: int = 5  # Target FPS processed from native 30 FPS stream (5-10 FPS recommended)
    CV_OCCLUSION_DENSITY_THRESHOLD: float = 2.5  # Density threshold (peds/m2) to trigger Dense Crowd Fallback
    CV_TRACKER_TYPE: str = "bytetrack"  # "bytetrack" (preferred for speed) or "deepsort"

    # Incident Response Policy Configuration (Phase 6D.1)
    # Configurable policy trigger states (operational choice, not hardcoded ground truth)
    INCIDENT_POLICY_TRIGGER_STATES: list[str] = ["EARLY_WARNING", "HIGH_RISK"]

    # Phase 6F Performance & Resilience Configuration
    REALTIME_PERSISTENCE_QUEUE_MAXSIZE: int = 100
    REALTIME_PERSISTENCE_WORKERS: int = 2
    REALTIME_FRAME_BUFFER_SIZE: int = 1
    REALTIME_MAX_FRAME_AGE: float = 2.0
    YOLO_DEVICE: str = "auto"
    YOLO_IMAGE_SIZE: int = 640
    YOLO_CONFIDENCE: float = 0.35
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
            ".env",
            "backend/.env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_production_config(self) -> None:
        """
        Fail-fast validation for required production settings.
        Raises ValueError if required settings are insecure or missing in production.
        """
        if self.ENV.lower() == "production":
            errors = []
            if self.DEBUG:
                errors.append("DEBUG mode must be False in production.")
            if not self.DATABASE_URL or "localhost" in self.DATABASE_URL:
                errors.append("DATABASE_URL must be configured with a production database host.")
            if not self.SUPABASE_JWT_SECRET or "YOUR_" in self.SUPABASE_JWT_SECRET:
                errors.append("SUPABASE_JWT_SECRET must be set to a valid secret.")
            if errors:
                raise ValueError("Production Configuration Error:\n" + "\n".join(f" - {err}" for err in errors))


settings = Settings()
if settings.ENV.lower() == "production":
    settings.validate_production_config()

