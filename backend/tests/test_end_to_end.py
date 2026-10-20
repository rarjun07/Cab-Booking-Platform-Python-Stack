"""Day 13: real HTTP/WS/DB/Redis/worker journeys with controlled route/Stripe calls."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
import io
import json
from threading import Barrier
import time
from uuid import UUID, uuid4

import httpx
from pypdf import PdfReader
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from websockets.exceptions import ConnectionClosedError

from app.auth import COOKIE_NAME
from app.models import Driver, Payment, PromoRedemption, ReceiptEmail, Ride, WalletEntry
from journey_support import journey_server, ORIGIN, PARAMS, POINT
from test_wallet_promos import signed_event, success


def saved(response, status=200):
    assert response.status_code == status
    return response.json()


def online(client, point=POINT):
    saved(client.put("/api/drivers/me", json={"vehicle_info": {"make": "Maruti", "model": "Dzire", "plate": "DAY13-DEMO"}}))
    assert saved(client.post("/api/drivers/me/availability", json={"status": "active", "location": point}))["available_for_matching"]


def book(client):
    quote = saved(client.get("/api/rides/estimate", params=PARAMS))
    return saved(client.post("/api/rides/request", json={"quote_token": quote["quote_token"]}), 201), quote


def progress(client, ride, statuses=("arriving", "in_progress", "completed")):
    for status in statuses:
        assert saved(client.post(f"/api/drivers/me/rides/{ride}/status", json={"status": status}))["status"] == status


def event(ws, kind, allowed, ride=None):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        message = json.loads(ws.recv(timeout=max(.01, deadline-time.monotonic())))
        if "ride_id" in message: assert message["ride_id"] in allowed
        if message["type"] == kind and (ride is None or message.get("ride_id") == ride): return message
    pytest.fail("Expected private live event did not arrive.")


def notify(client, intent, event_id=None):
    payload, signature = signed_event(intent, event_id=event_id)
    return saved(client.post("/api/webhooks/stripe", content=payload, headers={"Stripe-Signature": signature}))


def pdf_text(content):
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(content)).pages)


def test_two_rider_driver_journeys_with_receipt_email_promos_reviews_wallet_and_revocation(journey_server):
    env = journey_server
    rider_a, rider_b = env.account("rider-a"), env.account("rider-b")
    driver_a, driver_b = env.account("driver-a", "driver"), env.account("driver-b", "driver")
    outsider = env.account("outsider")
    online(driver_a)
    online(driver_b)
    trip_a, quote_a = book(rider_a)
    trip_b, _ = book(rider_b)
    a, b = trip_a["id"], trip_b["id"]
    duplicate = saved(rider_a.post("/api/rides/request", json={"quote_token": quote_a["quote_token"]}))
    assert duplicate["id"] == a
    for client in (driver_a, driver_b):
        assert {offer["ride"]["id"] for offer in saved(client.get("/api/drivers/me/offers"))} == {a, b}
    ws_a, ws_b = env.websocket(rider_a), env.websocket(rider_b)
    event(ws_a, "ready", {a})
    event(ws_b, "ready", {b})
    saved(driver_a.post(f"/api/drivers/me/rides/{a}/accept"))
    event(ws_a, "ride.changed", {a}, a)
    assert [item["ride"]["id"] for item in saved(driver_b.get("/api/drivers/me/offers"))] == [b]
    assert driver_a.post(f"/api/drivers/me/rides/{b}/accept").status_code == 409
    saved(driver_b.post(f"/api/drivers/me/rides/{b}/accept"))
    event(ws_b, "ride.changed", {b}, b)
    assert driver_b.post(f"/api/drivers/me/rides/{a}/status", json={"status": "arriving"}).status_code == 404
    assert driver_a.post(f"/api/drivers/me/rides/{a}/status", json={"status": "completed"}).status_code == 409
    assert saved(rider_a.get(f"/api/rides/{a}/driver-location"))["location"] == POINT
    progress(driver_a, a)
    event(ws_a, "ride.changed", {a}, a)
    assert saved(rider_a.get(f"/api/rides/{a}/driver-location")) is None
    assert saved(driver_b.get("/api/drivers/me/ride"))["id"] == b
    # The released driver can take another request while the second trip continues.
    trip_c, _ = book(rider_a)
    c = trip_c["id"]
    saved(driver_a.post(f"/api/drivers/me/rides/{c}/accept"))
    progress(driver_b, b)
    progress(driver_a, c)
    for client in (driver_a, driver_b): assert saved(client.get("/api/drivers/me/ride")) is None

    for client, ride in ((rider_a, a), (rider_b, b)):
        promo = saved(client.post(f"/api/rides/{ride}/promo", json={"code": env.campaign}), 201)
        assert promo["discount_amount"] == "10.44" and promo["final_amount"] == "93.94"
        assert saved(client.post(f"/api/rides/{ride}/promo", json={"code": env.campaign})) == promo
        prepared = saved(client.post(f"/api/rides/{ride}/payment-intent", json={}))
        invoice = prepared["payment"]
        assert invoice["amount"] == "93.94" and invoice["status"] == "pending"
        assert saved(client.post(f"/api/rides/{ride}/payment-intent", json={}))["payment"]["id"] == invoice["id"]
        intent = env.payments.keys[invoice["id"]]
        success(env.payments, intent)
        assert saved(client.get(f"/api/rides/{ride}/payment"))["status"] == "pending"
        identifier = "evt_day13" + uuid4().hex
        notify(client, intent, identifier)
        assert notify(client, intent, identifier)["duplicate"]
        assert saved(client.get(f"/api/rides/{ride}/payment"))["status"] == "succeeded"
    for client, ride, stars in ((rider_a, a, 5), (driver_a, a, 4), (rider_b, b, 3), (driver_b, b, 5)):
        saved(client.post(f"/api/rides/{ride}/reviews", json={"rating": stars, "comment": "Journey feedback"}), 201)
    assert saved(driver_a.get("/api/ratings/me"))["average"] == "5.00"
    assert saved(driver_b.get("/api/ratings/me"))["average"] == "3.00"
    assert saved(rider_a.get("/api/ratings/me"))["average"] == "4.00"
    assert saved(rider_b.get("/api/ratings/me"))["average"] == "5.00"
    history_a = saved(rider_a.get("/api/rides/history", params={"limit": 1}))
    assert [row["id"] for row in history_a["items"]] == [c] and history_a["next_cursor"]
    older = saved(rider_a.get("/api/rides/history", params={"limit": 1, "cursor": history_a["next_cursor"]}))
    assert [row["id"] for row in older["items"]] == [a] and older["items"][0]["payment_status"] == "succeeded"
    assert {row["id"] for row in saved(driver_a.get("/api/rides/history"))["items"]} == {a, c}
    assert [row["id"] for row in saved(rider_b.get("/api/rides/history"))["items"]] == [b]
    for suffix in ("status", "driver-location", "payment", "promo", "reviews", "receipt.pdf", "receipt-email"):
        assert outsider.get(f"/api/rides/{a}/{suffix}").status_code == 404
        assert rider_b.get(f"/api/rides/{a}/{suffix}").status_code == 404
    document = rider_a.get(f"/api/rides/{a}/receipt.pdf")
    assert document.status_code == 200
    text = pdf_text(document.content)
    assert "Test payment receipt" in text and "93.94" in text and env.campaign in text
    assert b not in text

    env.start_mail_worker()
    path = f"/api/rides/{a}/receipt-email"
    first = saved(rider_a.post(path, json={}), 202)
    again = rider_a.post(path, json={})
    assert again.status_code in (200, 202) and again.json()["id"] == first["id"]
    message = BytesParser(policy=policy.default).parsebytes(env.messages.get(timeout=25))
    assert str(message["To"]) == env.accounts["rider-a"]["email"]
    attachment, = list(message.iter_attachments())
    assert attachment.get_filename() == f"ride-{a}.pdf"
    emailed = pdf_text(attachment.get_payload(decode=True))
    assert "93.94" in emailed and "Test payment receipt" in emailed and b not in emailed
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with Session(env.engine) as db:
            state = db.get(ReceiptEmail, UUID(first["id"]))
            if state.status == "sent": break
        time.sleep(.05)
    status = saved(rider_a.get(path))
    assert status["status"] == "sent" and status["attempts"] == 1
    assert saved(rider_a.post(path, json={}))["id"] == first["id"]

    retry_key = str(uuid4())
    topup = saved(rider_a.post("/api/wallet/topups", json={"amount": "100.00", "request_key": retry_key}))["topup"]
    assert saved(rider_a.post("/api/wallet/topups", json={"amount": "100.00", "request_key": retry_key}))["topup"]["id"] == topup["id"]
    intent = env.payments.keys[topup["id"]]
    success(env.payments, intent)
    assert saved(rider_a.get("/api/wallet"))["balance"] == "0.00"
    notify(rider_a, intent)
    notify(rider_a, intent)
    event(ws_a, "wallet.changed", {a, c})
    wallet = saved(rider_a.get("/api/wallet"))
    assert wallet["balance"] == "100.00" and len(wallet["entries"]) == 1
    assert saved(rider_b.get("/api/wallet"))["balance"] == "0.00"
    assert rider_b.get(f"/api/wallet/topups/{topup['id']}").status_code == 404
    with Session(env.engine) as db:
        owned = {UUID(value) for value in (a, b, c)}
        assert db.scalar(select(func.count()).select_from(Ride).where(Ride.id.in_(owned))) == 3
        assert db.scalar(select(func.count()).select_from(Payment).where(Payment.ride_id.in_(owned))) == 2
        assert db.scalar(select(func.count()).select_from(PromoRedemption).where(PromoRedemption.ride_id.in_(owned))) == 2
        assert db.scalar(select(func.count()).select_from(WalletEntry).where(WalletEntry.topup_id == UUID(topup["id"]))) == 1
    old_cookie = rider_a.cookies.get(COOKIE_NAME)
    assert rider_a.post("/api/auth/logout").status_code == 204
    rider_a.cookies.set(COOKIE_NAME, old_cookie)
    assert rider_a.get("/api/auth/me").status_code == 401
    assert rider_b.get("/api/auth/me").status_code == 200
    deadline = time.monotonic() + 4
    while True:
        try:
            ws_a.recv(timeout=max(.01, deadline-time.monotonic()))
            assert time.monotonic() < deadline
        except ConnectionClosedError as error:
            assert error.rcvd.code == 4401
            break


@pytest.mark.parametrize("scenario", ["two_drivers_one_ride", "one_driver_two_rides"])
def test_competing_real_http_accepts_preserve_single_assignment(journey_server, scenario):
    env = journey_server
    riders = [env.account("rider-a"), env.account("rider-b")]
    drivers = [env.account("driver-a", "driver"), env.account("driver-b", "driver")]
    for client in drivers: online(client)
    rides = [book(client)[0]["id"] for client in riders]
    tasks = [(0, 0), (1, 0)] if scenario == "two_drivers_one_ride" else [(0, 0), (0, 1)]
    barrier = Barrier(2)
    def accept(index):
        driver, ride = tasks[index]
        with httpx.Client(base_url=env.base, headers={"Origin": ORIGIN}, cookies=drivers[driver].cookies, timeout=8) as client:
            barrier.wait(timeout=3)
            return client.post(f"/api/drivers/me/rides/{rides[ride]}/accept").status_code
    with ThreadPoolExecutor(max_workers=2) as workers: results = list(workers.map(accept, range(2)))
    assert sorted(results) == [200, 409]
    assigned = [saved(client.get(f"/api/rides/{ride}/status")) for client, ride in zip(riders, rides)]
    assert sum(ride["status"] == "accepted" for ride in assigned) == 1
    with Session(env.engine) as db:
        assert db.scalar(select(func.count()).select_from(Ride).where(Ride.id.in_([UUID(value) for value in rides]), Ride.status == "accepted")) == 1


def test_stale_far_and_declined_drivers_cannot_take_the_pending_request(journey_server):
    env = journey_server
    rider = env.account("rider")
    near, far, stale = (env.account(label, "driver") for label in ("near", "far", "stale"))
    online(near)
    online(far, {"latitude": 19.076, "longitude": 72.8777})
    online(stale)
    with Session(env.engine) as db:
        db.get(Driver, UUID(env.accounts["stale"]["id"])).location_updated_at = datetime.now(timezone.utc)-timedelta(hours=1)
        db.commit()
    ride, _ = book(rider)
    path = f"/api/drivers/me/rides/{ride['id']}"
    candidates = saved(rider.get(f"/api/rides/{ride['id']}/drivers"))
    assert [candidate["driver_id"] for candidate in candidates] == [env.accounts["near"]["id"]]
    for client in (far, stale):
        assert saved(client.get("/api/drivers/me/offers")) == []
        assert client.post(path + "/accept").status_code == 409
    assert near.post(path + "/decline").status_code == 204
    assert saved(near.get("/api/drivers/me/offers")) == []
    assert near.post(path + "/accept").status_code == 409
    assert saved(rider.get(f"/api/rides/{ride['id']}/status"))["status"] == "requested"
