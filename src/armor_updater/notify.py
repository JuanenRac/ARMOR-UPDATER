# =============================================================================
# ARMOR-UPDATER - Telling that updates exist, without installing anything: notify.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""For a scheduled task (cron, a systemd timer): turns the result of ``status --json`` into one short message and, only when asked with ``--ntfy-url``, sends it to a ntfy topic.

Nothing is installed or updated here. With nothing outdated there is no message at all (a silent run is a good run). The address is the one the owner gives: a plain http(s) URL without
credentials, and the message holds only project names and versions.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

MAX_LISTED = 20
SEND_TIMEOUT_S = 10


def summarize(payload: Mapping[str, Any]) -> tuple[str, str] | None:
    """(title, body) for the projects whose state is OUTDATED, or None when there are none."""
    outdated = [p for p in payload.get("projects", []) if p.get("state") == "OUTDATED"]
    if not outdated:
        return None
    lines = [f"{p['name']}: {p.get('local_version') or '?'} -> {p.get('github_version') or '?'}" for p in outdated[:MAX_LISTED]]
    if len(outdated) > MAX_LISTED:
        lines.append(f"... and {len(outdated) - MAX_LISTED} more")
    title = f"A.R.M.O.R.: {len(outdated)} project{'s' if len(outdated) != 1 else ''} to update"
    return title, "\n".join(lines)


def check_url(url: str) -> str:
    """Only a plain http(s) address is accepted: no credentials in it, no fragment."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ValueError("--ntfy-url must be a plain http(s) address without credentials, e.g. https://ntfy.sh/my-topic")
    return url


def send(url: str, title: str, body: str, timeout: float = SEND_TIMEOUT_S) -> int:
    """POSTs the message the way ntfy takes it (the text as the body, the title in a header). Returns the HTTP status."""
    request = urllib.request.Request(check_url(url), data=body.encode("utf-8"), method="POST",
                                     headers={"Title": title.encode("ascii", "replace").decode("ascii"), "Content-Type": "text/plain; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:   # noqa: S310 - the scheme was checked above
            return int(reply.status)
    except urllib.error.HTTPError as error:
        error.close()
        return int(error.code)
