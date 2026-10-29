<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-UPDATER banner" width="100%">
</p>

# 🛠️ ARMOR-UPDATER

<p align="center">
  🇺🇸 <b>English</b> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Detects, installs and updates every A.R.M.O.R. repository on the machine it runs on (a Python program with no required dependencies)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-288%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Honesty check - what runs today:** The manifest discovery, the version comparison, the signature check, the staged install and update with its lock, journal, backups and rollback, the evidence log and the eight-language interface tables are tested (288 tests), and the Qt Quick shell has been run on Windows. It has not been run against every repository of the family end to end, and the installs it makes need `git` and each repository's own build tools on the machine.

---

## 📋 At a glance

| | |
|---|---|
| Version | `0.1.5` |
| Maturity | Established |
| Role | Desktop tool that installs and updates the family on a PC, one project at a time |
| Stack | Python 3.10+, git; optional PySide6 (Qt Quick) |
| Tests | 288 (`python -m pytest tests -q`, about six minutes) |
| Interfaces | `armor-updater --cli` with `status`, `install`, `update`, `rollback` and `backups`, and a Qt Quick window in eight languages |
| Runs on | A PC with Python and git (the window has only run on Windows) |
| On real hardware | Not applicable: it is a desktop program; its Qt Quick shell has been run on Windows |
| License | GPL-3.0-or-later |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Security](#-security--safety) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Quick start](#-quick-start) · [Testing](#-testing) · [Troubleshooting](#-troubleshooting) · [Structure](#-repository-structure) · [Related](#-related-projects)

## 🚦 Project status

Each line is one part of this repository and the light says how far it is today. It is written from what the repository can show (tests, builds, runs), not from what is planned.

🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working

| Area | State | What it means here |
|---|---|---|
| Software | 🟡 | The manifest discovery, the version comparison and the staged install and update work; they have not been run end to end against every repository of the family. |
| Tests | 🟢 | 288 tests pass (`python -m pytest tests -q`): the discovery, the version comparison, the signature check, the staged install with its lock, journal, backups and rollback, the evidence log and the eight-language tables. |
| Interface | 🟡 | The Qt Quick shell has been run on Windows only. |
| Security | 🟡 | The signature check and the evidence log are tested on the host; there has been no independent review. |
| Updates | 🟡 | The installs it makes need `git` and each repository's own build tools on the machine. |
| Documentation | 🟢 | Eight languages and the changelog are up to date. |

## 🎯 Overview

* **Discovery, no fixed list:** a local folder joins the moment it carries a valid `armor.project.json` declaring `ecosystem: "A.R.M.O.R."`; remotely, every public repository of the account is checked the same way. A `GITHUB_TOKEN` is optional: it only raises GitHub's limit of 60 requests an hour.
* **Install and update, never in place:** a new project and an update are both built and verified in an independent staging clone first, and only promoted - two journalled renames, the replaced checkout kept as a backup under `.armor-updater/backups/` (the newest three) - once that build succeeds; an update to the commit already installed does nothing; a genuinely uncommitted local edit is refused outright, never silently discarded; a crash between the renames is healed at the next run, and `rollback` puts the newest backup back.
* **One at a time, and ordered:** a lock stops two updaters working on a workspace together; a batch goes ARMOR-COMMON first (every build needs it), and a project is not built without it.
* **Evidence:** every attempt, successful or not, appends one line to a local log with the project, the version and commit before and after, and the reason for a failure.
* **Requirements:** a manifest can list, in the optional `requires` field, the projects that must be installed first; a batch puts them first, and an install or update is refused with a clear message, in the language of the window, when one of them is missing.
* **Signatures, warn by default:** a revision without a valid signature is installed or updated all the same, and the window and the command line state that it is not signed; choosing *require* in the settings (`"signature_policy": "require"`) refuses it instead.
* **Previous copies:** the window can restore the previous copy of a project or delete the copies kept, and `status` shows how many there are and the disk they take.
* **A CLI and an optional desktop shell:** `armor-updater status`/`install`/`update`, and a Qt Quick interface (`pip install ".[gui]"`) in the ecosystem's eight languages.

## 🧩 Role in A.R.M.O.R.

ARMOR-UPDATER is the desktop tool for the person who keeps a copy of the family on a PC: it finds the A.R.M.O.R. repositories on the machine, compares them with GitHub and installs or updates one at a time, verifying before it replaces anything. It is separate from the updates that [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) drives on the CM5 (those go through [ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)): this one is for a developer's machine.

| It talks to | How | What for |
|---|---|---|
| Local workspace | folders with a valid `armor.project.json` | what is installed and in which version |
| GitHub | `api.github.com`, `raw.githubusercontent.com` and git; `GITHUB_TOKEN` optional | the latest version of every repository of the account |
| ARMOR-COMMON | a project may list it in `requires` | it goes first in every batch: every build needs it |
| ARMOR-DEVOPS | separate | the updates that ARMOR-STUDIO drives on the CM5 go through it, not through this tool |

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-UPDATER architecture: the person, the workspace and GitHub, the modules of the updater and the live checkout and build it changes" width="100%">
</p>

## 🔒 Security & Safety

| Threat | Defence |
|---|---|
| Compromised code gets installed | The commits are checked against signers in `data/allowed_signers` (OpenSSH format) whose fingerprint is pinned in `signature.py`; changing the file without the pin makes every check fail (closed); `signature_policy` is `warn` (default: installs and says it is not signed) or `require` (refuses) |
| A half-finished install or a replacement in place | Never in place: everything is built and verified in an independent staging clone and promoted with two journalled renames (`promotion.json`); the replaced checkout is kept in `.armor-updater/backups/` (the newest three) |
| Two updaters on one workspace | A lock (`.armor-updater/lock`) that goes stale after 6 hours |
| A dependency that is not built | ARMOR-COMMON goes first and a project is not built without it; the optional `requires` field of the manifest orders a batch and refuses an install with a clear message in the language of the window |
| Local edits lost | An update to the commit already installed does nothing; a genuinely uncommitted local edit is refused outright |
| A fake discovery | A project counts only with a valid `armor.project.json` that declares `ecosystem: "A.R.M.O.R."`; remotely, every public repository of the account is checked the same way |
| GitHub slow or down | Request timeout 10 s, up to 8 at a time, 3 retries (0.5 s base wait), `ls-remote` 20 s; the delay of minutes of `raw.githubusercontent.com` is allowed for |

Every attempt, successful or not, appends one line to the local evidence log (project, version and commit before and after, reason of a failure). The installs need `git` and the build tools of each repository; the signature is only warned about unless `require` is chosen; it has not been run against every repository of the family end to end, and there has been no independent review.

## 🔌 Interfaces

| Route | Auth | What it does |
|---|---|---|
| `armor-updater --cli status` | - | what is installed, its version and the latest on GitHub; `--workspace D`, `--offline` (local only), `--notes` (the real notes of each project), `--json` (machine-readable) |
| `armor-updater --cli install <project>` | - | clone, build and install ONE project that is not installed yet; `--no-build` only clones |
| `armor-updater --cli update <project>` | - | update an installed one, built and verified before it is put in place; `--no-build` only pulls |
| `armor-updater --cli rollback <project>` | - | put the newest backup of the replaced checkout back |
| `armor-updater --cli backups [<project>]` | - | list the backups of replaced checkouts and the disk they take; `--prune N` keeps the newest N of each |
| `armor-updater --version` | - | the version of the tool |

The window (Qt Quick, `pip install ".[gui]"`, started on Windows by `run-gui.vbs`) shows the same state, installs and updates one project, restores the previous copy of a project or deletes the copies kept, and states when a revision is not signed; it is worded in eight languages (`i18n.py`, `i18n_pt.py`, `i18n_recovery.py`, `result_text.py`) and has only been run on Windows. Full reference: [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) and [docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md).

## ⚙️ Configuration

| Setting | Default | What it does |
|---|---|---|
| `--workspace` | the parent folder of the tool | the workspace root to scan |
| `GITHUB_TOKEN` | optional | raises GitHub's limit of 60 requests an hour; it is only read, never written |
| `signature_policy` | warn | `warn` installs and says it is not signed; `require` refuses; kept in `~/.armor_updater_settings.json` |
| Backups kept | 3 | the newest three of each project; `backups --prune N` changes it |
| Lock | 6 h | a lock older than this is ignored |

`.env.example` shows the variables a repository build may read. The language of the window follows `~/.armor_updater_settings.json` (and the old `~/.armor_updater_lang.json`).

## 🚀 Quick start

**Requirements:** Python 3.10+, `git` and the build tools of the repositories you install; optional: PySide6 for the desktop window.

```bash
pip install -e ".[dev]"                     # or ".[dev,gui]" for the optional Qt Quick window
python -m pytest tests -q                   # 288 tests, about six minutes
armor-updater --cli status                  # local and GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK   # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK    # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK  # put the newest backup of a replaced checkout back
```

See [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

## 🧪 Testing

```powershell
python -m pytest tests -q  # 288 tests, about six minutes
python -I tools/armor_ci_validate.py
```

| Area | What it covers |
|---|---|
| Discovery and versions | the manifest, the registry, local and remote detection, version parsing and the GitHub client |
| Install and update | staging, the lock, the journal, the backups and the rollback, requirements and the evidence log |
| Signatures | the pinned keys, the closed failure and the two policies |
| Command line | `status`, `install`, `update`, `rollback` and `backups` with their options |
| Languages and window | the eight languages (`test_i18n.py`) and the texts of every result |

`python -m unittest` finds only three of them: the suite is written for pytest (`conftest.py` is in `tests/`) and takes close to six minutes. GitHub Actions runs the A.R.M.O.R. baseline on every push and pull request: the validation of the manifest, version, changelog and README parity, then the project's own build and tests.

## 🏗️ Build & Release

It is plain Python: nothing to compile (`pip install -e .`). The version lives in `pyproject.toml`, in `armor.project.json` and in the README badge (read from the manifest); each version has its entry in [CHANGELOG.md](CHANGELOG.md). Releases are published on GitHub.

## 🩺 Troubleshooting

| You see | Because | Do |
|---|---|---|
| An update says nothing happened | the project is already at the commit that GitHub has | nothing to do |
| An update is refused because of local changes | the checkout has an edit that is not committed | commit or stash it, then update |
| It says a requirement is not installed | the manifest lists it in `requires` | install that project first (a batch already orders them) |
| The window or the command line says the revision is not signed | `signature_policy` is `warn`, so it installs and says so | choose `require` in the settings to refuse unsigned revisions |
| An update broke something | the new revision builds but does not behave | `armor-updater --cli rollback <project>` puts the newest backup back |

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-UPDATER" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
ARMOR-UPDATER/
├── src/armor_updater/
│   ├── project_manifest.py registry.py ecosystem_catalog.py   the manifest, the list, the catalogue
│   ├── detect.py github_client.py version_parse.py            local and remote discovery, versions
│   ├── install.py git_ops.py staging.py                       staged install and update
│   ├── promotion.py releases.py deploy_category.py            lock, journal, backups, layouts
│   ├── signature.py                                           signed updates, pinned keys
│   ├── evidence.py settings.py console_flags.py               the log, the settings, the flags
│   ├── main.py                                                the command line
│   ├── i18n.py i18n_pt.py i18n_recovery.py result_text.py     the eight languages
│   ├── gui.py qt_gui.py qml/                                  the optional Qt Quick window
│   └── data/ assets/                                          allowed_signers; the icon
├── tests/                                                     288 tests in 25 modules
├── docs/                                                      CLI_REFERENCE.md, QML_DESKTOP_GUI.md
├── tools/                                                     the shared CI checks, the launcher and generate_app_icon.py
├── images/                                                    banner, icon and the pictures of the README
├── .github/                                                   CI workflow, dashboard notice, issue and pull-request templates
├── armor.project.json                                         manifest: version, role, maturity
├── pyproject.toml                                             package metadata, entry points
├── CHANGELOG.md                                               what changed in each version
├── run-gui.vbs                                                opens the window on Windows without a console
├── run.sh run.bat                                             start, shared workflow
├── build.sh build.bat                                         build and test, shared workflow
├── build-test.sh build-test.bat                               build, test and package
├── test.sh test.bat                                           only the tests, never the version
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roadmap & Known limits

**Known limits today**

* The Qt Quick window has only been run on Windows.
* It has not been run against every repository of the family end to end.
* The installs need `git` and the build tools of each repository.
* No independent security review.

**Next**

* Run it end to end against every repository of the family and on Linux and macOS.

## 🌍 Languages

README and texts exist in English, Spanish, French, Italian, German, Chinese, Japanese and European Portuguese.

## 🔗 Related Projects

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) is a perimeter-security system made of independent repositories. Each one has its own version, its own tests and its own README; this is the family:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Message contracts, validators, conformance vectors and generated types
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Field-node firmware for ESP32-S3 with three radars and its own web panel
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Solar inverter and battery protocols and the messages of a gateway node
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Electrical node: meters, the message of the network's readings and the rules for switching
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Alarm node and panel: zones, arming, delays, siren and PIN, with the server or without it
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Touch panel: the state of the system on a wall screen, arming and acknowledging, and the home of the voice assistant
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - The local network: its devices, the internet and what changes
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Central coordinator: telemetry, alarms, devices, solar readings and cameras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web console: cameras, radar, alarms, solar energy and the 2D/3D site designer
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Android operator client with a live 2D/3D radar
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone operator client
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Visual inference policy that explains its decisions and never actuates
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Camera zones, masks and detection rules for the Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Offline voice intents with a confirmation that cannot be forged
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Enclosures, electronics and the bench acceptance matrix
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Deployment, the CM5 test bench, backup and TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Offline telemetry simulator with repeatable faults
* **ARMOR-UPDATER** (this repository) - Detects, installs and updates the ecosystem's own repositories
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, security baseline and the capability matrix

## 📚 Documentation

* [Command-line reference](docs/CLI_REFERENCE.md): every command and option
* [The Qt Quick window](docs/QML_DESKTOP_GUI.md): how the desktop window works
* [Capability matrix: what is proven and what is not](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Project catalogue: versions and how the repositories depend on each other](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Changelog of this repository](CHANGELOG.md)

## 🤝 Contributing & Community

* Before a pull request run `python -I tools/armor_ci_validate.py` and the tests: both must pass. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md).
* The README exists in eight languages and is generated from the sources in ARMOR-DOCS: a change to the text is made there.
* A change to a message between components starts in ARMOR-COMMON.
* Do not describe as working on a board what has only been built.
* Report a vulnerability privately: [SECURITY.md](SECURITY.md). Questions, ideas and reports: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - see [LICENSE](LICENSE).
