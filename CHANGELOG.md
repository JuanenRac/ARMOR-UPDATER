# Changelog: ARMOR-UPDATER 🛠️

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `ARMOR-COMMON/tools/armor_project_tool.py`.

## [0.0.2]

- `build.bat`/`build-test.bat`/`build.sh`/`build-test.sh` create and use their own project-local `.venv` first, unlike every other A.R.M.O.R. repository's build scripts - a real bug, not a style choice: `run.bat`'s own double-click path (`run-gui.vbs`) launches `.venv\Scripts\pythonw.exe` directly, by design, and that `.venv` never existed because the generic delegator this repo used before never created one.
- Every A.R.M.O.R. repository is now public; the manifest, `pyproject.toml`'s description and every "private ecosystem" reference across the README and source comments described a state that no longer holds. `GITHUB_TOKEN` remains supported (a private fork, or simply to raise the 60/hour unauthenticated ceiling) but is no longer required.

## [0.0.1] - Detects, installs and updates the A.R.M.O.R. ecosystem

- Discovers every `armor.project.json`-carrying repository on disk (no fixed
  project list) and, given a `GITHUB_TOKEN`, every repository GitHub says the
  authenticated account owns whose own manifest declares `ecosystem:
  "A.R.M.O.R."`. Every A.R.M.O.R. repository is private, so remote discovery
  (`github_client.py`) requires that token throughout: it lists
  `/user/repos` rather than a public user's repositories, and sends the same
  bearer token to `raw.githubusercontent.com` for the manifest content
  itself. There is no unauthenticated fallback to fall back to.
- Compares each local checkout's version against GitHub's and performs an
  explicit `install` or `update`. An update is atomic-by-verification: the
  candidate is cloned, merged and built in an independent staging clone
  first, and only promoted (two back-to-back directory renames, the previous
  install kept at `<name>.backup`) once that build actually succeeds - a
  build failure, crash, or full disk before promotion leaves the previous
  installation untouched. A genuinely uncommitted edit to an already-tracked
  file is detected upfront and refused outright, never silently discarded.
- `evidence.py`: every install or update attempt appends one line to
  `<workspace>/.armor-updater/evidence.jsonl` with the project, the version
  and commit before and after, whether it succeeded, and its message.
- A CLI (`main.py`) and an optional Qt Quick desktop shell
  (`gui.py`/`qt_gui.py`/`qml/Main.qml`, `pip install ".[gui]"`) in the
  ecosystem's seven languages (`i18n.py`).
- Built for a private ecosystem from the start: remote discovery and manifest
  fetches require a mandatory `GITHUB_TOKEN` throughout (there is no
  unauthenticated fallback), and the manifest reader matches A.R.M.O.R.'s own
  manifest shape (free-text `role`/`deployment_target`, a plain
  `native_version` string that `armor_project_tool.py` always keeps equal to
  `version` - there is no separate native build file/regex to read).
- A GitHub Actions CI baseline (`.github/workflows/ci.yml`) using the same
  canonical `tools/armor_ci_validate.py`/`tools/_armor_readme_parity.py`/
  `tools/armor_project_tool.py` every other A.R.M.O.R. repository vendors
  from ARMOR-COMMON; its own build/test runs `pip install -e ".[dev]"` then
  `pytest tests -q`.
