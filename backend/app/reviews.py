"""Completed-trip reviews with private reads and serialized aggregate updates."""
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth import DB, check_origin
from app.events import Events
from app.history import Account, completed_ride
from app.models import Review, User
from app.review_schemas import RatingSummary, ReviewInput, ReviewPublic, TripReviews

router = APIRouter(prefix="/api", tags=["Ratings and reviews"])


def rounded(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def rating_summary(user, db):
    # A single aggregate statement keeps average and count on the same DB snapshot.
    average, count = db.execute(select(func.avg(Review.rating), func.count(Review.id))
                                .where(Review.rated_id == user.id)).one()
    return RatingSummary(user_id=user.id, name=user.name, role=user.role,
                         average=rounded(average) if count else None, count=count)


def counterpart(ride, user, db, *, lock=False):
    target_id = ride.driver_id if user.role == "rider" else ride.rider_id
    if target_id is None or target_id == user.id:
        return None
    query = select(User).where(User.id == target_id, User.role == ("driver" if user.role == "rider" else "rider"))
    if lock:
        # FOR NO KEY UPDATE serializes the cached average while allowing the
        # foreign-key KEY SHARE checks on participant IDs in opposite reviews.
        query = query.with_for_update(key_share=True).execution_options(populate_existing=True)
    return db.scalar(query)


@router.get("/ratings/me", response_model=RatingSummary)
def my_rating(user: Account, db: DB):
    return rating_summary(user, db)


@router.get("/rides/{ride_id}/reviews", response_model=TripReviews)
def trip_reviews(ride_id: UUID, user: Account, db: DB):
    ride = completed_ride(ride_id, user, db, purpose="Reviews")
    target = counterpart(ride, user, db)
    if target is None:
        return TripReviews(counterpart=None, submitted=None, received=None, can_review=False,
                           reason="This trip has no available counterpart to review.")
    given = db.scalar(select(Review).where(Review.ride_id == ride.id, Review.rater_id == user.id,
                                         Review.rated_id == target.id))
    received = db.scalar(select(Review).where(Review.ride_id == ride.id, Review.rater_id == target.id,
                                            Review.rated_id == user.id))
    return TripReviews(counterpart=rating_summary(target, db),
                       submitted=ReviewPublic.model_validate(given) if given else None,
                       received=ReviewPublic.model_validate(received) if received else None, can_review=given is None)


@router.post("/rides/{ride_id}/reviews", response_model=ReviewPublic, status_code=201,
             dependencies=[Depends(check_origin)])
def submit_review(ride_id: UUID, data: ReviewInput, user: Account, db: DB, response: Response, events: Events):
    # Lock this ride to serialize duplicate submissions. Different rides can be
    # rated together, so also lock the recipient before inserting/recalculating.
    ride = completed_ride(ride_id, user, db, lock=True, purpose="Reviews")
    target = counterpart(ride, user, db, lock=True)
    if target is None:
        raise HTTPException(409, "This trip has no available counterpart to review.")
    previous = db.scalar(select(Review).where(Review.ride_id == ride.id, Review.rater_id == user.id))
    if previous:
        if previous.rated_id == target.id and previous.rating == data.rating and previous.comment == data.comment:
            response.status_code = 200
            return previous
        raise HTTPException(409, "You already reviewed this trip. Reviews cannot be changed.")
    review = Review(ride_id=ride.id, rater_id=user.id, rated_id=target.id, rating=data.rating, comment=data.comment)
    db.add(review)
    try:
        db.flush()
        target.rating_avg = rounded(db.scalar(select(func.avg(Review.rating)).where(Review.rated_id == target.id)))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This review could not be saved. Refresh the trip reviews.") from None
    db.refresh(review)
    events.review_changed(ride)
    return review
