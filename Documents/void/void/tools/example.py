"""Example tool — proves the tool-calling loop works."""

import datetime
import json

from void.tools.registry import register


def get_time(tz: str = "UTC") -> dict:
    """Current UTC time — real impl would use pytz/zoneinfo."""
    # ponytail: naive UTC only, zoneinfo/pytz when TZ support matters
    now = datetime.datetime.now(datetime.timezone.utc)
    return {"time": now.isoformat(), "tz": tz, "note": "UTC only for now"}


register(
    name="get_time",
    schema={
        "name": "get_time",
        "description": "Current time in ISO format",
        "parameters": {
            "type": "object",
            "properties": {
                "tz": {"type": "string", "description": "Timezone hint (currently ignored)"},
            },
            "required": [],
        },
    },
    handler=get_time,
)
