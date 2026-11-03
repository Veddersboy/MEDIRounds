from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    # Must match the frontend's value; used to verify Better Auth session cookies.
    BETTER_AUTH_SECRET: str
    # Origin allowed to call the API with cookies (CORS).
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    CHATBOT_API_URL: str | None = None
    CHATBOT_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
