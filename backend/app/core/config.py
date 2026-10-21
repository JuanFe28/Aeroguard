"""
AeroGuard — Backend Configuration
Centraliza todas las variables de entorno y configuraciones del sistema.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # La plantilla también contiene variables de Docker y del simulador.
    )

    # ====== App ======
    APP_NAME: str = "AeroGuard"
    APP_VERSION: str = "1.2.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    ALLOW_DEMO_TOKENS: bool = False
    SEED_DEMO_DATA: bool = False
    ALLOW_SQLITE_FALLBACK: bool = False
    PUBLIC_FRONTEND_URL: str = "http://127.0.0.1:3000"
    AUTH_RATE_LIMIT: int = Field(default=20, ge=1)
    AUTH_RATE_WINDOW_SECONDS: int = Field(default=60, ge=1)
    REPORT_SCHEDULER_ENABLED: bool = True
    SENSOR_STALE_SECONDS: int = 120
    METRICS_BEARER_TOKEN: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    # ====== API ======
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    ]

    # ====== Database ======
    DATABASE_URL: str = "postgresql+asyncpg://aeroguard:aeroguard_pass@localhost:5432/aeroguard"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ====== Security / JWT ======
    SECRET_KEY: str = "CHANGE_THIS_TO_A_VERY_LONG_RANDOM_SECRET_IN_PRODUCTION_MIN_32_CHARS"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    MIN_PASSWORD_LENGTH: int = 8

    # ====== RabbitMQ ======
    RABBITMQ_URL: str = "amqp://aeroguard:aeroguard_pass@localhost:5672/"
    RABBITMQ_EXCHANGE: str = "aeroguard"
    QUEUE_AI_PROCESSING: str = "ai.processing"
    QUEUE_REPORTS: str = "reports.generation"
    QUEUE_NOTIFICATIONS: str = "notifications.send"
    QUEUE_TELEMETRY: str = "telemetry.incoming"

    # ====== AI / Vision ======
    AI_MODEL_PATH: str = "models/yolov8n.pt"
    AI_CONFIDENCE_THRESHOLD: float = 0.70
    AI_ENABLED: bool = True

    # ====== Detection ======
    DETECTION_MAX_ALTITUDE: float = 1000.0
    DETECTION_MIN_SPEED: float = 0.0
    DETECTION_MAX_SPEED: float = 300.0
    ANOMALY_THRESHOLD: float = 2.5
    ALERTS_ENABLED: bool = True

    # ====== Logging ======
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # ====== Email (for password reset) ======
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@aeroguard.co"

    # ====== Reports ======
    REPORTS_DIR: str = Field(default_factory=lambda: str(Path.home() / ".aeroguard" / "reports"))
    MAX_REPORT_AGE_DAYS: int = 30

    # ====== SOAR / n8n Webhook & AI Tactical Agent ======
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook/aeroguard-incident"
    N8N_WEBHOOK_TIMEOUT: float = 3.5
    SOAR_AI_AGENT_ENABLED: bool = False

    @model_validator(mode="after")
    def validate_production(self):
        if self.APP_ENV == "production":
            weak = (len(self.SECRET_KEY) < 32 or self.SECRET_KEY.startswith(("CHANGE_", "AEROGUARD_SECURE_DEV")))
            if weak:
                raise ValueError("Producción requiere SECRET_KEY propia de al menos 32 caracteres.")
            if self.DEBUG or self.ALLOW_DEMO_TOKENS or self.SEED_DEMO_DATA or self.ALLOW_SQLITE_FALLBACK:
                raise ValueError("Producción no permite DEBUG, datos/tokens demo ni fallback de base de datos.")
        return self


# Singleton
settings = Settings()
