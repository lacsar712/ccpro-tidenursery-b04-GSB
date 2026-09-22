from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.pond import Pond
from app.models.user import User
from app.models.water_sample import WaterSample
from app.schemas.water_sample import WaterSampleCreate, WaterSampleOut
from app.services import salinity

router = APIRouter(prefix="/api/water-samples", tags=["water-samples"])


@router.get("", response_model=List[WaterSampleOut])
def list_samples(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(WaterSample)
    if pond_id is not None:
        q = q.filter(WaterSample.pond_id == pond_id)
    return q.order_by(WaterSample.sampled_at.desc()).all()


@router.post("", response_model=WaterSampleOut, status_code=status.HTTP_201_CREATED)
def create_sample(
    payload: WaterSampleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")

    open_ticket = salinity.get_open_ticket(db, payload.pond_id)
    if open_ticket is not None:
        # 工单处理中：只允许登记恰好一份复测样，且盐度必须 < 32。
        existing = salinity.count_retest_samples(db, open_ticket.id)
        if existing >= 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"该塘已有 {existing} 份复测样，未关闭工单前禁止继续采样；"
                    "复测盐度已低于 32 时请先关闭工单"
                ),
            )
        if payload.salinity_ppt >= salinity.RETEST_PASS_MAX:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"该塘高盐复测工单处理中，复测样盐度必须低于 "
                    f"{salinity.RETEST_PASS_MAX:g} ppt（当前 {payload.salinity_ppt:g}）"
                ),
            )
        item = WaterSample(
            pond_id=payload.pond_id,
            sampled_at=payload.sampled_at,
            temp_c=payload.temp_c,
            salinity_ppt=payload.salinity_ppt,
            do_mg_l=payload.do_mg_l,
            ph=payload.ph,
            notes=payload.notes,
            retest_ticket_id=open_ticket.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    # 无未关闭工单：若最近两份（不含本次）盐度已均 >= 35，本次即第三份，
    # 必须先生成复测工单后按复测样处理。
    prior_two = salinity.latest_two_samples(db, payload.pond_id)
    if salinity.is_consecutive_high(prior_two):
        raise HTTPException(
            status_code=400,
            detail=(
                "该塘最近两份水质样盐度均 ≥ "
                f"{salinity.TRIGGER_SALINITY:g} ppt，禁止新建第三份；"
                "请先生成复测工单，再补一份盐度 < "
                f"{salinity.RETEST_PASS_MAX:g} ppt 的复测样"
            ),
        )

    item = WaterSample(
        pond_id=payload.pond_id,
        sampled_at=payload.sampled_at,
        temp_c=payload.temp_c,
        salinity_ppt=payload.salinity_ppt,
        do_mg_l=payload.do_mg_l,
        ph=payload.ph,
        notes=payload.notes,
    )
    db.add(item)
    db.flush()

    # 本次与上一份构成连续两份高盐（>= 35）：自动生成复测工单，
    # 此后该塘常规采样即被工单拦截，只能补一份 < 32 的复测样。
    latest_two = salinity.latest_two_samples(db, payload.pond_id)
    if salinity.is_consecutive_high(latest_two):
        salinity.create_ticket(db, payload.pond_id)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(WaterSample).filter(WaterSample.id == sample_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="水质样不存在")
    if item.retest_ticket_id is not None:
        raise HTTPException(
            status_code=400,
            detail="复测样关联复测工单，不可删除；如需调整请先在工单中处理",
        )
    db.delete(item)
    db.commit()
