import pytest
from pydantic import ValidationError

from app.schemas import MessageCreate, MessageSchema


def test_schema_rejects_invalid_messages():
    assert MessageCreate.model_validate({"content": "  What is HbA1c?  "}).content == "What is HbA1c?"

    for bad_payload in ({"content": " "}, {"content": 123}, {"content": "Hello", "unexpected": True}):
        with pytest.raises(ValidationError):
            MessageCreate.model_validate(bad_payload)

    with pytest.raises(ValidationError):
        MessageSchema.model_validate({
            "id": "msg-1", "role": "system", "content": "Not allowed",
            "createdAt": "2026-10-26T12:00:00Z", "citations": [],
        })
