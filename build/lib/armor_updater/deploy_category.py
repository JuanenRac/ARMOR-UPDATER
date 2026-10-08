# =============================================================================
# ARMOR-UPDATER - Deploy-target categorisation: deploy_category.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Buckets A.R.M.O.R.'s own free-text ``deployment_target`` manifest field
into a small, closed set of real hardware-target categories, for the
desktop GUI's deploy filter only.

A.R.M.O.R.'s manifest schema deliberately keeps ``deployment_target`` as
free, human-readable text (see ARMOR-UPDATER's own ``armor.project.json``
notes) instead of a closed enum the way HYDRA-UMC's manifest does - a
real project describes its own real hardware ("ESP32-S3-ETH-PoE",
"NVIDIA Jetson Orin NX") instead of squeezing it into an artificial fixed
value. The desktop filter still needs a small set of buttons to filter
by, so this module classifies that free text by real keyword content
instead of asking every project to declare a second, enum-shaped field.

Earlier, the filter reused HYDRA-UMC's own closed enum verbatim
(``cm5``/``user-pc``/``mobile``/``wearable``/``dev-server``) and compared
it against A.R.M.O.R.'s free text with ``==`` - none of A.R.M.O.R.'s real
projects ever literally equal one of those five strings, so every filter
button except "all" silently matched zero projects (not just the mobile
one), and the deploy-target column tried to translate the raw free text
itself as an i18n key, showing broken strings like "deploy_Android 10+"
in the table instead of the project's own real text.
"""

from __future__ import annotations

#: The real category keys this module classifies into, in the order the
#: desktop GUI shows its filter buttons. "all" is the GUI's own "no
#: filter" option, not a category this module ever returns.
DEPLOY_CATEGORIES: tuple[str, ...] = (
    "all",
    "field-node",
    "server",
    "mobile",
    "browser",
    "workstation",
    "shared",
)

#: Ordered (keyword, category) rules, checked top to bottom against the
#: lower-cased manifest text; the first match wins. Order matters where a
#: real manifest's text could match more than one rule (e.g. ARMOR-STUDIO's
#: "Browser served by central server" contains both "browser" and "central
#: server" - "browser" is the more specific, meaningful category for a
#: client that runs in one).
_KEYWORD_RULES: tuple[tuple[str, str], ...] = (
    ("android", "mobile"),
    ("browser", "browser"),
    ("esp32", "field-node"),
    ("outdoor field node", "field-node"),
    ("jetson", "server"),
    ("any machine", "workstation"),
    ("developer workstation", "workstation"),
    ("administration host", "workstation"),
    ("central server", "workstation"),
)


def categorize_deployment_target(raw: str) -> str:
    """Classify a real A.R.M.O.R. manifest's free-text ``deployment_target``
    into one of ``DEPLOY_CATEGORIES`` (never "all").

    A value that opens with "All " (ARMOR-COMMON's "All A.R.M.O.R. services
    and tools", ARMOR-DOCS' "All users and maintainers") is ecosystem-wide
    rather than tied to one kind of hardware, so it is classified as
    "shared" before the keyword rules run. Anything that matches none of
    the rules below is also "shared" - a real, visible fallback bucket
    instead of a project silently vanishing from every specific filter.
    """
    text = raw.strip().lower()
    if text.startswith("all "):
        return "shared"
    for needle, category in _KEYWORD_RULES:
        if needle in text:
            return category
    return "shared"
