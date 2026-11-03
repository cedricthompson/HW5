"""Append-only audit trail for every agent loop step.

output/audit_trail.json is a JSON array. Each run adds events to the end; the
file is never wiped. Writes go to a temp file first, then replace the original,
so a crash can't leave half-written JSON.
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.models import AuditEvent, TeamDeps

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_FIELD_CHARS = 2000  # long tool outputs are cut to keep the file readable

_lock = threading.Lock()


def clip(value: Any) -> Any:
    """Keep audit values JSON-safe and short."""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, default=str)
        return value if len(text) <= MAX_FIELD_CHARS else text[:MAX_FIELD_CHARS] + "...[cut]"
    if isinstance(value, str) and len(value) > MAX_FIELD_CHARS:
        return value[:MAX_FIELD_CHARS] + "...[cut]"
    return value


def record(deps: TeamDeps, step: int, event: str, detail: dict[str, Any], usage: dict[str, int] | None = None) -> None:
    row = AuditEvent(
        timestamp=datetime.now().astimezone().isoformat(timespec="milliseconds"),
        run_id=deps.run_id,
        ticket_id=deps.ticket_id,
        agent=deps.agent,
        parent_agent=deps.parent_agent,
        depth=deps.depth,
        step=step,
        event=event,
        # A finished agent's report is kept whole (it's bounded by the model's reply cap); everything else is clipped.
        detail={k: (v if event == "run_end" and k == "output" else clip(v)) for k, v in detail.items()},
        usage=usage or {},
    )
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        rows = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size else []
        rows.append(row.model_dump())
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rows, indent=2, default=str))
        os.replace(tmp, AUDIT_PATH)
