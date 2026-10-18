"""Loopback-only SMTP catcher. Saves private .eml files; never forwards mail."""
import asyncio
import os
from pathlib import Path
from uuid import uuid4

from aiosmtpd.controller import Controller


class Capture:
    async def handle_DATA(self, server, session, envelope):
        directory = Path(__file__).resolve().parents[2] / "tmp" / "mail"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / f"receipt-{uuid4()}.eml"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(envelope.original_content)
        print(f"Captured locally: {path.name}", flush=True)
        return "250 Captured locally; not delivered to the internet"


async def main():
    controller = Controller(Capture(), hostname="127.0.0.1", port=1025, data_size_limit=2 * 1024 * 1024)
    controller.start()
    print("Local mail catcher on 127.0.0.1:1025; private messages in tmp/mail/.", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        controller.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
