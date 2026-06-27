import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.api.v1 import router as api_router

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("lis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"📦 Database: {settings.get_database_url()[:60]}...")

    # 导入所有模型
    import app.models  # noqa

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created")

    # 启动 MQTT 服务（后台任务，连接失败不影响启动）
    mqtt_task = None
    if settings.MQTT_ENABLED:
        try:
            from app.mqtt.service import mqtt_service
            mqtt_task = asyncio.create_task(mqtt_service.start())
            logger.info("✅ MQTT Service started (connecting in background)")
        except Exception as e:
            logger.warning(f"⚠️ MQTT Service failed to start: {e}")

    yield

    # Shutdown
    if mqtt_task:
        try:
            from app.mqtt.service import mqtt_service
            await mqtt_service.stop()
            mqtt_task.cancel()
        except Exception:
            pass
    logger.info("👋 Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
