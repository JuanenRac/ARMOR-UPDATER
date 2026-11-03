# Only signed tags

By default the updater installs what the GitHub remote serves and warns about an unsigned revision (see the signature policy in the settings). The **only signed tags** mode is stricter and is **off by default**: with it on, a project is installed or updated only when its candidate revision is pointed at by an **annotated git tag** whose signature `git verify-tag` accepts against an **allowed-signers file pinned by its SHA-256**.

No tag, a lightweight tag, a tag signed by another key, or an allowed-signers file whose content differs from the pinned SHA-256 means nothing is installed, and the reason is shown. The check reads git objects and runs `ssh-keygen` only: nothing of the downloaded repository is run or built before the signature is verified, and a refused candidate leaves the installed checkout untouched.

## Switch it on

In `~/.armor_updater_settings.json` (the window has a checkbox for the first key):

```json
{
  "signed_tags_only": true,
  "allowed_signers_file": "/home/me/.config/armor/allowed_signers",
  "allowed_signers_sha256": "<64 hexadecimal characters>"
}
```

The same can be set for one run with `ARMOR_UPDATER_SIGNED_TAGS_ONLY=1`, `ARMOR_UPDATER_ALLOWED_SIGNERS=<file>` and `ARMOR_UPDATER_ALLOWED_SIGNERS_SHA256=<hex>`; the environment wins over the settings. A damaged settings file never switches the mode off.

* `allowed_signers_file` is optional. Without it the file shipped with the updater (`data/allowed_signers`) is used, and only while it holds exactly the keys pinned in `signature.py`.
* `allowed_signers_sha256` is **required** with a file you chose: the file is not used until its SHA-256 equals this value. Compute it with `sha256sum allowed_signers` (Linux, macOS) or `certutil -hashfile allowed_signers SHA256` (Windows).

## The allowed-signers file

One line per trusted key: a principal, the option `namespaces="git"`, the key type and the public key. `allowed_signers.example` in this folder shows the format with a placeholder key; it holds no real key. A key's own fingerprint (`ssh-keygen -lf key.pub`, `SHA256:...`) identifies it; the SHA-256 of the whole file pins the list, so adding or removing a line changes the pin on purpose.

## How the maintainer signs a tag

These steps are for the person who publishes a release; the updater never runs them.

1. Create a dedicated signing key once, with a passphrase, and keep the private half out of every repository: `ssh-keygen -t ed25519 -f ~/.ssh/armor_signing -C "release signing"`.
2. Tell git to sign with SSH keys: `git config --global gpg.format ssh` and `git config --global user.signingkey ~/.ssh/armor_signing.pub`.
3. Add the public key to the allowed-signers file as `principal namespaces="git" ssh-ed25519 AAAA...`, then pin the new SHA-256 of the file in the settings of every machine that uses the mode.
4. Sign the release commit with an annotated tag: `git tag -s -m "release" v1.2.3 <commit>` and push it: `git push origin v1.2.3`.
5. Check it before announcing it: `git -c gpg.ssh.allowedSignersFile=allowed_signers verify-tag v1.2.3`.

A tag must be created after the commit it names is final: moving a signed tag to another commit is a new release and needs a new signature.
