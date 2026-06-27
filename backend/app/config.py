from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database - 优先用 SQL Server，没有则用 SQLite
    DATABASE_URL: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str = "lis-server"
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_TOPIC_RESULT: str = "lis/instrument/+/result"
    MQTT_TOPIC_STATUS: str = "lis/instrument/+/status"
    MQTT_ENABLED: bool = True

    # Security
    SECRET_KEY: str = "lis-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # App
    DEBUG: bool = True
    APP_NAME: str = "LIS 实验室信息系统"
    APP_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # 默认用 SQLite（开发模式）
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lis.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
