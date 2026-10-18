"""Celery receipt worker: only a job UUID crosses Redis, not email/PDF content."""
from datetime import datetime, timezone
from email.message import EmailMessage
import smtplib
import ssl
from uuid import UUID

from celery import Celery
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_engine
from app.models import ReceiptEmail
from app.receipts import render_receipt_pdf

settings = get_settings()
celery_app = Celery("cab_booking_receipts", broker=(settings.celery_broker_url or settings.redis_url).get_secret_value())
celery_app.conf.update(
    task_default_queue="receipts", task_serializer="json", accept_content=["json"],
    task_ignore_result=True, task_store_errors_even_if_ignored=False,
    broker_connection_timeout=2, broker_connection_retry_on_startup=True,
    broker_transport_options={"global_keyprefix": settings.celery_key_prefix,
                              "socket_connect_timeout": 2, "socket_timeout": 2},
    worker_prefetch_multiplier=1, worker_hijack_root_logger=False,
    timezone="UTC", enable_utc=True,
)


def deliver_message(job, pdf):
    settings = get_settings()
    message = EmailMessage()
    message["From"] = str(settings.smtp_from)
    message["To"] = job.recipient
    message["Subject"] = "Your Cab Booking Platform trip document"
    message["Message-ID"] = f"<receipt-{job.id}@cab-booking.example>"
    message.set_content("Your completed-trip document is attached. It records the payment status at request time. "
                        "This is an internship test app; trip completion alone is not proof of payment.")
    message.add_attachment(pdf, maintype="application", subtype="pdf", filename=f"ride-{job.ride_id}.pdf")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


def deliver_receipt(job_id, engine, send=deliver_message):
    """Return whether a bounded retry is needed. A row lock serializes duplicates."""
    with Session(engine) as db:
        job = db.scalar(select(ReceiptEmail).where(ReceiptEmail.id == UUID(job_id)).with_for_update())
        if job is None or job.status == "sent" or job.attempts >= 3:
            return False
        if not get_settings().receipt_email_enabled:
            job.status = "failed"
            db.commit()
            return False
        job.attempts += 1
        job.last_attempt_at = datetime.now(timezone.utc)
        try:
            pdf = render_receipt_pdf(job.snapshot)
            send(job, pdf)
        except (smtplib.SMTPException, OSError, ImportError, RuntimeError, ValueError):
            # Do not persist/log provider text, credentials, recipient, or PDF data.
            job.status = "queued" if job.attempts < 3 else "failed"
            db.commit()
            return job.attempts < 3
        job.status = "sent"
        job.sent_at = datetime.now(timezone.utc)
        db.commit()
        return False


@celery_app.task(bind=True, name="cab_booking.send_receipt_email", max_retries=2,
                 ignore_result=True, acks_late=True)
def send_receipt_email(self, job_id):
    try:
        retry = deliver_receipt(job_id, get_engine())
    except Exception:
        # Bound infrastructure retries and avoid serializing DB/provider exceptions.
        raise self.retry(countdown=5 * (2 ** self.request.retries), exc=RuntimeError("Receipt worker unavailable.")) from None
    if retry:
        raise self.retry(countdown=5 * (2 ** self.request.retries), exc=RuntimeError("Receipt delivery will be retried.")) from None
