# =============================================================================
# ARMOR-UPDATER - Results in the language of the window: result_text.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Turns an InstallResult into a sentence in the language of the window.

The install code writes every message in English (the command line is meant to be scripted and stays in English). A result that carries a `code` (a refusal because a required
project is missing, a signature refusal, a restored copy...) and an installed revision that was not signed are said again here in the language chosen in the window.
"""
from __future__ import annotations

from . import i18n
from .install import InstallResult

_CODE_KEYS = {
    "requires_missing": "msg_requires_missing",
    "signature_refused": "msg_signature_refused",
    "no_backup": "msg_restore_none",
    "restored": "msg_restored",
    "rolled_back": "msg_rolled_back",
    "rollback_failed": "msg_rollback_failed",
    "restore_failed": "msg_restore_failed",
    "cleaned": "msg_cleaned",
    "clean_failed": "msg_clean_failed",
}

_WARNING_MARK = "; WARNING:"


def localized_message(lang: str, result: InstallResult) -> str:
    """The message of `result` in `lang`; an unknown code keeps the English message. A revision that was installed without a valid signature always gets the warning sentence."""
    key = _CODE_KEYS.get(result.code)
    if key is not None:
        text = i18n.t(lang, key, **result.params)
    else:
        text = result.message
        if result.unsigned and _WARNING_MARK in text:
            text = text.split(_WARNING_MARK, 1)[0]
    if result.unsigned:
        text += " " + i18n.t(lang, "msg_unsigned_warning", **{"project": result.params.get("project", ""), "commit": result.unsigned})
    return text
