"""Stripe test-mode adapter; errors never expose credentials or client secrets."""
from typing import Annotated

from fastapi import Depends, HTTPException
import stripe

from app.config import get_settings


def payment_settings():
    settings = get_settings()
    if not (settings.stripe_secret_key and settings.stripe_publishable_key and settings.stripe_webhook_secret):
        raise HTTPException(503, "Test payments are not configured yet.")
    return settings


class StripeGateway:
    def client(self):
        settings = payment_settings()
        return stripe.StripeClient(settings.stripe_secret_key.get_secret_value(),
                                   http_client=stripe.RequestsClient(timeout=5), max_network_retries=1)

    def create(self, payment, ride):
        try:
            return self.client().v1.payment_intents.create(
                {"amount": int(payment.amount * 100), "currency": payment.currency,
                 "payment_method_types": ["card"], "capture_method": "automatic",
                 "metadata": {"project": "cab-booking-platform", "payment_id": str(payment.id),
                              "ride_id": str(ride.id), "rider_id": str(ride.rider_id)}},
                options={"idempotency_key": f"cab-booking-payment:{payment.id}"}).to_dict()
        except stripe.StripeError:
            raise HTTPException(503, "Could not prepare the test payment. Please retry.") from None

    def retrieve(self, intent_id):
        try:
            return self.client().v1.payment_intents.retrieve(intent_id).to_dict()
        except stripe.StripeError:
            raise HTTPException(503, "Could not verify the test payment. Please retry.") from None

    def create_topup(self, topup):
        try:
            return self.client().v1.payment_intents.create(
                {"amount": int(topup.amount * 100), "currency": topup.currency,
                 "payment_method_types": ["card"], "capture_method": "automatic",
                 "metadata": {"project": "cab-booking-platform", "kind": "wallet_topup",
                              "wallet_topup_id": str(topup.id), "user_id": str(topup.user_id)}},
                options={"idempotency_key": f"cab-booking-wallet:{topup.id}"}).to_dict()
        except stripe.StripeError:
            raise HTTPException(503, "Could not prepare the test top-up. Please retry.") from None


def get_payment_gateway():
    return StripeGateway()


Gateway = Annotated[StripeGateway, Depends(get_payment_gateway)]
