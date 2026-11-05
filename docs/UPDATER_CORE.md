# The common core of the updaters

The updaters of the families do the same work: find the projects, compare versions, bring a checkout in a staging folder, verify it, promote it and leave a trace.
What differs is a handful of names. ARMOR-UPDATER keeps those names in one place, the profile of its family, so the modules that read the profile can become the same
code in every updater.

## What is shared and how it stays the same

- `updater_profile.py` is the same file, byte for byte, in the HYDRA-UMC, URTC and A.R.M.O.R. updaters. It holds `EcosystemProfile` (the ecosystem id, the manifest file, the
  prefix of the environment variables, the state folder, the User-Agent, the repository prefix, the prefix of the hidden files, the folder of the version trains and the order of a batch)
  and the helpers that build a variable name or a thread name from them. It imports nothing from the package, so the copies can differ only in their bytes.
- `tests/test_updater_profile_copy.py` pins the digest of that file and, when the other updaters are checked out next to this repository, compares their copies byte for byte.
  To change the file, change the three copies and the digest in the three tests.
- `updater_core.py` is not shared: it holds the profile of this family and `profile_for`, which refuses an unknown family instead of falling back to another one.

## The profile of this updater

| Field | Value |
|---|---|
| `ecosystem_id` | `A.R.M.O.R.` |
| `manifest_file` | `armor.project.json` |
| `env_prefix` | `ARMOR_UPDATER` |
| `state_directory` | `.armor-updater` |
| `user_agent` | `ARMOR-UPDATER` |
| `repo_prefix` | `ARMOR` |
| `file_prefix` | `.armor_updater` |

The modules that read it (`CORE_MODULES`): `github_client`, `promotion`, `signature`, `settings`, `evidence`, `releases`, `git_ops`, `qt_gui`. Their names, files and variables are the ones the updater has always used.

## What is not shared, and why

The modules of the three updaters are not copies of one another any more: the HYDRA-UMC updater has the version trains and the signed package of a release, the URTC updater has the
shared modules of URTC-COMMON and the doctor, and this one has its own promotion, staging and releases layout. The GitHub client, the installer, the manifest parser and the settings differ in
the behaviour that belongs to each family (the version rule of the fourth number, the signatures, the layouts), so they are not merged; only the names they read are. A module becomes
shared when the three can run the same text, not before, and then it is added to the files that the digest test pins.
