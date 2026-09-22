from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TicketClose(BaseModel):
    close_note: str = Field(..., min_length=4, alias="closeNote")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("close_note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        note = v.strip()
        if len(note) < 4:
            raise ValueError("关闭说明至少 4 个字")
        return note


class SalinityRetestTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    pond_code: Optional[str] = Field(default=None, serialization_alias="pondCode")
    triggered_at: datetime = Field(serialization_alias="triggeredAt")
    closed_at: Optional[datetime] = Field(default=None, serialization_alias="closedAt")
    close_note: Optional[str] = Field(default=None, serialization_alias="closeNote")
    retest_sample_id: Optional[int] = Field(
        default=None, serialization_alias="retestSampleId"
    )
    retest_salinity: Optional[float] = Field(
        default=None, serialization_alias="retestSalinity"
    )


class PondSalinityStatus(BaseModel):
    """某塘采样放行/拦截状态，供水质样页展示拦截原因。"""

    model_config = ConfigDict(populate_by_name=True)

    pond_id: int = Field(serialization_alias="pondId")
    blocked: bool
    can_create_sample: bool = Field(serialization_alias="canCreateSample")
    can_create_ticket: bool = Field(serialization_alias="canCreateTicket")
    phase: str  # normal | needs_ticket | awaiting_retest | awaiting_close
    open_ticket_id: Optional[int] = Field(
        default=None, serialization_alias="openTicketId"
    )
    reason: Optional[str] = None
