# =============================================================================
# ARMOR-UPDATER - Dynamic project entry helpers: registry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Runtime representation of a repository-owned A.R.M.O.R. manifest.

This module deliberately contains no project catalogue.  A repository enters
the ecosystem by publishing a valid ``armor.project.json``; discovery in
the dashboard and updater creates one ``ProjectEntry`` from that file.
"""

from __future__ import annotations

from dataclasses import dataclass

from .deploy_category import categorize_deployment_target
from .project_manifest import MANIFEST_FILE, ProjectManifest


GITHUB_OWNER = "JuanenRac"
GITHUB_BRANCH = "main"


@dataclass(frozen=True)
class ProjectEntry:
    """Generic project data read from one repository manifest."""

    name: str
    stack: str
    native_version: str = ""
    note: str = ""
    deploy: str = "cm5"
    tech: tuple[str, ...] = ()
    notes: str = ""
    maturity: str = "scaffolding"
    role: str = "service"
    family: str = ""
    parent: str | None = None
    # Real, optional live-status probe target - see ProjectManifest's own
    # field comments. None/None means "not a network service".
    service_port: int | None = None
    service_health_path: str | None = None
    service_systemd_unit: str | None = None

    @property
    def deploy_category(self) -> str:
        """This entry's own ``deploy`` (the manifest's free-text
        ``deployment_target``), bucketed into a small, closed category for
        the desktop GUI's deploy filter - see deploy_category.py. Computed,
        never stored, so it can never drift out of sync with ``deploy``."""
        return categorize_deployment_target(self.deploy)


def entry_from_manifest(manifest: ProjectManifest) -> ProjectEntry:
    """Create a runtime entry using only data owned by its repository."""
    return ProjectEntry(
        name=manifest.name,
        stack=manifest.stack,
        native_version=manifest.native_version,
        note=manifest.build,
        deploy=manifest.deployment_target,
        tech=manifest.technologies,
        notes=manifest.notes,
        maturity=manifest.maturity,
        role=manifest.role,
        family=manifest.family,
        parent=manifest.parent,
        service_port=manifest.service_port,
        service_health_path=manifest.service_health_path,
        service_systemd_unit=manifest.service_systemd_unit,
    )


def github_raw_url(entry: ProjectEntry, *, owner: str = GITHUB_OWNER, branch: str = GITHUB_BRANCH) -> str:
    """Return the raw GitHub URL for a repository manifest."""
    return f"https://raw.githubusercontent.com/{owner}/{entry.name}/{branch}/{MANIFEST_FILE}"


def github_repo_url(entry: ProjectEntry, *, owner: str = GITHUB_OWNER) -> str:
    """Return the public GitHub repository URL."""
    return f"https://github.com/{owner}/{entry.name}"


def github_actions_url(entry: ProjectEntry, *, owner: str = GITHUB_OWNER) -> str:
    """Return the project's GitHub Actions page."""
    return f"{github_repo_url(entry, owner=owner)}/actions"


def github_issues_url(entry: ProjectEntry, *, owner: str = GITHUB_OWNER) -> str:
    """Return the project's GitHub issues page."""
    return f"{github_repo_url(entry, owner=owner)}/issues"
