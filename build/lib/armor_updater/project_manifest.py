# =============================================================================
# ARMOR-UPDATER - Universal repository manifest validation
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Validation for the canonical ``armor.project.json`` repository file.

The manifest is intentionally dependency-free JSON so it can be read on a
developer PC, the central server, GitHub Actions or directly from GitHub raw
content. It describes public project metadata and the release version only;
secrets, machine-specific paths and credentials never belong in it.

A.R.M.O.R.'s ``role`` and
``deployment_target`` are free descriptive prose (each repository's real
role varies too much for a short enum, and the ecosystem's own
``tools/armor_project_tool.py`` already dispatches by repository *name*, not
by these fields) and ``native_version`` is a plain version string that
``armor_project_tool.py``'s own ``bump()`` always keeps equal to ``version``
- there is no separate native build file/regex to read here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


MANIFEST_FILE = "armor.project.json"
SCHEMA_VERSION = "1.0"
ECOSYSTEM_ID = "A.R.M.O.R."
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")
VALID_MATURITY = frozenset({"scaffolding", "functional", "established", "production"})


class ManifestValidationError(ValueError):
    """A manifest is syntactically valid JSON but violates the v1 contract."""


@dataclass(frozen=True)
class ProjectManifest:
    """Validated public metadata owned by one repository."""

    schema_version: str
    ecosystem: str
    name: str
    version: str
    role: str
    stack: str
    technologies: tuple[str, ...]
    deployment_target: str
    maturity: str
    family: str
    parent: str | None
    native_version: str
    build: str
    notes: str
    # Real, optional live-status probe target - present only for a repo that
    # actually runs as a local network service (an "api"/"service" role
    # listening on a real port), absent for a library/CLI/firmware/UI that
    # never does. `service_port` alone (no `service_health_path`) means "do
    # a real TCP connect check"; `service_health_path` additionally means
    # "do a real HTTP GET against that path and expect a 2xx" instead.
    service_port: int | None = None
    service_health_path: str | None = None
    # Real, optional systemd unit name the service runs as on the central
    # server (e.g. "armor-server.service") - documents which unit
    # `systemctl status`/`journalctl -u` targets for this project, alongside
    # the live-status probe above. Absent for anything not deployed as a
    # systemd service.
    service_systemd_unit: str | None = None


def _require_string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field} must be a non-empty string")
    return value


def parse_manifest(text: str, *, expected_name: str | None = None) -> ProjectManifest:
    """Parse and validate a v1 manifest without a third-party JSON Schema lib."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"invalid JSON: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ManifestValidationError("manifest root must be an object")

    expected_fields = {
        "schema_version", "ecosystem", "name", "version", "role", "stack", "technologies",
        "deployment_target", "maturity", "family", "parent", "native_version", "build", "notes",
    }
    # Recognized but genuinely optional - a repo that never runs as a
    # network service has no reason to declare one. Still an explicit,
    # spelled-out set (not "anything goes") so a typo'd key is still
    # caught below, same reasoning as expected_fields itself.
    # "deployment_target_note": a real, human-readable clarification for a
    # deployment_target value whose meaning isn't self-evident from the
    # prose alone - optional, most values need no such note.
    optional_fields = {"service", "deployment_target_note"}
    unknown = sorted(set(data) - expected_fields - optional_fields)
    missing = sorted(expected_fields - set(data))
    if missing:
        raise ManifestValidationError("missing field(s): " + ", ".join(missing))
    if unknown:
        raise ManifestValidationError("unknown field(s): " + ", ".join(unknown))

    schema_version = _require_string(data, "schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ManifestValidationError(
            f"schema_version must be {SCHEMA_VERSION!r}, got {schema_version!r}"
        )

    ecosystem = _require_string(data, "ecosystem")
    if ecosystem != ECOSYSTEM_ID:
        raise ManifestValidationError(
            f"ecosystem must be {ECOSYSTEM_ID!r}, got {ecosystem!r}"
        )

    name = _require_string(data, "name")
    if expected_name is not None and name != expected_name:
        raise ManifestValidationError(
            f"name {name!r} does not match expected repository {expected_name!r}"
        )

    version = _require_string(data, "version")
    if not VERSION_RE.fullmatch(version):
        raise ManifestValidationError("version must use MAJOR.MINOR.PATCH")

    role = _require_string(data, "role")

    stack = _require_string(data, "stack")
    raw_technologies = data.get("technologies")
    if (
        not isinstance(raw_technologies, list)
        or not raw_technologies
        or any(not isinstance(item, str) or not item.strip() for item in raw_technologies)
        or len(set(raw_technologies)) != len(raw_technologies)
    ):
        raise ManifestValidationError("technologies must be a non-empty unique string array")

    deployment_target = _require_string(data, "deployment_target")

    maturity = _require_string(data, "maturity")
    if maturity not in VALID_MATURITY:
        raise ManifestValidationError(f"unsupported maturity: {maturity!r}")

    family = _require_string(data, "family")
    parent = data.get("parent")
    if parent is not None and (not isinstance(parent, str) or not parent.strip()):
        raise ManifestValidationError("parent must be a non-empty string or null")

    native_version = _require_string(data, "native_version")
    if not VERSION_RE.fullmatch(native_version):
        raise ManifestValidationError("native_version must use MAJOR.MINOR.PATCH")
    if native_version != version:
        raise ManifestValidationError(
            f"native_version {native_version!r} differs from version {version!r}"
        )

    build = data.get("build")
    if not isinstance(build, str):
        raise ManifestValidationError("build must be a string")

    service_port, service_health_path, service_systemd_unit = _parse_service(data.get("service"))

    return ProjectManifest(
        schema_version=schema_version,
        ecosystem=ecosystem,
        name=name,
        version=version,
        role=role,
        stack=stack,
        technologies=tuple(raw_technologies),
        deployment_target=deployment_target,
        maturity=maturity,
        family=family,
        parent=parent,
        native_version=native_version,
        build=build,
        notes=_require_string(data, "notes"),
        service_port=service_port,
        service_health_path=service_health_path,
        service_systemd_unit=service_systemd_unit,
    )


def _parse_service(raw_service: Any) -> tuple[int | None, str | None, str | None]:
    """Validate the optional `service` object (real live-status probe target).

    Absent entirely (the common case - a library/CLI/firmware/UI never runs
    as a network service): returns (None, None, None). Present: `port`
    (1-65535) and `systemd_unit` (the real unit name the service runs as,
    e.g. "armor-server.service") are each individually optional, but at
    least one of them must be given - a background systemd worker with no
    listening port declares `systemd_unit` alone; a network service
    declares `port` (with an optional `health_path`, an HTTP path starting
    with "/", for an HTTP-level check instead of a bare TCP connect -
    meaningless without a `port` to connect to, so it requires one).
    """
    if raw_service is None:
        return None, None, None
    if not isinstance(raw_service, dict):
        raise ManifestValidationError("service must be an object when present")

    allowed = {"port", "health_path", "systemd_unit"}
    unknown = sorted(set(raw_service) - allowed)
    if unknown:
        raise ManifestValidationError("unknown field(s) in service: " + ", ".join(unknown))

    port: int | None = None
    if "port" in raw_service:
        port = raw_service["port"]
        if isinstance(port, bool) or not isinstance(port, int) or not (1 <= port <= 65535):
            raise ManifestValidationError("service.port must be an integer between 1 and 65535")

    health_path: str | None = None
    if "health_path" in raw_service:
        if port is None:
            raise ManifestValidationError("service.health_path requires service.port")
        health_path = raw_service["health_path"]
        if not isinstance(health_path, str) or not health_path.startswith("/"):
            raise ManifestValidationError("service.health_path must be a string starting with '/'")

    systemd_unit: str | None = None
    if "systemd_unit" in raw_service:
        systemd_unit = raw_service["systemd_unit"]
        if not isinstance(systemd_unit, str) or not systemd_unit.endswith(".service"):
            raise ManifestValidationError("service.systemd_unit must be a string ending in '.service'")

    if port is None and systemd_unit is None:
        raise ManifestValidationError("service must declare at least one of port or systemd_unit")

    return port, health_path, systemd_unit
