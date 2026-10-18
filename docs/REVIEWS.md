# Day 9: ratings and reviews

Day 9 adds completed-trip reviews and rating summaries. Day 8 documentation commit `9f59017d2d4d39453aefb2a1fcd6f0c0e3a61e2f` was verified equal to GitHub before starting, with a clean working tree. No new package, account or secret is needed. Stripe setup remains deferred; reviewing a completed trip does not depend on payment.

## Step 1: understand who can review

After a completed trip, the rider can review its assigned driver, and that driver can review its rider. Requested, accepted, arriving, in-progress and cancelled rides cannot be reviewed. A completed legacy/demo ride without an available counterpart shows an explanatory message instead of a form. Another account receives 404 for the trip's reviews, even if it knows the ride UUID.

The request body contains only a whole-number `rating` from 1 to 5 and an optional `comment` of up to 2,000 characters. The backend chooses the author from the session cookie and the recipient from the ride. Client-supplied account/ride IDs in the body are rejected. Leading/trailing comment whitespace is removed; a blank comment becomes null. Comments are stored as plain text and displayed by React as text, not HTML.

Comments must contain valid Unicode without a null character, so invalid database text is rejected with 422 before any write. Validation responses omit the submitted comment text.

Each participant has one review per trip. An identical normalized retry returns the same review with 200; the first submission returns 201. A different rating/comment after submission returns 409. This prevents a timeout/retry from creating duplicate feedback. The database's existing `(ride_id, rater_id)` unique constraint remains in force. All writes require an allowed Origin and a valid session.

Both participants can read the reviews of their completed trip. Each account can read its own overall rating; the trip panel also shows its counterpart's overall average/count. No API exposes a global feed of private comments or account emails.

## Step 2: understand the average

The review and the recipient's `users.rating_avg` are committed together. The average is recalculated from all reviews received by that user, rounded to two decimal places with half-up rounding: ratings 4, 4 and 5 produce 4.33. The count and average returned by summary endpoints come from one SQL aggregate statement so they use the same database snapshot. A user with no reviews gets `average=null, count=0`; the UI says **No ratings yet**, while the stored numeric cache remains zero.

Two riders can review the same driver at the same time on different trips. Locking only the ride would allow both to overwrite the cached average from incomplete data. The write path therefore locks the trip, then serializes the recipient's average with PostgreSQL `FOR NO KEY UPDATE`. This still permits the foreign-key key-share checks used when the two participants rate each other across different trips. The concurrency tests force those recipient locks to overlap before the inserts and verify that both reviews commit without a deadlock or lost average.

Application writes must use the review API. Administrative SQL edits/inserts bypass this aggregate maintenance and require an explicit recalculation afterward.

## Step 3: apply the migration and run

Use the existing environment and services:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
python -m alembic upgrade head
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m uvicorn app.main:app --reload --no-proxy-headers --ws-max-size 2048
```

Migration `0007_review_timestamps` adds a nullable creation timestamp, then sets its default for future inserts. Existing reviews keep unknown/null dates; their feedback and IDs are preserved. It reconciles each user's derived average from existing reviews, including zero for users with none. Identity fields, password hashes, sessions, rides and invoices are not rewritten. No `create_all` is used.

React, in another terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run dev
```

Keep PostgreSQL and Redis running. The library-path line is for this Mac's existing PDF dependency, not a new reviews dependency. Celery/SMTP are needed only when exercising the earlier email feature.

## Step 4: try both accounts (manual check pending)

1. Use independent browser profiles/windows for rider and driver. Sign in and complete an assigned sample trip using the existing booking/trip controls.
2. As the rider, find that completed trip in **Ride history and trip documents** and click **Ratings and review**.
3. Choose **5 stars**, optionally write a comment, and select **Submit review**. The saved review replaces the form; the driver's average/count appears in the panel.
4. In the driver's window, check **Your rating** and open the same trip's review panel. The rider's feedback should appear. Submit a rating for the rider, then check the rider's own summary.
5. Reload both windows. Saved reviews and averages should remain. **Refresh reviews** and **Refresh history** work when live updates are unavailable.
6. Before submitting a fresh review on another completed trip, type a draft and wait through the 15-second live sync. The draft should remain. Background history refreshes keep the mounted form; explicitly closing it or navigating pages can discard unsaved input.
7. Check that cancelled trips have no review control, unrelated accounts cannot open this trip's reviews, and sign-out removes private account history/reviews.

These browser steps remain unverified after the earlier browser URL-policy rejection. Source inspection, API tests and a successful build are not claimed as a rendered UI pass.

New `review.changed` notifications go only to the rider/driver's private channels after commit. They contain the event type and ride ID only, with no comment/rating/user email in the payload and no shared matching-channel publication. React rereads protected data; periodic sync/reconnect and manual refresh recover missed notifications.

## Endpoints and files

| Endpoint | Result |
| --- | --- |
| `GET /api/ratings/me` | Signed-in account's rating average/count and its own safe identity fields. |
| `GET /api/rides/{id}/reviews` | Completed-trip participant reads counterpart summary, own submitted review, received review and eligibility. |
| `POST /api/rides/{id}/reviews` | `{ "rating": 5, "comment": "Helpful driver" }`; creates or identically reuses the participant's review. |

| File | Purpose |
| --- | --- |
| `backend/app/review_schemas.py` | Strict input, safe review responses and rating summaries. |
| `backend/app/reviews.py` | Ownership/completion checks, recipient selection, duplicate handling and serialized average updates. |
| `backend/alembic/versions/0007_review_timestamps.py` | Preserve legacy feedback/dates and reconcile derived averages. |
| `backend/app/events.py` / `backend/app/realtime.py` | Participant-only review notifications. |
| `frontend/src/RideReviews.jsx` | Rating selector, optional comment, saved/received reviews and own rating summary. |
| `frontend/src/RideHistory.jsx` | Completed-trip review controls and background refresh that keeps open forms mounted. |
| `backend/tests/test_reviews.py` | Validation, private reads, eligibility, retries, averages and five real PostgreSQL concurrency scenarios. |

## Verification

- Final full regression: **184 backend tests passed in 22.89 seconds**, including 27 added review/validation/migration/notification checks. Pip consistency and Alembic drift checks passed; the existing TestClient/HTTPX deprecation warning remains. Earlier targeted review/migration and review/realtime runs also passed.
- Five separate-connection concurrency scenarios cover identical retries, conflicting retries, two riders rating one driver, both directions on one trip, and forced overlapping opposite-direction submissions on two trips.
- Migration tests preserve legacy review IDs/text/ratings and unknown dates, verify new timestamps and reconciled averages, preserve existing account/invoice data, and exercise fresh upgrade/downgrade.
- Real Redis/TCP WebSocket checks cover participant delivery, safe payload projection, no matching-channel publication and unrelated-account rejection. Synthetic committed rows are removed after tests; Redis is not flushed.
- React production build passed (29 modules). Browser interaction remains pending; earlier manual UI checks and user-deferred Stripe verification remain open. No Day 10 wallet/promo work is included.

References: [PostgreSQL 14 row lock modes](https://www.postgresql.org/docs/14/explicit-locking.html#LOCKING-ROWS), [SQLAlchemy locking options](https://docs.sqlalchemy.org/en/21/core/selectable.html#sqlalchemy.sql.expression.Select.with_for_update).
