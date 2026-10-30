# Changelog

All notable changes to this project are documented here.

## [Unreleased]

- **The lights of Project status follow the evidence of the manifest:** the manifest says how far the repository has been shown to work (`evidence`: `host-test`, `simulator`, `bench` or `field`) and the validator fails when a light is above what that evidence and the maturity allow (`tools/status_lights.py`), so a green that never ran on real hardware cannot come back.
- **The README follows the universal layout in the eight languages:** a threat and defence table with the real limits, every command with its options (including `backups --prune`, `--offline`, `--notes`, `--json` and `--no-build`), the settings, the tests by area, troubleshooting, the Architecture picture drawn from `docs/architecture.json` and the Repository Structure drawn from `docs/structure.json`.
- **The layout of the README is checked in the CI:** the validator runs the shared `tools/universal_readme_check.py` and lists, as a warning, what differs from the universal layout of the README.
- **The pictures of the README come from shared tools:** `tools/make_architecture.py` draws `images/architecture.svg` from `docs/architecture.json` and `tools/make_structure.py` draws the Repository Structure (the text tree and the animated picture) from `docs/structure.json`; both measure every text, and `--check` fails when a picture, its description or the code it points to disagree. They are vendored from ARMOR-COMMON like the shared CI checks.

## [0.1.5] - The updater and the registry of the family are held together by tests and the releases layout is the default

- **The updater and the registry of the family are held together by tests:** every repository that the registry of ARMOR-COMMON names has to publish a manifest this updater accepts, with the name and the group the registry gives it, and what a manifest requires to be installed first has to be a repository of the family (`tests/test_family_registry.py`).
- **The releases layout is the default:** every project, ARMOR-UPDATER included, is a link to `releases/<commit>`. The first update of an existing checkout migrates it by itself: a git bundle of its whole history is written first, the checkout is kept as a release, and if anything fails the link goes back (or, where the folder cannot be moved or the workspace cannot hold links, that update goes on in the older layout with nothing lost). `deploy_layout: checkout` keeps the older layout. Said in the eight languages (`layout_migrated`), with tests for the migration, the backup and the fallback.

- **A release that fails its check goes back by itself:** right after the link of the releases layout is switched, the updater checks that the path leads to the new release, that its manifest can be read and that the commit is the one built; if not, the link returns to the release that was in service (a new project is left without a link), the failed release is deleted and the window and the command say why, in the eight languages (`rolled_back`, `rollback_failed`).
- **The window no longer fills the console with `Cannot read property ... of null` when it closes:** the windows are deleted before the object their bindings read, instead of the other way round.

- **The build scripts work when the python first on the PATH makes a venv with no activate script** (for example the python that ESP-IDF installs): the venv is made with the `py` launcher when there is one and its own python, or its folder first on the PATH, is used instead of the activate script.

- **Signers of the ecosystem:** the public keys that sign the ecosystem's commits ship with the updater and their fingerprints are pinned in the code; without a file of the person's own, signatures are checked against them, and a changed, added or missing key fails closed. A test fails when the file and the pin differ.
- **Releases layout (optional):** `deploy_layout: releases` builds each candidate in its final folder and puts it in service by switching a link, keeping the previous releases so that going back is one more switch. Off by default, never applied to the updater itself, with a journalled first migration, tests for the build failure, the migration, the rollback and the pruning, and the risks written in the CLI reference.
- The repository has a security policy, a code of conduct, a contributing guide and a support file.
- The banner follows the animated style of the ecosystem banners, with the name, the kind and the technologies of the project.
- **No more console windows:** every git call the graphical updater makes (version reads, the remote check, signatures, the dirty check of a project, the manifest of a revision) now starts without a console of its own. Started from the silent launcher (pythonw.exe has no console) each one used to open a command window, and a screen that checks many projects filled the desktop with them. A test fails if any child process of the updater is started without the flag.

## [0.1.4] - Requirements between projects, signatures that warn by default, fresh version reads and buttons for the previous copies

- **Requirements:** a manifest can name the projects that must be installed first with the optional requires field. A batch puts them first (after ARMOR-COMMON, and a parent before its children), and an install or update of a project whose requirement is not installed is refused with a clear message, said in the eight languages of the window; a manifest without the field behaves as before.
- **Signatures warn by default:** a revision without a valid signature is installed or updated all the same, and the window and the command line state that it is not signed. Choosing require in the settings (signature_policy) refuses it as before, with every new commit checked, and a settings file that cannot be read still counts as require.
- **Fresh versions:** the version on GitHub is read without the stale cache of raw.githubusercontent.com, through the contents API when there is a token and at the exact commit that git ls-remote reports when there is not; the branch URL is only the fallback.
- **Previous copies in the window:** both windows (Qt Quick and Tk) have a button to restore the previous copy of the selected project and one to delete the kept copies, each asking first, and show how many copies there are and the disk they take. status shows the same and the signature policy in force.
- Every new text of the window exists in the eight languages; refusals and unsigned installs carry a code so the window says them in its own language, while the command line stays in English.
- The install code is split by responsibility (git_ops, staging, promotion and the decisions in install), the lint check ruff runs in build-test, and a test installs a project end to end whose build makes a virtual environment in the final place.
- Tests: 191 (before 140).

## [0.1.3] - Default-branch awareness

- An update is refused when the checkout is on a branch other than the repository default branch, instead of merging the default branch into it.
- Discovery records each repository default branch, and the fallback manifest lookup uses it instead of assuming main.
- run.sh and the CLI header describe the GUI requirements and the ordered batches of the window.
- The changelog now says the signature check applies when the signature policy is switched on.

## [0.1.2] - Updates that survive a crash, a project that cannot be left half installed and commands that mean what the README says

- **A promotion is journalled.** The two renames that put a new checkout in place of the old one are recorded on disk first; if the process dies between them (a kill, a power cut) the next run puts the previous checkout back instead of leaving the project without a folder. The journal the earlier code looked for lived in a package that never existed, so the recovery never ran; it is now part of the updater.
- **Backups out of the way:** the replaced checkout is kept under `<workspace>/.armor-updater/backups/<project>/` (the newest three), not next to the projects, where each one showed as a project with an invalid manifest and took the disk of a whole checkout for ever. `rollback <project>` puts the newest back (and can itself be undone), `backups` lists them with their size and `--prune N` trims them.
- **An update to the commit already installed does nothing** (before, it cloned, built and promoted again, making another copy).
- **A new project is built before it takes its place:** a failed build installs nothing, instead of leaving a folder that said *already exists, use update*.
- **Virtual environments survive the move:** the environment the build made in the staging folder holds its absolute path and broke when the folder was renamed; it is now removed before the promotion and made again in the final place by the project's own `build.sh`/`.bat`.
- **One updater at a time:** a lock under `.armor-updater/` stops a window and a command, or two windows, from working on one workspace together (one left by a process that is gone is taken over).
- **The window cannot be left busy for ever:** whatever fails inside an install or update (git missing, a file in the folder open, a full disk) comes back as a failed result with its line of evidence, where before it killed the worker and left every button disabled.
- **A batch goes ARMOR-COMMON first,** a parent before its children, and a project is not built when ARMOR-COMMON is not installed next to it (every build needs it); a batch used to go alphabetically and fail the first projects.
- **Local data is carried over right:** a build folder at any depth (`app/build`, `.gradle`, a nested `node_modules`) is no longer copied into the candidate, which made updates slow and the verified build reuse old artifacts.
- **Commands:** `armor-updater status|install|update|rollback|backups` run the command line without `--cli` (they used to open the window and ignore the arguments), the program exits with 1 when no window can be opened, and installed as a package it asks for `--workspace` (or `ARMOR_WORKSPACE`) instead of cloning into the folders of the Python environment.
- **Signed commits:** with the policy on, every new commit is checked, not only the last one; the settings file is written whole beside the old one and put in place, and a settings file that cannot be read is no longer taken as *policy off*.
- The evidence lines say when they happened and how long they took.
- The documents say the truth: the repositories are public and the token is optional, the commands carry `--cli`, the guarantees are the real ones, and the comments that came from another ecosystem are gone. The old copy of the package under `build/` is no longer in the repository.
- Tests: 140 (before 120, 6 of them skipped for ever); new ones cover the lock, the journal and its recovery, the backups and the rollback, the order of a batch, the failed installs, the environments, the nested build folders, the command line without `--cli` and the settings.

## [0.1.1] - Portuguese interface

- The interface now speaks Portuguese as well: the eighth language of the family, with the whole table of texts (menus, states, checkpoints, batch actions, About), selectable in the language box of the window.
- A test keeps the Portuguese table with exactly the same keys as English, and the list of languages equal to the tables.

## [0.1.0] - Build trees are forgotten after an install

- After an install the updater forgets the temporary build trees so the next run starts clean and the disk does not fill.

## [0.0.9] - The copy button of the log is an icon

- The button that copies the activity log is now a small icon (two sheets), with the old words as its tooltip, and turns green for a moment when it has copied.

## [0.0.8] - Signed updates are verified

- When the signature policy is switched on, an update is verified against its signature before it is installed, and read-only files left by git in the staging folder no longer stop a clean-up on Windows.
- Tests for the signature check.

## [0.0.7] - A failed write of the evidence is said

- **The evidence file:** when the line of evidence of an install or update attempt cannot be written, the log now says so (it used to return nothing without a word).

## [0.0.6] - The logo shows when the updater is opened from Electro Hobby 3D Updater

- **Real bug, reported by the user:** the window icon and the logo at the top of the window were looked for next to the project's folder, which does not exist when the updater is installed as a package (as Electro Hobby 3D Updater installs it) - so they never showed when opened from there. The icons now live inside the package (`assets/`) and are shipped with it.

## [0.0.5] - The logo was never shown

- **Real bug, reported by the user:** the header of the window and the About window pointed at `images/ARMOR_UPDATER_ICON.svg`, a file that does not exist (the project's icon is `ARMOR_ICON.svg`), so the logo at the top left stayed empty. They now point at the real file.
- **Window and taskbar icon:** an `.ico` with seven sizes (`images/ARMOR_ICON.ico`, made from the SVG) is now shipped, the window is given its icon itself, and on Windows the process gets its own identity so the taskbar shows it and not the one of Python.

## [0.0.4] - The CLI status table glued ROLE straight into STACK

- **Real bug, found while checking the previous fix for real via ELECTRO-HOBBY-3D-UPDATER's own `status --ecosystem all`:** the plain-text `--cli status` table padded ROLE to a fixed 10 characters - correct for HYDRA-UMC/URTC's short role enum (`tool`, `service`, ...), but A.R.M.O.R.'s manifest schema deliberately keeps `role` as free text, several real repos declaring a whole sentence. A fixed pad does nothing once the text is already longer than it, so every A.R.M.O.R. row ran ROLE straight into STACK with no separator at all (`Android operator clientKotlin / Jetpack Compose`). `role_w` is now computed the same way `stack_w` already was (that column had the identical bug fixed once before, for the same reason). New regression test in `tests/test_main.py` locks a real, long role's own separating space in place.

## [0.0.3] - The deploy filter matched none of A.R.M.O.R.'s own real projects

- **Real bug, reported by the user filtering for mobile apps and not finding ARMOR-ANDROID-CONTROL:** the desktop GUI's deploy filter (both the Tkinter and the Qt Quick shell) compared each project's own real, free-text `deployment_target` against HYDRA-UMC's own closed enum (`cm5`/`user-pc`/`mobile`/`wearable`/`dev-server`) with `==` - a straight copy from HYDRA-UMC-UPDATER's own filter, never adapted to A.R.M.O.R.'s deliberately free-text manifest field. None of A.R.M.O.R.'s 15 real projects ever literally equal one of those five strings, so every filter button except "All" silently matched zero projects, not just the mobile one. The same raw text was also fed straight into `i18n.t(f"deploy_{value}")` for the Deploy column, so every row showed a broken string like `deploy_Android 10+` or `deploy_NVIDIA Jetson Orin NX` instead of its own real text.
- New `deploy_category.py` classifies each project's real `deployment_target` text into one of six real hardware-target categories (`field-node`, `server`, `mobile`, `browser`, `workstation`, `shared`) by keyword content, checked against all 15 real manifests in a new test file (`tests/test_deploy_category.py`). `ProjectEntry.deploy_category` is a computed property, so it can never drift out of sync with the manifest's own `deploy` text. The filter now uses this category; the Deploy column now shows each project's own real text unchanged.
- The Tkinter shell's Linux-only default filter (`cm5`, another value no A.R.M.O.R. project ever declares) now defaults to `server` - the real category of A.R.M.O.R.'s own Jetson-based central server.

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
