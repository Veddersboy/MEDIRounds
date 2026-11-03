from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db, settings
from app.models import AuthUser
from app.schemas import CurrentUserSchema

app = FastAPI(title="MediRounds App API", version="0.1.0")

# The frontend calls the API with credentials: "include", so the origin must be explicit (not "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "MediRounds app backend is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/db-test")
async def db_test(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"database": result.scalar()}


@app.get("/api/v1/me", response_model=CurrentUserSchema)
async def me(user: AuthUser = Depends(get_current_user)):
    return user
