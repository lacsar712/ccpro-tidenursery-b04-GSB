from datetime import datetime
from typing import List, Optional, Set

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.water_sample import WaterSample
from app.models.work_order import WorkOrder

# 触发复测的盐度阈值：最近两份水样盐度均 >= 35 ppt
HIGH_SALINITY_MIN = 35.0
# 复测通过线：复测水样盐度必须严格 < 32 ppt
RETEST_SALINITY_MAX = 32.0


class RetestGateError(Exception):
    """高盐复测规则拦截错误，路由层映射为 HTTP 400。"""


def latest_two_samples(db: Session, pond_id: int) -> List[WaterSample]:
    """按采样时刻倒序取该塘最近两份水样（时间并列以 id 倒序打破）。"""
    return (
        db.query(WaterSample)
        .filter(WaterSample.pond_id == pond_id)
        .order_by(WaterSample.sampled_at.desc(), WaterSample.id.desc())
        .limit(2)
        .all()
    )


def both_high(samples: List[WaterSample]) -> bool:
    return (
        len(samples) == 2
        and all(s.salinity_ppt >= HIGH_SALINITY_MIN for s in samples)
    )


def open_work_order(db: Session, pond_id: int) -> Optional[WorkOrder]:
    return (
        db.query(WorkOrder)
        .filter(WorkOrder.pond_id == pond_id, WorkOrder.closed_at.is_(None))
        .one_or_none()
    )


def open_work_order_pond_ids(db: Session) -> Set[int]:
    rows = (
        db.query(WorkOrder.pond_id)
        .filter(WorkOrder.closed_at.is_(None))
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def high_salinity_pond_ids(db: Session) -> Set[int]:
    """最近两份水样盐度均 >= 35 的塘口（窗口函数一条 SQL 完成分组取前二）。"""
    rn = (
        func.row_number()
        .over(
            partition_by=WaterSample.pond_id,
            order_by=(WaterSample.sampled_at.desc(), WaterSample.id.desc()),
        )
        .label("rn")
    )
    ranked = db.query(
        WaterSample.pond_id.label("pond_id"),
        WaterSample.salinity_ppt.label("salinity_ppt"),
        rn,
    ).subquery("ranked_samples")

    rows = (
        db.query(ranked.c.pond_id)
        .filter(ranked.c.rn <= 2)
        .group_by(ranked.c.pond_id)
        .having(
            func.count("*") == 2,
            func.min(ranked.c.salinity_ppt) >= HIGH_SALINITY_MIN,
        )
        .all()
    )
    return {r[0] for r in rows}


def restricted_pond_ids(db: Session) -> Set[int]:
    """受高盐复测限制的塘：有未关闭工单的塘 ∪ 两份高盐但尚无工单的塘。"""
    open_ids = open_work_order_pond_ids(db)
    return open_ids | (high_salinity_pond_ids(db) - open_ids)


def process_sample_creation(
    db: Session,
    *,
    pond_id: int,
    sampled_at: datetime,
    temp_c: float,
    salinity_ppt: float,
    do_mg_l: float,
    ph: float,
    notes: Optional[str],
) -> WaterSample:
    """新建水质样的权威业务决策树（塘口存在性由路由层先行校验）。"""
    wo = open_work_order(db, pond_id)

    # ---- 分支 A：存在未关闭工单，只允许恰好一份复测样 ----
    if wo is not None:
        existing = (
            db.query(WaterSample)
            .filter(WaterSample.work_order_id == wo.id)
            .first()
        )
        if existing is not None:
            raise RetestGateError("该复测工单的复测水样已登记，工单关闭前无法继续采样")
        if salinity_ppt >= RETEST_SALINITY_MAX:
            raise RetestGateError(
                f"复测水样盐度必须低于 {RETEST_SALINITY_MAX:g} ppt"
                f"（当前 {salinity_ppt:g}），请换水达标后再复测"
            )
        sample = WaterSample(
            pond_id=pond_id,
            sampled_at=sampled_at,
            temp_c=temp_c,
            salinity_ppt=salinity_ppt,
            do_mg_l=do_mg_l,
            ph=ph,
            notes=notes,
            work_order_id=wo.id,
        )
        db.add(sample)
        db.commit()
        db.refresh(sample)
        return sample

    # ---- 分支 B：无工单。最近两份已均高盐 -> 拦截第三份，须先建工单 ----
    if both_high(latest_two_samples(db, pond_id)):
        raise RetestGateError(
            "该塘口最近两次水样盐度均达到 35 ppt 及以上，请先生成复测工单后再继续采样"
        )

    sample = WaterSample(
        pond_id=pond_id,
        sampled_at=sampled_at,
        temp_c=temp_c,
        salinity_ppt=salinity_ppt,
        do_mg_l=do_mg_l,
        ph=ph,
        notes=notes,
        work_order_id=None,
    )
    db.add(sample)
    db.flush()  # 让新行对"插入后最近两份"查询可见

    # 自动路径：本次入库使最近两份双双高盐 -> 同事务自动建工单
    if both_high(latest_two_samples(db, pond_id)):
        db.add(WorkOrder(pond_id=pond_id))

    db.commit()
    db.refresh(sample)
    return sample
