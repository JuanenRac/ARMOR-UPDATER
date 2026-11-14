# The signed registry of releases

A tag in a repository says "this commit is version X" only as far as the repository can be trusted. The registry is a second statement, made by the maintainer's key and kept **outside** the repositories it describes, so a release cannot list itself.

## What is signed

`releases.json`, byte for byte, in the SSH-signature namespace `armor-releases` (a signature made for git tags is not valid here, and the other way round). The format is `schema_version` 1 (see `src/armor_updater/release_registry.py`):

```json
{"schema_version": 1, "releases": [
  {"project": "ARMOR-SERVER", "version": "0.8.2.2", "commit": "<40 hex>"},
  {"project": "ARMOR-NODE-RADAR", "version": "0.8.1.2", "board": "s3-eth", "sha256": "<64 hex>"}]}
```

A release names the commit under its tag or, for a firmware image, the file and its SHA-256. The file is written sorted and in one layout, so the signed bytes are always the same for the same list.

## Where it is published

`data/releases.json` and `data/releases.json.sig` in ARMOR-DOCS. The updater reads it only when the mode is on (`release_registry_required` in its settings, or `ARMOR_UPDATER_RELEASE_REGISTRY=1` for one run, with `release_registry_file` naming the file); the mode is off by default and, when it is on, a missing, damaged or unsigned registry refuses the release (it never fails open).

## How it is made, signed and checked

```
python -m armor_updater.registry_tool build  --root <folder with the ARMOR-* repositories> --out releases.json
python -m armor_updater.registry_tool sign   releases.json
python -m armor_updater.registry_tool verify releases.json
python -m armor_updater.registry_tool keys
```

- `build` lists, for each repository with an `armor.project.json` and a tag `v<version>`, the commit under that tag; a repository whose version has no tag is left out and named, never guessed.
- `sign` needs the PATH of an OpenSSH private key without passphrase, in the environment variable `ARMOR_RELEASE_SIGNING_KEY` (or `--key PATH`). The tool never looks for a key, never reads it into Python, never prints or copies it: it asks `ssh-keygen -y` for the public half, refuses to sign unless that half is one of the pinned keys, hands `ssh-keygen -Y sign` only the path and checks the signature it made.
- `verify` is for anyone: it checks the signature against the keys the updater ships and prints what the registry lists (`REGISTRY=PASS`).
- `keys` prints the fingerprints the updater pins.

## Choosing the key (the owner)

```
keys=$(python -m armor_updater.registry_tool keys)      # the fingerprints that are accepted
ssh-keygen -l -f /path/to/the/private/key               # the fingerprint of the key you mean to use: it must be in that list
export ARMOR_RELEASE_SIGNING_KEY=/path/to/the/private/key
python -m armor_updater.registry_tool build --root <folder> --out releases.json
python -m armor_updater.registry_tool sign releases.json
python -m armor_updater.registry_tool verify releases.json
```

Then put `releases.json` and `releases.json.sig` in `data/` of ARMOR-DOCS through a pull request. The key is never in a repository and never in CI.

## What the tests do

`tests/test_registry_tool.py` makes a key for each test in a folder that is deleted, signs and verifies with it, and checks that a key that is not one of the signers signs nothing, that a changed registry or another signer does not verify, that a missing signature is refused and that `build` leaves out an untagged version. No real key is read.
