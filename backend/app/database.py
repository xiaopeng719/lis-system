from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()
db_url = settings.get_database_url()

# SQLite 不支持 pool_size 等参数
connect_args = {}
engine_kwargs = {"echo": settings.DEBUG}

if "sqlite" in db_url:
    connect_args["check_same_thread"] = False
else:
    engine_kwargs.update({"pool_size": 20, "max_overflow": 10, "pool_pre_ping": True})

engine = create_async_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
