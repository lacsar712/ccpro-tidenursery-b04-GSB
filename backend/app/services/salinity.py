"""高盐复测工单触发规则。

阈值：
- TRIGGER_SALINITY：同一塘口按采样时刻排序，最近两份水质样盐度均 >= 35 时触发复测工单；
  工单未关闭前不允许继续常规采样（第三份会被拦截）。
- RETEST_PASS_MAX：未关闭工单存在时，仅允许登记恰好一份复测样，其盐度必须 < 32。
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.salinity_retest_ticket import SalinityRetestTicket
from app.models.water_sample import WaterSample

TRIGGER_SALINITY = 35.0
RETEST_PASS_MAX = 32.0


def latest_two_samples(db: Session, pond_id: int) -> List[WaterSample]:
    """按采样时刻（并列时按 id）倒序取该塘最近两份水质样。"""
    return (
        db.query(WaterSample)
        .filter(WaterSample.pond_id == pond_id)
        .order_by(WaterSample.sampled_at.desc(), WaterSample.id.desc())
        .limit(2)
        .all()
    )


def is_consecutive_high(samples: List[WaterSample]) -> bool:
    """最近两份盐度是否都达到触发阈值（>= 35）。"""
    return (
        len(samples) >= 2
        and samples[0].salinity_ppt >= TRIGGER_SALINITY
        and samples[1].salinity_ppt >= TRIGGER_SALINITY
    )


def get_open_ticket(db: Session, pond_id: int) -> Optional[SalinityRetestTicket]:
    return (
        db.query(SalinityRetestTicket)
        .filter(
            SalinityRetestTicket.pond_id == pond_id,
            SalinityRetestTicket.closed_at.is_(None),
        )
        .order_by(SalinityRetestTicket.id.desc())
        .first()
    )


def open_ticket_pond_ids(db: Session) -> set[int]:
    rows = (
        db.query(SalinityRetestTicket.pond_id)
        .filter(SalinityRetestTicket.closed_at.is_(None))
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def count_retest_samples(db: Session, ticket_id: int) -> int:
    return (
        db.query(WaterSample)
        .filter(WaterSample.retest_ticket_id == ticket_id)
        .count()
    )


def passing_retest_sample(
    db: Session, ticket_id: int
) -> Optional[WaterSample]:
    """工单下那份盐度 < 32 的复测样。"""
    return (
        db.query(WaterSample)
        .filter(
            WaterSample.retest_ticket_id == ticket_id,
            WaterSample.salinity_ppt < RETEST_PASS_MAX,
        )
        .order_by(WaterSample.sampled_at.desc(), WaterSample.id.desc())
        .first()
    )


def create_ticket(db: Session, pond_id: int) -> SalinityRetestTicket:
    ticket = SalinityRetestTicket(
        pond_id=pond_id,
        triggered_at=datetime.now(timezone.utc),
    )
    db.add(ticket)
    db.flush()
    return ticket
