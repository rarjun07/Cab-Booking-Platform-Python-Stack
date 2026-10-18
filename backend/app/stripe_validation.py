"""Canonical test-intent validation shared by trip invoices and wallet top-ups."""
import re

from fastapi import HTTPException

INTENT_STATUSES = {"succeeded", "processing", "canceled", "requires_payment_method", "requires_confirmation", "requires_action"}


def validate_test_intent(intent, amount, currency, metadata, linked_id=None):
    if not isinstance(intent, dict):
        raise HTTPException(409, "The test payment does not match the stored request.")
    actual_metadata = intent.get("metadata")
    intent_id = intent.get("id")
    if (intent.get("object") != "payment_intent" or intent.get("livemode") is not False
            or intent.get("status") not in INTENT_STATUSES
            or not isinstance(intent_id, str) or len(intent_id) > 255 or not re.fullmatch(r"pi_[A-Za-z0-9]+", intent_id)
            or type(intent.get("amount")) is not int or intent["amount"] != int(amount * 100)
            or intent.get("currency") != currency or (linked_id and intent_id != linked_id)
            or not isinstance(actual_metadata, dict) or any(actual_metadata.get(key) != value for key, value in metadata.items())):
        raise HTTPException(409, "The test payment does not match the stored request.")
    if intent["status"] == "succeeded" and (type(intent.get("amount_received")) is not int or intent["amount_received"] != int(amount * 100)):
        raise HTTPException(409, "The received test amount does not match the stored request.")


def checkout_secret(intent, *, paid=False):
    if intent["status"] in ("succeeded", "processing") or paid:
        return None
    value = intent.get("client_secret")
    if not isinstance(value, str) or not value.startswith(f'{intent["id"]}_secret_'):
        raise HTTPException(502, "The payment service returned an invalid checkout.")
    return value


def canonical_status(intent):
    return {"succeeded": "succeeded", "processing": "processing", "canceled": "cancelled",
            "requires_payment_method": "failed" if intent.get("last_payment_error") else "pending",
            "requires_confirmation": "pending", "requires_action": "pending"}[intent["status"]]
