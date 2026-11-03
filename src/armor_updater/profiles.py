# =============================================================================
# ARMOR-UPDATER - Update profiles by machine role: profiles.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Update profiles by machine role (the CM5, an operator PC, a development PC).

A profile is a named list of components. The updater has no catalogue of its own (it discovers the projects by their manifests), so a profile only names projects: the ones that
are not discovered on this machine are reported as a warning, never as a failure. The profiles are data, in `ARMOR-DOCS/data/update-profiles.json` (schema `1.0`); a copy ships
inside the package (`data/update-profiles.json`) and is used when the workspace has no ARMOR-DOCS checkout. The chosen profile and the adjustments made to it are remembered in
the settings file. The composition of the roles is a proposal until the owner confirms it (the file says so).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import settings

SCHEMA_VERSION = "1.0"
BUNDLED_PROFILES = Path(__file__).with_name("data") / "update-profiles.json"
DOCS_PROFILES = ("ARMOR-DOCS", "data", "update-profiles.json")
LANGUAGE_CODES = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class ProfilesError(ValueError):
    """The profiles file is not the expected schema."""


@dataclass(frozen=True)
class Profile:
    id: str
    title: dict[str, str]
    description: dict[str, str]
    components: tuple[str, ...]
    all_installable: bool = False

    def label(self, lang: str) -> str:
        return self.title.get(lang) or self.title.get("en") or self.id

    def about(self, lang: str) -> str:
        return self.description.get(lang) or self.description.get("en") or ""


@dataclass(frozen=True)
class ProfileSet:
    proposal: bool
    profiles: tuple[Profile, ...]

    def get(self, profile_id: str) -> Profile | None:
        return next((item for item in self.profiles if item.id == profile_id), None)


def _texts(value: Any, where: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ProfilesError(f"{where} must be an object with the texts per language")
    texts = {str(code): text for code, text in value.items() if isinstance(text, str) and text.strip()}
    if "en" not in texts:
        raise ProfilesError(f"{where} needs an English text")
    return texts


def parse_profiles(text: str) -> ProfileSet:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProfilesError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ProfilesError(f"schema_version must be {SCHEMA_VERSION!r}")
    raw = data.get("profiles")
    if not isinstance(raw, list) or not raw:
        raise ProfilesError("profiles must be a non-empty list")
    profiles: list[Profile] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            raise ProfilesError("every profile needs an id")
        components = item.get("components", [])
        if not isinstance(components, list) or any(not isinstance(name, str) or not name.strip() for name in components):
            raise ProfilesError(f"profile {item['id']}: components must be a list of project names")
        profile = Profile(
            item["id"],
            _texts(item.get("title"), f"profile {item['id']}: title"),
            _texts(item.get("description"), f"profile {item['id']}: description"),
            tuple(dict.fromkeys(name.strip() for name in components)),
            item.get("all_installable") is True,
        )
        if any(existing.id == profile.id for existing in profiles):
            raise ProfilesError(f"duplicate profile id {profile.id}")
        profiles.append(profile)
    return ProfileSet(data.get("proposal") is True, tuple(profiles))


def load_profiles(workspace_root: Path | None = None) -> ProfileSet:
    """The profiles of the workspace's ARMOR-DOCS checkout when it has a readable file, otherwise the copy shipped with the updater. A damaged workspace file falls back to the copy."""
    if workspace_root is not None:
        candidate = workspace_root.joinpath(*DOCS_PROFILES)
        try:
            return parse_profiles(candidate.read_text(encoding="utf-8"))
        except (OSError, ProfilesError):
            pass
    return parse_profiles(BUNDLED_PROFILES.read_text(encoding="utf-8"))


def resolve_components(profile: Profile, discovered: list[str]) -> tuple[list[str], list[str]]:
    """(components present on this machine, names the profile lists that were not discovered). Names compare ignoring case; the order is the discovered one."""
    folded = {name.casefold(): name for name in discovered}
    wanted = [name.casefold() for name in profile.components]
    present = list(folded.values()) if profile.all_installable else [folded[key] for key in wanted if key in folded]
    present = list(dict.fromkeys(present))
    missing = [name for name in profile.components if name.casefold() not in folded]
    return present, missing


def saved_profile() -> tuple[str, list[str] | None]:
    """(profile id, adjusted selection) remembered in the settings; ("", None) when none is chosen."""
    data = settings.load_settings()
    profile_id = data.get("update_profile")
    selection = data.get("update_profile_selection")
    chosen = [name for name in selection if isinstance(name, str)] if isinstance(selection, list) else None
    return (profile_id if isinstance(profile_id, str) else ""), chosen


def save_profile(profile_id: str, selection: list[str] | None) -> None:
    settings.save_settings(update_profile=profile_id, update_profile_selection=sorted(selection) if selection is not None else None)
