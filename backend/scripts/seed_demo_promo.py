"""Create one local learning promo without changing or extending an existing code."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import PromoCode


def main():
    with Session(get_engine()) as db:
        if db.scalar(select(PromoCode.id).where(PromoCode.code == "WELCOME10")):
            print("WELCOME10 already exists; its rules, usage and expiry were not changed.")
            return
        now = datetime.now(timezone.utc)
        db.add(PromoCode(code="WELCOME10", percent_off=10, min_fare=Decimal("80.00"),
                         max_discount=Decimal("50.00"), max_uses=100, per_user_limit=1,
                         starts_at=now, expires_at=now + timedelta(days=30)))
        db.commit()
        print("Created WELCOME10: 10% off, up to INR 50, minimum fare INR 80, one use per rider, 100 total uses, valid 30 days.")


if __name__ == "__main__":
    main()
