---
name: release
description: Cut a release of an STS2 mod, promote a beta branch into main, or upload to the Steam Workshop. Use for version bumps, tagging, GitHub Releases, and any task that ends with players getting a new build.
---

# Cut a release

Read the repo's `RELEASING.md` first. It is the primary record for the version policy,
the branch map and the exact command behaviour. This skill covers the order of
operations and the failures that cost the most time.

## The shape of the thing

A mod may ship from two branches, because Slay the Spire 2 has a default Steam branch
and a `public-beta` branch whose DLLs are not compatible. One build cannot serve both.
When a repo does this, a `workshop/targets.json` maps each git branch to its Workshop
item, tag suffix and pre-release flag, and every `dev.sh` command reads the branch you
are on and picks the right one. There is nothing to pass.

Both branches share one version line. The beta branch moves it forward; main inherits
whatever the merge brought and ships it unchanged.

## The everyday flow, two commands

```sh
scripts/dev.sh changelog        # draft; curate ## [Unreleased] by hand first
scripts/dev.sh release minor    # patch | minor | major | an explicit X.Y.Z
                                # examine the diff, then:
scripts/dev.sh publish-release  # commit, tag, push, create the GitHub Release
```

`release` stops without committing so you can read the diff. It refuses to run when the
working tree is dirty, when `## [Unreleased]` is empty, or when the installed game is on
the wrong Steam branch. That last check is the one that stops a build shipping that
cannot load.

Curate the changelog before you start. The **changelog** skill covers the entry voice.

**Expect to hand off the last command.** The publish step is a force-push-capable release
write, and the permission classifier blocks it. Do everything local first so the user runs
a single command. Offer a permission rule rather than retrying.

## Promoting beta into main

Infrequent by design. Do it when a batch of beta releases has settled.

```sh
git switch main
scripts/dev.sh sync-main        # merges with --no-ff, never rebases
                                # switch Steam to the default branch, then:
scripts/dev.sh publish          # rebuild against the default-branch DLL
                                # play it; loading to character select IS the test
scripts/dev.sh release promote  # keeps the merged version
scripts/dev.sh publish-release
```

`sync-main` refuses to rebase on purpose. Public tags point at commits on both branches
and each GitHub Release zip describes that exact history, so a rebase leaves every tag
naming a commit that no longer exists.

Step 3 is not optional. The installed build is still compiled against the other Steam
branch until you rebuild, and it will not load.

## The two rebase hazards, both silent

**A tag does not follow a rebase.** A rewrite moves the commits and leaves the tag behind,
pointing at an orphan. Two commits with the same `release: vX.Y.Z` subject at different
hashes is the tell. Check before trusting any release tag:

```sh
git merge-base --is-ancestor "<tag>^{}" HEAD && echo ok || echo ORPHANED
```

**A rebase also leaves the packaged artifacts stale**, which is the easier half to miss.
The release command packages `dist/` from the build at that moment. When a rebase reorders
later commits underneath the release commit, the tagged tree claims fixes the packaged pck
does not contain. Compare the commit timestamps against the zip's mtime, and confirm an
expected asset is really inside before you publish or upload:

```sh
strings -a <Mod>.pck | grep <asset-name>
```

Rebuild and repackage if it is not there.

Before any rewrite of published history, save a backup tag first, and afterwards confirm
only the version and changelog files differ:

```sh
git tag backup/pre-rewrite-vX.Y.Z main
git diff --stat backup/pre-rewrite-vX.Y.Z main
```

## The release commit holds exactly two files

The manifest and `CHANGELOG.md`. `publish-release` relies on that to decide it is safe to
auto-commit, and refuses when anything else is pending. If other changes are staged,
commit them separately first.

## The Steam Workshop upload is a separate manual step

Neither `release` nor `publish-release` touches Steam. The upload runs through MegaCrit's
uploader against the repo's `workshop/` folder, with Steam running and logged in. The
repo's `RELEASING.md` and the maintainer's own notes carry the platform setup.

Two rules that cost a day to learn:

- **Always upload with `previews/` populated, every time.** The updater returns early when
  the folder is absent, so a "metadata only" upload refreshes no previews, and slots rot
  on Steam's side until an upload touches them.
- **Every file in `previews/` becomes a preview.** Godot `.import` files and `.DS_Store`
  have each shipped as a broken preview slot. Run `ls -a` before every upload.

Changing preview filenames forces a full rebuild of the slots, one file per upload, because
the add order follows directory enumeration rather than sort order.

## Done means

The tag is an ancestor of the branch tip, the GitHub Release carries the zip and the notes
from `dist/`, and the packaged pck really contains the change you are shipping.

## Framework knowledge lives in the guides

- `building` for what the build and the pck export actually do
- `troubleshooting` for a build that fails after a game update
