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

## The manifest contract

Every updater of the families reads the same set of manifest fields, whatever the family. This is the least they share, and `tests/test_manifest_contract.py` (the same test in each updater) pins it:

| Part | Fields |
|---|---|
| Required in every manifest | `schema_version`, `ecosystem`, `name`, `version`, `role`, `stack`, `technologies`, `deployment_target`, `maturity`, `family`, `parent`, `native_version`, `build`, `notes` |
| Optional, accepted by every updater | `service`, `deployment_target_note`, `evidence`, `hardware_bound`, `min_common` |
| Attributes of the reader's result | the required fields (the native version as one value or as a file and a pattern, depending on the family), `service_port`, `service_health_path`, `service_systemd_unit` and `min_common` |

What is not part of the contract is allowed to differ and is kept apart: the value rules of a family (for example the free-text role of one family against the closed list of another) and the fields that belong to one family only (`depends_on`, `requires`, `components`, `binary`...). A misspelled field is refused as unknown in every updater. When the updaters sit next to one another, the test compares their readers; the reader of the updater of Electro Hobby 3D is read from its main branch with git, read only.

Two files are the same in every updater and are pinned by a digest in the tests: `updater_profile.py` (the names of the family) and `common_gate.py` (the reading of `min_common`, below).

## `min_common` in the manifest

A manifest may carry the optional field `min_common`: the oldest version of the shared contracts repository (ARMOR-COMMON) the project works with (three or four numbers). The updater accepts it and reads it into `ProjectManifest.min_common` and `ProjectEntry.min_common`; a value that is not a version is ignored (`None`) and never refuses the manifest, so a project that says it cannot stop an updater that does not understand it. A misspelled name of the field is still refused as an unknown field.

### What the updater does with it

`status` compares the `min_common` of every project with the version of ARMOR-COMMON installed in the workspace and, when a project asks for a newer one, prints a warning on the error stream (and lists it under `common_notices` in the `--json` output). It only warns: no update is held back and nothing is refused. When ARMOR-COMMON is not installed or its version cannot be read, a project that asks for a minimum gets a notice that says the installed version is not known.

| Setting | Environment variable | Values |
|---|---|---|
| `min_common_check` in `~/.armor_updater_settings.json` | `ARMOR_UPDATER_MIN_COMMON` | `warn` (the default) or `off`. Anything else counts as the default, so a typo never silences the notice. The environment variable wins over the saved setting. |

The comparison counts the fourth number (a missing one is 0). There is no value that holds an update back: whether the installed contracts may stop an update is a decision for later, and this reading is what it would be built on.

### Publication

No manifest of the projects carries `min_common` yet. It is published in the manifests and in the shared manifest schema once every updater of the families reads it.
