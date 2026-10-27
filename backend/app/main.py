from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

app = FastAPI(title="MediRounds App API", version="0.1.0")


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
