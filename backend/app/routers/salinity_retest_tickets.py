from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.pond import Pond
from app.models.salinity_retest_ticket import SalinityRetestTicket
from app.models.user import User
from app.schemas.salinity_retest_ticket import (
    PondSalinityStatus,
    SalinityRetestTicketOut,
    TicketClose,
)
from app.services import salinity

router = APIRouter(
    prefix="/api/salinity-retest-tickets", tags=["salinity-retest-tickets"]
)


def _serialize(ticket, db: Session) -> dict:
    passing = salinity.passing_retest_sample(db, ticket.id)
    return {
        "id": ticket.id,
        "pond_id": ticket.pond_id,
        "pond_code": ticket.pond.pond_code if ticket.pond else None,
        "triggered_at": ticket.triggered_at,
        "closed_at": ticket.closed_at,
        "close_note": ticket.close_note,
        "retest_sample_id": passing.id if passing else None,
        "retest_salinity": passing.salinity_ppt if passing else None,
    }


@router.get("/pond-status", response_model=PondSalinityStatus)
def pond_status(
    pond_id: int = Query(..., alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """某塘当前的采样放行/拦截状态，供前端展示拦截原因。"""
    open_ticket = salinity.get_open_ticket(db, pond_id)
    if open_ticket is not None:
        used = salinity.count_retest_samples(db, open_ticket.id) >= 1
        if used:
            reason = (
                "已登记复测样，未关闭工单前禁止继续采样；"
                "复测盐度已低于 32，请先关闭工单"
            )
            allow = False
            phase = "awaiting_close"
        else:
            reason = "高盐复测工单处理中：仅可登记一份复测样，且盐度须低于 32 ppt"
            allow = True
            phase = "awaiting_retest"
        return PondSalinityStatus(
            pond_id=pond_id,
            blocked=not allow,
            can_create_sample=allow,
            can_create_ticket=False,
            phase=phase,
            open_ticket_id=open_ticket.id,
            reason=reason,
        )

    latest_two = salinity.latest_two_samples(db, pond_id)
    if salinity.is_consecutive_high(latest_two):
        return PondSalinityStatus(
            pond_id=pond_id,
            blocked=True,
            can_create_sample=False,
            can_create_ticket=True,
            phase="needs_ticket",
            open_ticket_id=None,
            reason=(
                "最近两份水质样盐度均 ≥ 35 ppt，禁止新建第三份；"
                "请先生成复测工单"
            ),
        )

    return PondSalinityStatus(
        pond_id=pond_id,
        blocked=False,
        can_create_sample=True,
        can_create_ticket=False,
        phase="normal",
        open_ticket_id=None,
        reason=None,
    )


@router.get("", response_model=List[SalinityRetestTicketOut])
def list_tickets(
    open_only: bool = Query(False, alias="openOnly"),
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(SalinityRetestTicket)
    if open_only:
        q = q.filter(SalinityRetestTicket.closed_at.is_(None))
    if pond_id is not None:
        q = q.filter(SalinityRetestTicket.pond_id == pond_id)
    tickets = q.order_by(
        SalinityRetestTicket.closed_at.is_(None).desc(),
        SalinityRetestTicket.triggered_at.desc(),
    ).all()
    return [_serialize(t, db) for t in tickets]


@router.post(
    "",
    response_model=SalinityRetestTicketOut,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    pond_id: int = Query(..., alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")

    existing = salinity.get_open_ticket(db, pond_id)
    if existing is not None:
        raise HTTPException(status_code=400, detail="该塘已有未关闭的复测工单")

    latest_two = salinity.latest_two_samples(db, pond_id)
    if not salinity.is_consecutive_high(latest_two):
        raise HTTPException(
            status_code=400,
            detail=(
                f"仅当最近两份水质样盐度均 ≥ {salinity.TRIGGER_SALINITY:g} ppt "
                "时才可生成复测工单"
            ),
        )

    ticket = salinity.create_ticket(db, pond_id)
    db.commit()
    db.refresh(ticket)
    return _serialize(ticket, db)


@router.post("/{ticket_id}/close", response_model=SalinityRetestTicketOut)
def close_ticket(
    ticket_id: int,
    payload: TicketClose,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = (
        db.query(SalinityRetestTicket)
        .filter(SalinityRetestTicket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="复测工单不存在")
    if ticket.closed_at is not None:
        raise HTTPException(status_code=400, detail="工单已关闭")

    passing = salinity.passing_retest_sample(db, ticket.id)
    if passing is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"须先登记一份盐度低于 {salinity.RETEST_PASS_MAX:g} ppt 的复测样，"
                "方可关闭工单"
            ),
        )

    ticket.closed_at = datetime.now(timezone.utc)
    ticket.close_note = payload.close_note
    db.commit()
    db.refresh(ticket)
    return _serialize(ticket, db)
