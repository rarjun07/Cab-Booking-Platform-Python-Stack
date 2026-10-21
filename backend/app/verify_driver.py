"""Trusted local operator command; no browser endpoint can approve a driver."""
import argparse
import getpass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_engine
from app.driver_schemas import VehicleInfo
from app.events import get_event_publisher
from app.models import Driver, DriverVerification, User


def checked_driver(db, driver_id, plate):
    driver = db.scalar(select(Driver).where(Driver.user_id == driver_id).with_for_update())
    if driver is None: raise ValueError("Driver profile not found.")
    if db.get(User, driver_id).role != "driver": raise ValueError("This account is not a driver.")
    vehicle = VehicleInfo.model_validate(driver.vehicle_info)
    if vehicle.plate.strip().upper() != plate.strip().upper():
        raise ValueError("The number plate differs from the reviewed vehicle. Review the current profile again.")
    return driver


def set_verification(db, driver_id, *, approved, plate, operator, reason):
    operator, reason = operator.strip(), reason.strip()
    if not 1 <= len(operator) <= 100 or not 1 <= len(reason) <= 500:
        raise ValueError("Provide an operator and a review reason (up to 500 characters).")
    driver = checked_driver(db, driver_id, plate)
    driver.verified = approved
    db.add(DriverVerification(driver_id=driver_id, approved=approved, vehicle_info=dict(driver.vehicle_info),
                              operator=operator, reason=reason))
    db.commit()
    return driver


def main():
    parser = argparse.ArgumentParser(description="Record a driver vehicle review. Requires trusted database access. Default is dry-run.")
    parser.add_argument("--driver-id", type=UUID, required=True)
    parser.add_argument("--status", choices=("approved", "revoked"), required=True)
    parser.add_argument("--plate", required=True, help="Number plate of the vehicle actually reviewed")
    parser.add_argument("--reason", required=True, help="Review outcome; do not include identity-document numbers or secrets")
    parser.add_argument("--apply", action="store_true", help="Persist this review; omit for a dry-run")
    args = parser.parse_args()
    if not 1 <= len(args.reason.strip()) <= 500:
        parser.error("Provide a review reason of 1-500 characters.")
    try:
        with Session(get_engine()) as db:
            checked_driver(db, args.driver_id, args.plate)
            if not args.apply:
                print(f"Dry-run: would mark driver {args.driver_id} {args.status}. No changes saved.")
                return
            set_verification(db, args.driver_id, approved=args.status == "approved", plate=args.plate,
                             operator=getpass.getuser(), reason=args.reason)
        get_event_publisher().driver_changed(args.driver_id)
        print(f"Driver {args.driver_id}: {args.status}; review saved.")
    except ValueError as error:
        parser.error(str(error))
    except SQLAlchemyError:
        parser.error("Database operation failed. Check connectivity and apply the documented migration first.")


if __name__ == "__main__":
    main()
