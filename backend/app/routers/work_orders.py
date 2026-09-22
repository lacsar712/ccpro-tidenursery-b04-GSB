from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.pond import Pond
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.work_order import WorkOrderClose, WorkOrderCreate, WorkOrderOut
from app.services import retest

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


@router.get("", response_model=List[WorkOrderOut])
def list_work_orders(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    status_filter: Optional[Literal["open", "closed"]] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(WorkOrder)
    if pond_id is not None:
        q = q.filter(WorkOrder.pond_id == pond_id)
    if status_filter == "open":
        q = q.filter(WorkOrder.closed_at.is_(None))
    elif status_filter == "closed":
        q = q.filter(WorkOrder.closed_at.is_not(None))
    items = q.order_by(WorkOrder.triggered_at.desc(), WorkOrder.id.desc()).all()
    return [WorkOrderOut.build(w) for w in items]


@router.post("", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")
    if retest.open_work_order(db, payload.pond_id) is not None:
        raise HTTPException(
            status_code=400, detail="该塘口已存在未关闭的复测工单，请勿重复创建"
        )
    if not retest.both_high(retest.latest_two_samples(db, payload.pond_id)):
        raise HTTPException(
            status_code=400,
            detail="该塘口最近两次水样盐度未同时达到 35 ppt，暂不符合复测工单生成条件",
        )
    wo = WorkOrder(pond_id=payload.pond_id)
    db.add(wo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="该塘口已存在未关闭的复测工单，请勿重复创建"
        )
    db.refresh(wo)
    return WorkOrderOut.build(wo)


@router.post("/{work_order_id}/close", response_model=WorkOrderOut)
def close_work_order(
    work_order_id: int,
    payload: WorkOrderClose,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="复测工单不存在")
    if wo.closed_at is not None:
        raise HTTPException(status_code=400, detail="该复测工单已关闭，请勿重复操作")
    wo.closed_at = datetime.now(timezone.utc)
    wo.close_note = payload.close_note.strip()
    db.commit()
    db.refresh(wo)
    return WorkOrderOut.build(wo)
