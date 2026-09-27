# =============================================================================
# ARMOR-UPDATER - GitHub version lookup: github_client.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Fetches each project's universal manifest directly from GitHub raw content.
#
# IMPORTANT:
#
# This does NOT use GitHub Releases or tags.
#
# The ecosystem's versioning convention stores the public project version in
# armor.project.json. Builds must keep their native package/firmware
# version synchronized with that manifest; local validation catches drift.
#
# Architecture:
#
#   registry.py
#        |
#        v
#   github_raw_url()
#        |
#        v
#   GitHub raw content
#        |
#        v
#   parse_manifest()
#
# stdlib-only:
#
#   urllib
#   concurrent.futures
#   dataclasses
#
# No requests dependency is required.
# =============================================================================

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass

from .project_manifest import (
    ECOSYSTEM_ID,
    MANIFEST_FILE,
    ManifestValidationError,
    ProjectManifest,
    parse_manifest,
)
from .registry import (
    ProjectEntry,
    entry_from_manifest,
    github_raw_url,
)
from .version_parse import Version


# ---------------------------------------------------------------------------
# Network configuration
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT_S = 10

# GitHub is being queried for small text files only.
#
# Keeping this moderate avoids turning a simple version checker into a
# high-concurrency crawler.
MAX_CONCURRENT_REQUESTS = 8

USER_AGENT = "ARMOR-UPDATER"

# Real hosts by default; module-level so tests can point them at a local
# HTTP server instead of mocking urllib itself - real request/response
# round-trips against real fixture servers, same spirit as this
# ecosystem's Go projects using net/http/httptest.
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# Real, bounded retry for genuinely transient network failures - a
# connection that never got a response (DNS, refused, reset, timeout), or
# a real GitHub secondary rate limit (403/429 carrying a Retry-After
# header, see _retry_after_seconds() below). Every OTHER definitive HTTP
# response, even an error one (404/500, or the hourly PRIMARY rate limit -
# see describe_http_error()), is never retried here: GitHub already
# answered, retrying would not change that answer within this process's
# own lifetime, only spend more of the rate limit.
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_S = 0.5


def _retry_after_seconds(exc: urllib.error.HTTPError) -> float | None:
    """GitHub's real secondary-rate-limit signal: a 403/429 response
    carrying a `Retry-After` header telling the caller exactly how many
    seconds to wait - short (seconds, not minutes) and genuinely worth
    retrying within this same process, unlike the hourly PRIMARY rate
    limit (`X-RateLimit-Reset`, handled separately by
    `describe_http_error()` below) which can be tens of minutes away and
    isn't worth blocking a foreground CLI run for."""
    if exc.code not in (403, 429) or exc.headers is None:
        return None
    raw = exc.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


def is_primary_rate_limited(exc: urllib.error.HTTPError) -> bool:
    """True when `exc` is GitHub's real PRIMARY (hourly) rate limit - a
    403/429 with `X-RateLimit-Remaining: 0` - as opposed to a real 404,
    a genuine permission error, or the SECONDARY rate limit
    `_urlopen_with_retries` already retries via `Retry-After`. Extracted
    from `describe_http_error()`'s own detection so a caller that needs
    to make a real decision (stop burning the rest of a batch against an
    already-exhausted budget, not just describe one failure) does not
    have to duplicate this condition or string-match a message."""
    return exc.code in (403, 429) and exc.headers is not None and exc.headers.get("X-RateLimit-Remaining") == "0"


def describe_http_error(exc: urllib.error.HTTPError) -> str:
    """A real, actionable message for an HTTPError - found while
    auditing the code: every HTTPError used to
    become the same opaque `f"HTTP {code}"`, including GitHub's own
    PRIMARY rate limit (a 403/429 with `X-RateLimit-Remaining: 0`), which
    is genuinely transient and tells the caller exactly when it resets
    (`X-RateLimit-Reset`) - a real, common failure mode when running
    status/discovery across every A.R.M.O.R. repository with a
    `GITHUB_TOKEN` too close to its hourly budget (authenticated GitHub
    API calls are capped at 5000/hour, not 60 - every A.R.M.O.R.
    repository is private, so an unauthenticated call to any of them
    is always a plain 404, never a rate limit)."""
    headers = exc.headers
    if is_primary_rate_limited(exc):
        reset_raw = headers.get("X-RateLimit-Reset")
        if reset_raw is not None:
            try:
                reset_at = datetime.fromtimestamp(int(reset_raw), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                pass
            else:
                return f"rate limited by GitHub - resets at {reset_at.isoformat()}"
    if exc.code in (401, 403, 404):
        return f"HTTP {exc.code} (every A.R.M.O.R. repository is private; check GITHUB_TOKEN)"
    return f"HTTP {exc.code}"


def _urlopen_with_retries(
    request: urllib.request.Request,
    *,
    timeout: float,
    max_attempts: int | None = None,
    backoff_base_s: float | None = None,
    opener=urllib.request.urlopen,
    sleep=time.sleep,
) -> bytes:
    """Open `request`, retrying up to `max_attempts` times on a transient
    network failure (URLError/TimeoutError/socket.timeout/OSError, or a
    real GitHub secondary rate limit - see `_retry_after_seconds()`).
    Never retries any other HTTPError, a real response GitHub already
    gave us. Waits `backoff_base_s * 2**attempt` between network-failure
    retries, or the server's own `Retry-After` value for a secondary rate
    limit. `opener`/`sleep` are injectable so tests can exercise the real
    retry/backoff logic without real network flakiness or real
    wall-clock delay. `max_attempts`/`backoff_base_s` default to the
    module-level constants, read here (not as literal defaults) so tests
    can also monkeypatch those constants directly for callers - like
    every real caller in this module - that never override them
    explicitly."""
    if max_attempts is None:
        max_attempts = RETRY_MAX_ATTEMPTS
    if backoff_base_s is None:
        backoff_base_s = RETRY_BACKOFF_BASE_S
    attempt = 0
    while True:
        attempt += 1
        try:
            with opener(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            retry_after = _retry_after_seconds(exc)
            if retry_after is None or attempt >= max_attempts:
                raise
            sleep(retry_after)
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            if attempt >= max_attempts:
                raise
            sleep(backoff_base_s * (2 ** (attempt - 1)))


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class RemoteStatus:
    """
    Result of looking up one project's remote version.

    version:
        Parsed semantic version, or None when the lookup failed.

    error:
        Human-readable reason for failure, or None when successful.

    http_status:
        HTTP status code when GitHub returned an HTTP error.

    url:
        Raw manifest URL that was queried. This is useful for verbose diagnostics.

    """

    entry: ProjectEntry

    version: Version | None

    error: str | None = None

    http_status: int | None = None

    url: str | None = None

    manifest: ProjectManifest | None = None


@dataclass(frozen=True)
class RemoteDiscovery:
    """Projects positively identified by their own GitHub manifest."""

    projects: tuple[RemoteStatus, ...]
    errors: tuple[str, ...]


def _fetch_discovered_manifest(owner: str, name: str, branch: str, token: str) -> RemoteStatus | None:
    """Return a project only when its own manifest opts into A.R.M.O.R.

    Every A.R.M.O.R. repository is private: `raw.githubusercontent.com`
    accepts the same bearer token as the REST API for a private repository's
    content, so `token` is threaded through here rather than left optional.
    """
    url = f"{GITHUB_RAW_BASE}/{owner}/{name}/{branch}/{MANIFEST_FILE}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )
    try:
        text = _urlopen_with_retries(request, timeout=REQUEST_TIMEOUT_S).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"{name}: manifest {describe_http_error(exc)}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        raise RuntimeError(f"{name}: manifest lookup failed: {exc}") from exc

    try:
        manifest = parse_manifest(text, expected_name=name)
    except ManifestValidationError as exc:
        # A repository that exposes this exact manifest path is relevant to
        # the maintainer even when it is malformed; surface it in workflow
        # logs rather than silently treating it as a non-ecosystem project.
        raise RuntimeError(f"{name}: invalid manifest: {exc}") from exc

    if manifest.ecosystem != ECOSYSTEM_ID:
        return None
    return RemoteStatus(
        entry=entry_from_manifest(manifest),
        version=Version.from_string(manifest.version),
        url=url,
        manifest=manifest,
    )


class MissingTokenError(RuntimeError):
    """No GITHUB_TOKEN was supplied. Every A.R.M.O.R. repository is private,
    so discovery cannot proceed without one - there is no unauthenticated
    fallback to fall back to, unlike a public ecosystem."""


def discover_remote_projects(
    owner: str = "JuanenRac",
    *,
    token: str | None = None,
) -> RemoteDiscovery:
    """Discover every A.R.M.O.R. repository this token can see, no fixed list.

    GitHub's repository listing is only a candidate list. A repository joins
    the ecosystem only after its own root manifest validates and declares
    ``ecosystem: A.R.M.O.R.``. A newly pushed repository therefore appears on
    the next dashboard or updater scan without an index.html edit.

    Every A.R.M.O.R. repository is private, so this lists the AUTHENTICATED
    user's own repositories (``/user/repos``) rather than a public user's
    (``/users/{owner}/repos``, which never returns a private repository
    regardless of the caller's token) - a real, deliberate difference from
    a public ecosystem, which can fall back to unauthenticated reads.
    """
    resolved_token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
    if not resolved_token:
        raise MissingTokenError(
            "GITHUB_TOKEN is required: every A.R.M.O.R. repository is private "
            "(create a fine-grained personal access token with read access to "
            f"{owner}'s A.R.M.O.R.-* repositories)"
        )
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {resolved_token}",
    }

    candidates: list[tuple[str, str]] = []
    page = 1
    while True:
        url = f"{GITHUB_API_BASE}/user/repos?affiliation=owner&visibility=private&per_page=100&page={page}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            payload = json.loads(_urlopen_with_retries(request, timeout=REQUEST_TIMEOUT_S).decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            # Found while diagnosing a real report of repeated GitHub
            # refreshes silently listing fewer and fewer projects (42 ->
            # 9 -> 0): the raw `str(exc)` this used to embed here (a bare
            # "HTTP Error 403: rate limit exceeded") never told the
            # caller it was the hourly PRIMARY rate limit, when it
            # resets, or that GITHUB_TOKEN raises the limit - all of
            # which describe_http_error() already knows how to say.
            raise RuntimeError(f"unable to list GitHub repositories for {owner}: {describe_http_error(exc)}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"unable to list GitHub repositories for {owner}: {exc}") from exc
        if not isinstance(payload, list):
            raise RuntimeError(f"unexpected GitHub repository-list response for {owner}")
        for item in payload:
            owner_login = item.get("owner", {}).get("login") if isinstance(item.get("owner"), dict) else None
            if isinstance(item, dict) and isinstance(item.get("name"), str) and owner_login == owner:
                branch = item.get("default_branch")
                candidates.append((item["name"], branch if isinstance(branch, str) and branch else "main"))
        if len(payload) < 100:
            break
        page += 1

    discovered: list[RemoteStatus] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS, thread_name_prefix="armor-discovery") as pool:
        futures = {pool.submit(_fetch_discovered_manifest, owner, name, branch, resolved_token): name for name, branch in candidates}
        for future in as_completed(futures):
            name = futures[future]
            try:
                status = future.result()
            except RuntimeError as exc:
                errors.append(str(exc))
                continue
            if status is not None:
                discovered.append(status)

    discovered.sort(key=lambda status: status.entry.name.casefold())
    return RemoteDiscovery(projects=tuple(discovered), errors=tuple(sorted(errors)))


# ---------------------------------------------------------------------------
# One project
# ---------------------------------------------------------------------------

def _fetch_one(
    entry: ProjectEntry,
    token: str,
) -> RemoteStatus:
    """
    Fetch and parse the version for one project.

    This function intentionally never raises ordinary network/HTTP errors
    to the caller. A single broken repository must not abort the complete
    ecosystem scan. Every A.R.M.O.R. repository is private, so `token` is
    required (no unauthenticated fallback exists to fall back to).
    """

    url = github_raw_url(entry)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/plain,*/*",
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )

    try:
        raw = _urlopen_with_retries(request, timeout=REQUEST_TIMEOUT_S)
        text = raw.decode("utf-8", errors="replace")

    except urllib.error.HTTPError as exc:
        # Typical cases:
        #
        #   404 -> manifest/repository/path disappeared, or an access
        #          restriction on a private repository (see
        #          describe_http_error())
        #   401/403 -> bad/expired token, or a real rate limit
        #   429 -> too many requests
        #   500+ -> GitHub/server problem
        #
        return RemoteStatus(
            entry=entry,
            version=None,
            error=describe_http_error(exc),
            http_status=exc.code,
            url=url,
        )

    except urllib.error.URLError as exc:
        reason = getattr(
            exc,
            "reason",
            "unknown network error",
        )

        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"network error: {reason}",
            url=url,
        )

    except (TimeoutError, socket.timeout):
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"timed out after {REQUEST_TIMEOUT_S}s",
            url=url,
        )

    except OSError as exc:
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"OS/network error: {exc}",
            url=url,
        )

    except Exception as exc:
        # Last-resort protection:
        #
        # One unexpected parser/network implementation error should still
        # become an "unknown" project instead of killing all 44/45 lookups.
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"unexpected error: {type(exc).__name__}: {exc}",
            url=url,
        )

    # -----------------------------------------------------------------------
    # Manifest and version parsing
    # -----------------------------------------------------------------------

    try:
        manifest = parse_manifest(text, expected_name=entry.name)
        version = Version.from_string(manifest.version)
    except ManifestValidationError as exc:
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"invalid project manifest: {exc}",
            url=url,
        )

    return RemoteStatus(
        entry=entry,
        version=version,
        error=None,
        http_status=None,
        url=url,
        manifest=manifest,
    )


# ---------------------------------------------------------------------------
# All projects
# ---------------------------------------------------------------------------

def fetch_all(
    entries: list[ProjectEntry],
    progress=None,
    *,
    token: str | None = None,
) -> dict[str, RemoteStatus]:
    """
    Fetch the latest GitHub version for every given entry.

    Parameters
    ----------
    entries:
        Projects to query.

        Discovered local or remote project entries. The caller must supply
        them; this module deliberately has no fixed project catalogue.

    progress:
        Optional callback:

            progress(done, total)

        It is called after each individual request completes.

    Returns
    -------
    dict[str, RemoteStatus]

        Dictionary keyed by project name.

    Notes
    -----
    Requests are performed concurrently, but the concurrency is intentionally
    limited to MAX_CONCURRENT_REQUESTS.

    Results are inserted as soon as each request completes. Therefore the
    dictionary's insertion order is completion order. Consumers can apply
    their own family/name ordering after discovery.
    """

    targets = entries

    results: dict[str, RemoteStatus] = {}

    total = len(targets)
    done = 0

    if total == 0:
        return results

    resolved_token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
    if not resolved_token:
        raise MissingTokenError(
            "GITHUB_TOKEN is required: every A.R.M.O.R. repository is private"
        )

    with ThreadPoolExecutor(
        max_workers=MAX_CONCURRENT_REQUESTS,
        thread_name_prefix="armor-github",
    ) as pool:

        futures = {
            pool.submit(
                _fetch_one,
                entry,
                resolved_token,
            ): entry
            for entry in targets
        }

        for future in as_completed(futures):
            entry = futures[future]

            try:
                status = future.result()

            except Exception as exc:
                # This should normally never happen because _fetch_one already
                # converts expected failures into RemoteStatus. It is kept as
                # a final isolation boundary anyway.
                status = RemoteStatus(
                    entry=entry,
                    version=None,
                    error=(
                        "worker failure: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    url=github_raw_url(entry),
                )

            results[
                status.entry.name
            ] = status

            done += 1

            if progress is not None:
                progress(
                    done,
                    total,
                )

    return results
