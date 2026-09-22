from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        Index(
            "uq_work_orders_open_per_pond",
            "pond_id",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pond_id: Mapped[int] = mapped_column(
        ForeignKey("ponds.id"), nullable=False, index=True
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    close_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    pond: Mapped["Pond"] = relationship("Pond", back_populates="work_orders")
    retest_sample: Mapped[Optional["WaterSample"]] = relationship(
        "WaterSample", back_populates="work_order", uselist=False
    )
