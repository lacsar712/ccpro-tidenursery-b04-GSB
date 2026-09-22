from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from app.models.work_order import WorkOrder


class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pond_id: int = Field(..., alias="pondId")


class WorkOrderClose(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    close_note: str = Field(..., alias="closeNote")

    @field_validator("close_note")
    @classmethod
    def validate_close_note(cls, v: str) -> str:
        if len(v.strip()) < 4:
            raise ValueError("关闭说明至少需要 4 个字符")
        return v


class WorkOrderOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    pond_code: str = Field(serialization_alias="pondCode")
    triggered_at: datetime = Field(serialization_alias="triggeredAt")
    closed_at: Optional[datetime] = Field(None, serialization_alias="closedAt")
    close_note: Optional[str] = Field(None, serialization_alias="closeNote")
    status: Literal["open", "closed"]
    retest_sample_id: Optional[int] = Field(None, serialization_alias="retestSampleId")
    retest_salinity: Optional[float] = Field(None, serialization_alias="retestSalinity")
    retest_sampled_at: Optional[datetime] = Field(
        None, serialization_alias="retestSampledAt"
    )

    @classmethod
    def build(cls, wo: "WorkOrder") -> "WorkOrderOut":
        rs = wo.retest_sample
        return cls(
            id=wo.id,
            pond_id=wo.pond_id,
            pond_code=wo.pond.pond_code,
            triggered_at=wo.triggered_at,
            closed_at=wo.closed_at,
            close_note=wo.close_note,
            status="closed" if wo.closed_at else "open",
            retest_sample_id=rs.id if rs else None,
            retest_salinity=rs.salinity_ppt if rs else None,
            retest_sampled_at=rs.sampled_at if rs else None,
        )
