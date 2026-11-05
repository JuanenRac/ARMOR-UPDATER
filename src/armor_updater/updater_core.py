# =============================================================================
# ARMOR-UPDATER - Common core seam: updater_core.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What this updater calls its own: the profile of its family.

The updaters of the families do the same work (find the projects, compare versions, bring a checkout in a staging folder, verify it, promote it, leave a trace);
only a handful of names change. `EcosystemProfile` (in `updater_profile.py`, the one file that is the same in every updater) holds those names, and the modules
that read this profile instead of writing the names themselves can become the same code in every updater. The values here are the ones the updater has always used."""
from __future__ import annotations

from .project_manifest import ECOSYSTEM_ID, MANIFEST_FILE
from .updater_profile import EcosystemProfile, profile_in

__all__ = ["EcosystemProfile", "PROFILE", "PROFILES", "profile_for", "CORE_MODULES"]

PROFILE = EcosystemProfile(
    ecosystem_id=ECOSYSTEM_ID,
    manifest_file=MANIFEST_FILE,
    env_prefix="ARMOR_UPDATER",
    state_directory=".armor-updater",
    user_agent="ARMOR-UPDATER",
    repo_prefix="ARMOR",
    file_prefix=".armor_updater",
    trains_directory=".armor-trains",
    batch_first=("ARMOR-COMMON",),
    batch_last=("ARMOR-UPDATER",),
)

#: the profiles this updater knows
PROFILES: dict[str, EcosystemProfile] = {PROFILE.ecosystem_id: PROFILE}


def profile_for(ecosystem_id: str) -> EcosystemProfile:
    """The profile of `ecosystem_id`; an unknown family is an error, never a silent fallback to another one."""
    return profile_in(PROFILES, ecosystem_id)


#: The modules that read the profile for the names of the family.
CORE_MODULES: tuple[str, ...] = ("github_client", "promotion", "signature", "settings", "evidence", "releases", "git_ops")
