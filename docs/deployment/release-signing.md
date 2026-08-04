# Release Signing

Bayanat releases are signed with [minisign](https://jedisct1.github.io/minisign/).
The `bayanat` CLI verifies every release tarball against a pinned public key
before installing it, so `sudo bayanat update` (and the installer) will refuse
an unsigned or tampered release. This is the BAY-01-017 control.

## What the updater expects

For each GitHub release tagged `<tag>` (e.g. `v4.1.0`), two assets must be
attached:

| Asset | What it is |
|---|---|
| `bayanat-<tag>.tar.gz` | the release source tree |
| `bayanat-<tag>.tar.gz.minisig` | its minisign signature |

The updater downloads both, runs `minisign -V` against the pinned key, and only
extracts the tarball if the signature verifies. A missing `.minisig` is treated
as unsigned and refused.

## The pinned key

The verifying public key is baked into the `bayanat` script as `RELEASE_PUBKEY`
(root-owned, not swappable at update time):

```
RWS7XvDVF0InHWTCh/86K8sXGcHU/PmzCl4uH9GUDjNnNzHhcX1BvGqZ
```

key ID `1D274217D5F05EBB`.

The matching **secret key is held offline** (never in CI, never in the repo).
It signs releases on a maintainer's machine. CI and GitHub only ever carry the
already-made `.minisig`.

## Signing a release

On the machine that holds the secret key, from a clean checkout at the tag:

```bash
TAG=v4.1.0

# 1. Build the exact tree the tag points at.
git archive --format=tar.gz --prefix="bayanat-$TAG/" -o "bayanat-$TAG.tar.gz" "$TAG"

# 2. Sign it (prompts for the key password).
minisign -Sm "bayanat-$TAG.tar.gz"

# 3. Verify locally against the pinned public key before publishing.
minisign -Vm "bayanat-$TAG.tar.gz" -P RWS7XvDVF0InHWTCh/86K8sXGcHU/PmzCl4uH9GUDjNnNzHhcX1BvGqZ
```

Then attach `bayanat-$TAG.tar.gz` and `bayanat-$TAG.tar.gz.minisig` to the
GitHub release for `$TAG`.

`git archive` is deterministic for a given tree, and the signature covers the
exact bytes you upload, so there is no cross-machine reproducibility
requirement: the updater verifies the same file you signed.

## Key custody

- Working copy: `~/.config/minisign/bayanat-release.key` (chmod 600).
- Password: stored in a password manager. minisign cannot regenerate the key
  from the password alone, so the key file **and** the password must both
  survive. Keep an encrypted backup.
- More than one maintainer should hold the key file and password (bus factor).

## Rotation

minisign has no revocation. If the key is lost or compromised, generate a new
keypair, update `RELEASE_PUBKEY` in the `bayanat` script, and ship the new
pinned key in a fresh install or a documented manual swap. Until a host runs a
`bayanat` build carrying the new key, it will keep trusting the old one, so a
rotation reaches existing hosts only through an update they install with the
old key still trusted, or through a manual key swap on the host.

The manual update path always remains available, so a lost key never bricks an
install: an operator can still update the host by hand per
[upgrading.md](upgrading.md).
