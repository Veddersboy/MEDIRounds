from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    CHATBOT_API_URL: str | None = None
    CHATBOT_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

settings = Settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Development only, disable in production
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

app = FastAPI(
    title="Diabetes App API",
    version="0.1.0",
)

@app.get("/")
async def root():
    return {
        "message": "Diabetes app backend is running"
    }

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


@app.get("/health/db")
async def database_health(
    db: AsyncSession = Depends(get_db),
):
    await db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected"
    }

@app.get("/db-test")
async def db_test(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("SELECT 1"))

    return {
        "database": result.scalar()
    }