from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WaterSample(Base):
    __tablename__ = "water_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pond_id: Mapped[int] = mapped_column(ForeignKey("ponds.id"), nullable=False, index=True)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temp_c: Mapped[float] = mapped_column(Float, nullable=False)
    salinity_ppt: Mapped[float] = mapped_column(Float, nullable=False)
    do_mg_l: Mapped[float] = mapped_column(Float, nullable=False)
    ph: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("work_orders.id"), nullable=True, unique=True, index=True
    )

    pond: Mapped["Pond"] = relationship("Pond", back_populates="water_samples")
    work_order: Mapped[Optional["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="retest_sample"
    )
