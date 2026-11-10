
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import AuthUser, UserSettings
from app.schemas import UserSettingsSchema

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["Settings"],
)


@router.get("", response_model=UserSettingsSchema)
async def get_settings(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await db.scalar(
        select(UserSettings).where(
            UserSettings.user_id == user.id,
        )
    )

    if settings is None:
        # Return defaults if the user has no saved settings yet
        return UserSettingsSchema()

    return UserSettingsSchema(
        theme=settings.theme,
        clinicianName=settings.clinician_name,
        specialty=settings.specialty,
        showDisclaimer=settings.show_disclaimer,
        enterToSend=settings.enter_to_send,
        experience=settings.experience,
    )


@router.put("", response_model=UserSettingsSchema)
async def save_settings(
    body: UserSettingsSchema,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await db.scalar(
        select(UserSettings).where(
            UserSettings.user_id == user.id,
        )
    )

    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)

    settings.theme = body.theme
    settings.clinician_name = body.clinicianName
    settings.specialty = body.specialty
    settings.show_disclaimer = body.showDisclaimer
    settings.enter_to_send = body.enterToSend
    settings.experience = body.experience

    await db.commit()

    return body
