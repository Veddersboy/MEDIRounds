from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints
from typing import Annotated

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

class CitationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    title: NonBlank
    url: HttpUrl | None = None
    detail: str | None = None

class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    content: NonBlank


class MessageSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: str
    role: Literal["user", "assistant"]
    content: NonBlank
    createdAt: datetime
    citations: list[CitationSchema] = Field(default_factory=list)


class ChatSessionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    createdAt: datetime
    updatedAt: datetime
    messages: list[MessageSchema] = Field(default_factory=list)
    archived: bool = False


class ChatTitleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: NonBlank = Field(max_length=255)


class UserSettingsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    theme: Literal["light", "dark", "system"] = "system"
    clinicianName: str = ""
    specialty: str = ""
    showDisclaimer: bool = True
    enterToSend: bool = True
