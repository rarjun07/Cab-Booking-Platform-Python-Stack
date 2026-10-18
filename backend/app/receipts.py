"""Server-owned receipt data and escaped, offline-only WeasyPrint rendering."""
from datetime import datetime, timezone
from html import escape

from sqlalchemy import func, select

from app.models import Payment, PromoRedemption, User


def receipt_snapshot(ride, db):
    # One database snapshot keeps a newly applied promo and its fare together,
    # including when the caller loaded this ride before the promo committed.
    trip = type(ride)
    ride, payment, promo, x, y, dx, dy = db.execute(select(
        trip, Payment, PromoRedemption,
        func.ST_X(trip.pickup_point), func.ST_Y(trip.pickup_point),
        func.ST_X(trip.drop_point), func.ST_Y(trip.drop_point),
    ).outerjoin(Payment, Payment.ride_id == trip.id)
     .outerjoin(PromoRedemption, PromoRedemption.ride_id == trip.id)
     .where(trip.id == ride.id).execution_options(populate_existing=True)).one()
    rider = db.get(User, ride.rider_id)
    driver = db.get(User, ride.driver_id) if ride.driver_id else None
    amount = payment.amount if payment else ride.fare_actual if ride.fare_actual is not None else ride.fare_estimate
    snapshot = {
        "ride_id": str(ride.id), "rider": rider.name, "driver": driver.name if driver else "Not recorded",
        "requested_at": ride.created_at.isoformat(), "pickup": f"{y:.6f}, {x:.6f}",
        "destination": f"{dy:.6f}, {dx:.6f}", "amount": f"{amount:.2f}",
        "amount_label": "Invoice amount" if payment else "Final fare" if ride.fare_actual is not None else "Estimated fare",
        "distance": f"{ride.distance_meters / 1000:.2f} km" if ride.distance_meters is not None else "Not recorded",
        "duration": f"{ride.duration_secs / 60:.1f} min" if ride.duration_secs is not None else "Not recorded",
        "payment_status": payment.status if payment else "not_paid",
        "paid_at": payment.paid_at.isoformat() if payment and payment.paid_at else None,
    }
    if promo:
        snapshot.update(promo_code=promo.code, base_amount=f"{promo.base_amount:.2f}", discount_amount=f"{promo.discount_amount:.2f}")
    return snapshot


def no_external_resources(url, *args, **kwargs):
    raise ValueError("Receipt rendering does not fetch external resources.")


def render_receipt_pdf(snapshot):
    # No user HTML, remote images, stylesheets, fonts, or local file URLs.
    from weasyprint import HTML

    value = lambda key: escape(str(snapshot[key]))
    paid = snapshot["payment_status"] == "succeeded"
    title = "Test payment receipt" if paid else "Trip statement"
    note = ("Payment is recorded as succeeded in the application's test-payment ledger."
            if paid else "Trip completion does not confirm payment. This statement is not proof of payment.")
    requested = datetime.fromisoformat(snapshot["requested_at"]).astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    paid_at = escape(snapshot["paid_at"] or "Not recorded")
    promo_rows = (f'<tr><th>Before discount</th><td>INR {value("base_amount")}</td></tr>'
                  f'<tr><th>Promo {value("promo_code")}</th><td>- INR {value("discount_amount")}</td></tr>') if snapshot.get("promo_code") else ""
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>{title}</title>
    <style>
    @page {{ size:A4; margin:20mm; @bottom-center {{ content:'Cab Booking Platform | Learning project | ' counter(page); font:9pt sans-serif; color:#60706c; }} }}
    body {{ font:11pt sans-serif; line-height:1.5; color:#172a28; }}
    .brand {{ font-size:10pt; letter-spacing:2px; text-transform:uppercase; color:#52665e; }}
    h1 {{ font-size:29pt; line-height:1.2; margin:12pt 0 7pt; }}
    h2 {{ font-size:12pt; margin:22pt 0 8pt; }}
    .reference {{ font-size:9pt; color:#52665e; overflow-wrap:anywhere; }}
    .amount {{ background:#edf3ef; padding:16pt; margin-top:24pt; border-left:4pt solid #456854; }}
    .amount strong {{ display:block; font-size:27pt; margin-top:4pt; }}
    table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
    th,td {{ padding:6pt 0; border-bottom:1px solid #dce4df; vertical-align:top; text-align:left; overflow-wrap:anywhere; }}
    th {{ width:32%; color:#52665e; font-weight:normal; padding-right:10pt; }}
    .note {{ margin-top:16pt; padding:10pt; border:1px solid #dce4df; font-size:10pt; }}
    .footer {{ font-size:9pt; color:#52665e; margin-top:18pt; }}
    </style><body><p class="brand">Cab Booking Platform</p><h1>{title}</h1>
    <p class="reference">Ride reference: {value('ride_id')}</p>
    <div class="amount">{value('amount_label')}<strong>INR {value('amount')}</strong></div>
    <h2>Trip details</h2><table>{promo_rows}<tr><th>Trip status</th><td>Completed</td></tr>
    <tr><th>Requested</th><td>{requested}</td></tr>
    <tr><th>Rider</th><td>{value('rider')}</td></tr><tr><th>Driver</th><td>{value('driver')}</td></tr>
    <tr><th>Pickup</th><td>{value('pickup')}</td></tr><tr><th>Destination</th><td>{value('destination')}</td></tr>
    <tr><th>Route estimate</th><td>{value('distance')} / {value('duration')}</td></tr>
    <tr><th>Payment status</th><td>{value('payment_status').replace('_',' ')}</td></tr>
    <tr><th>Payment recorded</th><td>{paid_at}</td></tr></table>
    <p class="note">{note} All payments in this internship app use test mode; no real money is represented.</p>
    <p class="footer">Coordinates use latitude, longitude. Route distance and time are booking estimates, not measured trip usage.
    This learning-project document is not a tax invoice. Generated {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}.</p>
    </body></html>"""
    return HTML(string=html, url_fetcher=no_external_resources).write_pdf()
