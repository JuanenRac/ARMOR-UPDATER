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
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-191-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.4-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Honesty check - what runs today:** The manifest discovery, the version comparison, the signature check, the staged install and update with its lock, journal, backups and rollback, the evidence log and the eight-language interface tables are tested (191 tests), and the Qt Quick shell has been run on Windows. It has not been run against every repository of the family end to end, and the installs it makes need `git` and each repository's own build tools on the machine.

---

## 📋 At a glance

| | |
|---|---|
| Version | `0.1.4` |
| Maturity | Established |
| Tests | 191 (`python -m pytest tests -q`) |
| Stack | Python 3.10+ (standard library only; PySide6 optional for the desktop shell) |
| On real hardware | Not applicable: it is a desktop program; its Qt Quick shell has been run on Windows |

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

## 📂 Repository Structure

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client, install (staged install and update) + git_ops + staging + promotion (lock, journal, backups), signature (signed updates), evidence, main (CLI), settings, version_parse,
│                       i18n + i18n_pt + i18n_recovery + result_text (eight languages), gui / qt_gui / qml (the Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), generate_app_icon.py
├── tests/              18 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ Development Environment

**Requirements:** Python 3.10+, `git` and the build tools of the repositories you install, optional: PySide6 for the desktop shell

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 191 tests
armor-updater --cli status                              # local + GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK               # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK                # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK              # put the newest backup of a replaced checkout back
```

See `docs/CLI_REFERENCE.md`.

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
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Visual inference policy that explains its decisions and never actuates
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Camera zones, masks and detection rules for the Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Offline voice intents with a confirmation that cannot be forged
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Enclosures, electronics and the bench acceptance matrix
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Deployment, the CM5 test bench, backup and TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Offline telemetry simulator with repeatable faults
* **ARMOR-UPDATER** (this repository) - Detects, installs and updates the ecosystem's own repositories
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, security baseline and the capability matrix

## 📚 Documentation & Community

Where to read more:

* [Capability matrix: what is proven and what is not](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Project catalogue: versions and how the repositories depend on each other](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Changelog of this repository](CHANGELOG.md)
* [License (GPL-3.0-or-later)](LICENSE)
* Questions, ideas and reports: electrohobby3d@gmail.com

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - see [LICENSE](LICENSE).
