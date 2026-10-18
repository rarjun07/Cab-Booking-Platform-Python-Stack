"""Run in your own terminal to save test credentials without echoing them."""
from getpass import getpass
from pathlib import Path
import os
import tempfile

from dotenv import dotenv_values, set_key


def main():
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.exists():
        raise SystemExit("Configure the local backend .env first, following the authentication guide.")
    print("Enter Stripe SANDBOX/TEST credentials. Input is hidden; do not paste keys in chat.")
    entries = {}
    for key, prefix in [("STRIPE_SECRET_KEY", "sk_test_"), ("STRIPE_PUBLISHABLE_KEY", "pk_test_"), ("STRIPE_WEBHOOK_SECRET", "whsec_")]:
        value = getpass(f"{key}: ").strip()
        if not value.startswith(prefix) or "REPLACE" in value or "\n" in value or "\r" in value:
            raise SystemExit(f"Invalid {key}; expected a real test value starting with {prefix}. No changes saved.")
        entries[key] = value
    local = dotenv_values(path)
    if any(key in local for key in entries):
        answer = input("Replace the existing local Stripe test configuration? [y/N]: ").strip().lower()
        if answer != "y":
            raise SystemExit("No changes saved.")
    descriptor, temporary = tempfile.mkstemp(prefix=".env.payments-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as file:
            file.write(path.read_text())
        for key, value in entries.items():
            set_key(temporary, key, value)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print("Saved test configuration to ignored backend/.env with owner-only permissions.")
    print("Restart FastAPI and keep the matching Stripe webhook listener running.")


if __name__ == "__main__":
    main()
