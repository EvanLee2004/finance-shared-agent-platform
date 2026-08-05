"""ID generation — UUID4 as TEXT (design allows ULID or UUID)."""

from __future__ import annotations

import uuid


def new_id() -> str:
    return str(uuid.uuid4())
