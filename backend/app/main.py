
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db, settings
from app.models import AuthUser
from app.schemas import CurrentUserSchema
from app.routers.chats import router as chats_router

app = FastAPI(
    title="MediRounds App API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

app.include_router(chats_router)


@app.get("/")
async def root():
    return {"message": "MediRounds app backend is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/db")
async def database_health(
    db: AsyncSession = Depends(get_db),
):
    await db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "connected",
    }


@app.get("/db-test")
async def db_test(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("SELECT 1"))
    return {"database": result.scalar()}


@app.get(
    "/api/v1/me",
    response_model=CurrentUserSchema,
)
async def me(
    user: AuthUser = Depends(get_current_user),
):
    return user
