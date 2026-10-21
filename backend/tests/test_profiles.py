from uuid import UUID

import pytest
from sqlalchemy import select, func

from app.models import User, Driver, DriverVerification
from app.verify_driver import set_verification
from test_drivers import driver_account, online_driver, VEHICLE


@pytest.mark.parametrize("role", ["rider", "driver"])
def test_own_profile_updates_persist_without_changing_authentication(client, account, db, role):
    account["role"] = role
    registered = client.post("/api/auth/register", json=account).json()
    stored = db.get(User, UUID(registered["id"]))
    password_hash = stored.password_hash
    payload = {"name": "  Updated Name  ", "phone": "+91 98765-43210", "profile_pic": "https://images.example.com/avatar.png"}
    result = client.post("/api/auth/profile", json=payload)
    assert result.status_code == 200
    assert result.json()["name"] == "Updated Name" and result.json()["phone"] == "+919876543210"
    assert result.json()["profile_pic"] == payload["profile_pic"]
    assert result.json()["email"] == account["email"] and result.json()["role"] == role
    assert stored.password_hash == password_hash
    assert client.get("/api/auth/me").json() == result.json()
    assert client.post("/api/auth/profile", json={"name": "Updated Name", "phone": "", "profile_pic": ""}).json()["phone"] is None


@pytest.mark.parametrize("changes", [
    {"role": "driver"}, {"email": "other@example.com"}, {"id": "other"}, {"verified": True},
    {"name": "  "}, {"phone": "not-a-phone"}, {"phone": 123},
    {"profile_pic": "javascript:alert(1)"}, {"profile_pic": "http://example.com/p.png"},
    {"profile_pic": "https://user:pass@example.com/p.png"},
])
def test_profile_cannot_change_identity_or_store_invalid_fields(client, account, changes):
    client.post("/api/auth/register", json=account)
    assert client.post("/api/auth/profile", json={"name": "Test", **changes}).status_code == 422
    assert client.get("/api/auth/me").json()["name"] == account["name"]


def test_profile_requires_session_origin_and_unique_phone(client, account):
    body = {"name": "Updated", "phone": "+919876543210"}
    assert client.post("/api/auth/profile", json=body).status_code == 401
    client.post("/api/auth/register", json=account)
    assert client.post("/api/auth/profile", json=body, headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.post("/api/auth/profile", json=body).status_code == 200
    client.post("/api/auth/logout")
    account["email"] = "second-profile@example.com"
    client.post("/api/auth/register", json=account)
    assert client.post("/api/auth/profile", json=body).status_code == 409
    assert client.get("/api/auth/me").json()["name"] == account["name"]


def test_operator_approval_is_audited_and_vehicle_edits_revoke_it(client, online_driver, db):
    driver_id = UUID(online_driver["id"])
    with pytest.raises(ValueError, match="differs"):
        set_verification(db, driver_id, approved=True, plate="WRONG", operator="test-operator", reason="Reviewed vehicle")
    driver = set_verification(db, driver_id, approved=True, plate=VEHICLE["plate"], operator="test-operator", reason="Reviewed demo vehicle")
    assert driver.verified is True
    audit = db.scalar(select(DriverVerification).where(DriverVerification.driver_id == driver_id))
    assert audit.approved and audit.vehicle_info == VEHICLE and audit.created_at is not None
    assert client.get("/api/drivers/me").json()["verified"] is True
    assert client.put("/api/drivers/me", json={"vehicle_info": VEHICLE, "verified": True}).status_code == 422
    # An identical save keeps approval. A changed plate invalidates the reviewed vehicle.
    client.put("/api/drivers/me", json={"vehicle_info": VEHICLE})
    assert db.get(Driver, driver_id).verified
    response = client.put("/api/drivers/me", json={"vehicle_info": {**VEHICLE, "plate": "NEW-DEMO-001"}})
    assert response.status_code == 200 and response.json()["verified"] is False
    audits = list(db.scalars(select(DriverVerification).where(DriverVerification.driver_id == driver_id)))
    assert len(audits) == 2 and {record.approved for record in audits} == {True, False}
    set_verification(db, driver_id, approved=False, plate="NEW-DEMO-001", operator="test-operator", reason="Review withdrawn")
    assert db.scalar(select(func.count()).select_from(DriverVerification)) == 3
