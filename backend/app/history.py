"""Participant-only history, completed-trip PDF downloads, and email requests."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select, tuple_

from app.auth import DB, check_origin, get_current_user
from app.config import get_settings
from app.history_schemas import EmailReceiptInput, HistoryPage, HistoryRide, ReceiptEmailPublic
from app.models import Payment, ReceiptEmail, Ride, User
from app.receipts import receipt_snapshot, render_receipt_pdf

router = APIRouter(prefix="/api", tags=["History and receipts"])
Account = Annotated[User, Depends(get_current_user)]


def participant(user):
    return Ride.rider_id == user.id if user.role == "rider" else Ride.driver_id == user.id


def completed_ride(ride_id, user, db, *, lock=False):
    query = select(Ride).where(Ride.id == ride_id, participant(user))
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    ride = db.scalar(query)
    if ride is None:
        raise HTTPException(404, "Ride not found.")
    if ride.status != "completed":
        raise HTTPException(409, "Receipts are available after the trip is completed.")
    return ride


@router.get("/rides/history", response_model=HistoryPage)
def history(user: Account, db: DB, limit: Annotated[int, Query(ge=1, le=50)] = 10, cursor: UUID | None = None):
    filters = [participant(user), Ride.status.in_(("completed", "cancelled"))]
    if cursor:
        anchor = db.scalar(select(Ride).where(Ride.id == cursor, *filters))
        if anchor is None:
            raise HTTPException(422, "Invalid history cursor.")
        filters.append(tuple_(Ride.created_at, Ride.id) < tuple_(anchor.created_at, anchor.id))
    rows = db.execute(select(Ride, Payment, func.ST_X(Ride.pickup_point), func.ST_Y(Ride.pickup_point),
                             func.ST_X(Ride.drop_point), func.ST_Y(Ride.drop_point))
                      .outerjoin(Payment, Payment.ride_id == Ride.id).where(*filters)
                      .order_by(Ride.created_at.desc(), Ride.id.desc()).limit(limit + 1)).all()
    items = [HistoryRide(id=r.id, status=r.status, driver_id=r.driver_id, created_at=r.created_at,
                         pickup={"latitude": y, "longitude": x}, destination={"latitude": dy, "longitude": dx},
                         fare_estimate=r.fare_estimate, fare_actual=r.fare_actual, distance_meters=r.distance_meters,
                         duration_secs=r.duration_secs, payment_status=p.status if p else None,
                         payment_amount=p.amount if p else None, receipt_available=r.status == "completed")
             for r, p, x, y, dx, dy in rows[:limit]]
    return HistoryPage(items=items, next_cursor=items[-1].id if len(rows) > limit else None)


@router.get("/rides/{ride_id}/receipt.pdf")
def download_receipt(ride_id: UUID, user: Account, db: DB):
    ride = completed_ride(ride_id, user, db)
    try:
        pdf = render_receipt_pdf(receipt_snapshot(ride, db))
    except (ImportError, OSError, RuntimeError, ValueError):
        raise HTTPException(503, "PDF generation is unavailable. Check the local WeasyPrint setup.") from None
    return Response(pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="ride-{ride.id}.pdf"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })


def document_key(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def current_email(ride, user, db, snapshot):
    return db.scalar(select(ReceiptEmail).where(ReceiptEmail.ride_id == ride.id, ReceiptEmail.user_id == user.id,
                                               ReceiptEmail.document_key == document_key(snapshot)))


@router.get("/receipts/config")
def receipt_config(user: Account):
    return {"email_enabled": get_settings().receipt_email_enabled}


@router.get("/rides/{ride_id}/receipt-email", response_model=ReceiptEmailPublic | None)
def email_status(ride_id: UUID, user: Account, db: DB):
    ride = completed_ride(ride_id, user, db)
    return current_email(ride, user, db, receipt_snapshot(ride, db))


def publish_receipt(job_id):
    from app.tasks import send_receipt_email
    send_receipt_email.apply_async(args=[str(job_id)], retry=False)


def get_receipt_sender():
    return publish_receipt


@router.post("/rides/{ride_id}/receipt-email", response_model=ReceiptEmailPublic,
             dependencies=[Depends(check_origin)])
def request_email(ride_id: UUID, data: EmailReceiptInput, user: Account, db: DB, response: Response,
                  sender=Depends(get_receipt_sender)):
    ride = completed_ride(ride_id, user, db, lock=True)
    if not get_settings().receipt_email_enabled:
        raise HTTPException(503, "Receipt email is not configured. You can still download the PDF.")
    snapshot = receipt_snapshot(ride, db)
    job = current_email(ride, user, db, snapshot)
    if job and job.status == "sent":
        return job
    if job is None:
        job = ReceiptEmail(ride_id=ride.id, user_id=user.id, recipient=user.email,
                           document_key=document_key(snapshot), snapshot=snapshot)
        db.add(job)
    elif job.status == "failed":
        if job.last_attempt_at and job.last_attempt_at > datetime.now(timezone.utc) - timedelta(minutes=1):
            raise HTTPException(429, "Wait one minute before retrying receipt delivery.", headers={"Retry-After": "60"})
        job.status, job.attempts = "queued", 0
    db.commit()  # Durable before Redis; retrying a failed publication reuses this job.
    db.refresh(job)
    try:
        sender(job.id)
    except Exception:
        raise HTTPException(503, "Receipt saved, but the email queue is unavailable. Retry to queue the same receipt.") from None
    response.status_code = 202
    return job
