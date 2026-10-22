# ARMOR-UPDATER — CLI Reference

`armor-updater` with no arguments opens a windowed Qt Quick GUI. Passing `--cli` switches
to the headless argparse CLI documented here, before the optional desktop
runtime is imported, so `--cli` mode works on a genuinely headless CM5 with
no Qt/PySide6 desktop runtime installed and no display. A command word (`status`, `install`,
`update`, `rollback`, `backups`) as the first argument also runs the command line without `--cli`, so a script
or a scheduled job never opens a window; with no window available and no command, the program says so and
exits with 1.

Where the projects live: the parent folder of the updater's own checkout, or - when the updater is installed as
a package, where there is no such folder - the folder named by `--workspace`, by the environment variable
`ARMOR_WORKSPACE` or chosen before in the window; without any of them a command stops with exit code 2 and says so.

## Usage

```
$ armor-updater --cli -h
usage: armor-updater --cli [-h] [--version] {status,install,update,rollback,backups} ...

Detects, installs, and manually updates the A.R.M.O.R. ecosystem's
projects on this machine.

positional arguments:
  {status,install,update,rollback,backups}
    status              Show what's installed, its version, and the latest
                        GitHub version of every project.
    install             Clone and build ONE project that isn't installed yet.
    update              Pull and rebuild ONE project that's already installed.
    rollback            Put the newest backup of ONE project back in its place.
    backups             List the backups of replaced checkouts and the disk
                        they take; --prune N keeps the newest N of each.

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

```
$ armor-updater --cli --version
armor-updater 0.1.2
```

`install`/`update` are deliberately separate from `status` and always
take one explicit project name — there is no "update everything". A
fleet of real robots is not something to leave auto-updating
unattended: `status` shows what's outdated, a human picks what to
actually touch.

## Commands

### `status [--workspace PATH] [--offline] [--notes]`

```
$ armor-updater --cli status -h
usage: armor-updater --cli status [-h] [--workspace WORKSPACE] [--offline]
                                      [--notes]

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace root to scan (default: this tool's own
                        parent directory).
  --offline             Skip the GitHub check - local state only.
  --notes               Also print each project's real notes (family/parent,
                        what's actually implemented, tech) below the table.
```

Scans `--workspace` (or this tool's own parent directory by default) for
sibling folders that expose a valid `armor.project.json` — a folder
name alone is never enough to join the ecosystem — and, unless
`--offline`, checks each one's real published version on GitHub too.

```
$ armor-updater --cli status --workspace /path/to/workspace --offline
Workspace root: /path/to/workspace
(--offline: not checking GitHub - showing local state only)
PROJECT         MATURITY     ROLE      STACK       LOCAL     GITHUB    STATE
----------------------------------------------------------------------------
DEMO-PROJECT-A  functional   service   python      1.2.3     -         installed (not checked)

1/1 installed, 0 outdated (GitHub not checked)
```

### `install <PROJECT-NAME> [--workspace PATH] [--no-build]`

```
$ armor-updater --cli install -h
usage: armor-updater --cli install [-h] [--workspace WORKSPACE]
                                       [--no-build]
                                       project

positional arguments:
  project               Exact project name (see `status` for the full list).

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace root (default: this tool's own parent
                        directory).
  --no-build            Clone only - skip running the project's own build
                        script.
```

Clones the named project into a staging folder inside `--workspace`, runs its own `build-test.sh`/`.bat` there (unless `--no-build` is given) and only when the
build passes puts it in place (a project whose build fails is not left half installed). Every project's build runs `../ARMOR-COMMON/scripts/armor-project.sh`: a
project is not built when ARMOR-COMMON is not installed next to it, and a batch in the window goes ARMOR-COMMON first. A project name that
doesn't expose a valid manifest on GitHub is a real, reported failure —
never a silent no-op:

```
$ armor-updater --cli install NOT-A-REAL-PROJECT
Unknown ecosystem project: 'NOT-A-REAL-PROJECT'
The project must expose a valid armor.project.json on GitHub.
$ echo $?
1
```

### `update <PROJECT-NAME> [--workspace PATH] [--no-build]`

```
$ armor-updater --cli update -h
usage: armor-updater --cli update [-h] [--workspace WORKSPACE]
                                      [--no-build]
                                      project

positional arguments:
  project               Exact project name (see `status` for the full list).

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace root (default: this tool's own parent
                        directory).
  --no-build            Pull only - skip running the project's own build
                        script.
```

Fetches the remote candidate, validates its repository-owned
`armor.project.json` before modifying the checkout, rejects a candidate
whose version is lower than the installed manifest, does nothing when the candidate is
the commit already installed, and otherwise builds it in an independent staging clone and
promotes it with two journalled renames; the replaced checkout is kept under
`<workspace>/.armor-updater/backups/<project>/` (the newest three). With `--no-build` it only performs a
`git merge --ff-only`. If the process dies between the two renames, the next run puts the previous checkout back.
Virtual environments and CMake trees made by the build in the staging folder are removed before the promotion (they hold absolute paths and cannot be moved) and the
project's own `build.sh`/`.bat` makes the environment again in the final place. Only one updater works on a workspace at a time (a lock under
`.armor-updater/`); a second one is told to wait. The preflight is deliberately manifest-based: a reachable Git commit is
not automatically a safe ecosystem update. `--ff-only` is
deliberate and load-bearing: **a healthy local checkout is never
replaced**. A real local edit (this tool is meant to also run on a
developer machine, not only the CM5) or a diverged branch makes the
pull fail loudly with git's own error — never a silent reset or a
discarded change:

```
$ cd /path/to/workspace/SOME-PROJECT && git log --oneline -1
a1b2c3d local work in progress
$ armor-updater --cli update SOME-PROJECT
Pulled latest into ... failed (exit 1) - local changes or a diverged branch?
$ cd /path/to/workspace/SOME-PROJECT && git log --oneline -1
a1b2c3d local work in progress   # unchanged
```

(Exercised for real in `tests/test_install.py`'s
`test_diverged_pull_fails_without_resetting_local_checkout`: a real
diverged git history is built, the fast-forward is proven to fail, and
`HEAD`/file content are proven byte-for-byte unchanged afterward. The separate
`test_refuses_a_remote_manifest_version_lower_than_the_installed_version`
proves that an otherwise fast-forwardable downgrade leaves `HEAD` unchanged.)

## Requirements

A manifest may carry the optional `requires` field, a list of project names that must be installed (and built) first. `install` and `update` refuse a project whose requirement is not
installed in the workspace and say which one is missing; the window does the same in its own language, and a batch puts every required project first (after ARMOR-COMMON, and a parent
before its children). A manifest without the field behaves as before.

## Signatures

By default (`warn`) an install or update goes ahead when the new revision carries no valid signature, and the output ends with a `WARNING:` line that says the revision is not signed;
`status` prints the policy in force. To refuse such a revision instead, choose `require`:

```json
{"signature_policy": "require", "allowed_signers_file": "/home/me/.config/armor/allowed_signers"}
```

in `~/.armor_updater_settings.json` (the older `"require_signed_commits": true` still means the same), or set `ARMOR_UPDATER_REQUIRE_SIGNED=1` for one run. With `require`, every new commit of
an update is checked before anything is built, and a refused candidate leaves the installed checkout untouched. A settings file that cannot be read is treated as `require`.

### The signers of the ecosystem

The updater ships the public key(s) that sign the commits of the ecosystem in `src/armor_updater/data/allowed_signers`, and pins their SHA256 fingerprints in `signature.py`. When no
`allowed_signers_file` is chosen, a signature is checked against that file, and only while the keys in it are exactly the pinned ones: a changed, added or missing key makes the check
fail (it never falls back to "trust anything"). A file chosen with `allowed_signers_file` replaces it on purpose. A test fails when the shipped file and the pin drift apart. The
default policy stays `warn`, so an unsigned revision is still installed with a warning until the commits are signed; `require` makes the ecosystem key mandatory.

## Releases layout (optional, high risk)

By default a project is a plain checkout that is built in a staging folder and moved into place. With `{"deploy_layout": "releases"}` in `~/.armor_updater_settings.json` (or
`ARMOR_UPDATER_LAYOUT=releases`) the project folder becomes a link (a symbolic link, a junction on Windows) to `<workspace>/.armor-updater/releases/<project>/<commit>/`. The candidate
is cloned and built in that final folder, so a virtual environment or an editable install is never made in one place and moved to another, and it is put in service by switching the
link. The previous release stays untouched; `rollback` (and the restore button) switch the link back; the newest three releases are kept, never the one in service.

Risks and safeguards: the first update of a real checkout moves it to its own release folder (journalled; the next run undoes an interrupted move, and a link that cannot be made moves it
back), so a program that keeps files of the old folder open makes the update fail without changing anything; the environment of a release that was left behind keeps the paths it was
built with, so after going back to it run its own `build.sh` once; on Windows the switch of the link is two operations and the next run finishes one a crash cut in two. ARMOR-UPDATER
itself never moves to this layout. The default stays `checkout`.

## How a version is read

The version on GitHub is read from the manifest at the tip of the default branch without going through the cache of `raw.githubusercontent.com` (which can show the previous file for a few minutes
after a push): with a `GITHUB_TOKEN` through the contents API, otherwise from the commit that `git ls-remote` reports, and from the branch URL only when neither works.

## Exit codes

`status` always exits `0` (even when projects are outdated — that's
informational, not a failure). `install`/`update` exit `1` on any real
failure (unknown project, failed clone/pull, failed build script) and
`0` on success.

## Network resilience

Every real GitHub request `status` makes (repository listing, manifest
fetch) retries up to 3 times with backoff for a genuinely transient
network failure (DNS/timeout/connection reset) before giving up — never
for a definitive HTTP response GitHub already returned (404/403/500). If
the remote catalog itself is unreachable or malformed, `status` falls
back to local-only state with a `WARNING:` line instead of crashing.

## GUI

The preferred desktop client is the Qt Quick/QML interface. It is supplied by
the optional `PySide6` extra and uses the same discovery and update services as
this CLI; see [QML Desktop GUI](QML_DESKTOP_GUI.md). `--cli` remains fully
stdlib-only for a headless CM5. A Tkinter window can still appear only as a
temporary compatibility fallback when the optional Qt runtime is absent.

Running `armor-updater` with no arguments opens the QML desktop client.
On Windows, `run-gui.vbs` is the console-free double-click launcher; bare
`run.bat` delegates to it. The client provides a filterable project table,
explicit Install/Update actions, real in-window checkpoints and a language
selector (8 languages; the CLI itself stays English-only, since it's
meant to be scripted/piped).

## An update that survives a crash

Promoting an update takes two renames (the old checkout is moved aside into `.armor-updater/backups/<name>/`, then the new one takes its place). Both are written to a small journal in the
workspace before the first one happens, so a crash or a power cut between them is repaired the next time the tool runs: it finishes or undoes the promotion. An update is therefore correct
whether the process lives or not.

### `rollback <PROJECT-NAME> [--workspace PATH]`

Puts the newest backup of the project back in its place. The checkout that was there becomes the newest backup, so a rollback can itself be undone with another `rollback`.

### `backups [PROJECT-NAME] [--workspace PATH] [--prune N]`

Lists the backups (with the disk each takes). `--prune N` deletes all but the newest `N` of each project. Backups are never inside the scanned workspace folders, so they never show as projects.

### The evidence file

Every attempt appends one line to `<workspace>/.armor-updater/evidence.jsonl`: when it happened (UTC) and how long it took, the project, the version and commit before and after, whether it worked and why not.
