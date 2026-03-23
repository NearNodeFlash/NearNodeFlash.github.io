# Releasing NNF Software

## NNF Software Overview

The following repositories comprise the NNF Software and each have their own versions. There is a
hierarchy, since `nnf-deploy` packages the individual components together using submodules.

Each component under `nnf-deploy` needs to be released first, then `nnf-deploy` can be updated to
point to those release versions, then `nnf-deploy` itself can be updated and released.

The documentation repo (NearNodeFlash/NearNodeFlash.github.io) is released separately and is not
part of `nnf-deploy`, but it should match the version number of `nnf-deploy`. Release this like the
other components.

- [NearNodeFlash/nnf-deploy](https://github.com/NearNodeFlash/nnf-deploy)

  - [DataWorkflowServices/dws](https://github.com/DataWorkflowServices/dws)
  - [HewlettPackard/lustre-csi-driver](https://github.com/HewlettPackard/lustre-csi-driver)
  - [NearNodeFlash/lustre-fs-operator](https://github.com/NearNodeFlash/lustre-fs-operator)
  - [NearNodeFlash/nnf-mfu](https://github.com/NearNodeFlash/nnf-mfu) *(standalone repo, not a submodule)*
  - [NearNodeFlash/nnf-ec](https://github.com/NearNodeFlash/nnf-ec) *(standalone repo, not a submodule)*
  - [NearNodeFlash/nnf-storedversions-maint](https://github.com/NearNodeFlash/nnf-storedversions-maint) *(standalone repo, not a submodule)*
  - [NearNodeFlash/nnf-sos](https://github.com/NearNodeFlash/nnf-sos)
  - [NearNodeFlash/nnf-dm](https://github.com/NearNodeFlash/nnf-dm)
  - [NearNodeFlash/nnf-integration-test](https://github.com/NearNodeFlash/nnf-integration-test)

- [NearNodeFlash/NearNodeFlash.github.io](https://github.com/NearNodeFlash/NearNodeFlash.github.io)

The release order matters because of dependency relationships between repos. The `release-all.sh`
tool enforces the following order:

1. `dws`
2. `lustre-csi-driver`
3. `lustre-fs-operator`
4. `nnf-mfu`
5. `nnf-ec`
6. `nnf-storedversions-maint` *(standalone repo)*
7. `nnf-sos` (depends on dws, nnf-mfu, nnf-ec)
8. `nnf-dm` (depends on dws, nnf-sos, nnf-mfu)
9. `nnf-integration-test` (depends on dws, nnf-sos, nnf-dm, lustre-fs-operator)
10. `nnf-deploy` (packages all submodules)
11. `NearNodeFlash.github.io` (documentation, version matches nnf-deploy)

## Overview of release-all tool

`release-all.sh` automates most of the steps of releasing NNF software and adds additional checks for common issues.

## Prerequisites

The following tools must be installed and available in your PATH:

| Tool | Purpose | Notes |
| --- | --- | --- |
| `gh` | GitHub CLI for PRs, releases | Requires `GH_TOKEN` env var (see below) |
| `yq` | YAML processing | Must be the [Go version](https://github.com/mikefarah/yq), not the Python version |
| `jq` | JSON processing | Used by `final-release-notes.sh` |
| `git` | Version control | SSH access to GitHub required |
| `make` | Build automation | Runs `make manifests`, `make generate`, etc. |
| `perl` | Version string manipulation | Used for semver bump calculations |
| `sed` | Text processing | |
| `tput` | Terminal formatting | |

**Environment variables:**

- `GH_TOKEN` — A GitHub **classic** personal access token (not fine-grained) with `repo` scope. The token is 40 characters, starting with `ghp_`. Required by `gh` and by the `release-push`, `create-pr`, `merge-pr`, and `tag-release` phases.

**SSH access:**

- Verify with `ssh -T git@github.com`. The release tool clones all repos via SSH.

## Assumptions

- `master` or `main` branch for each repository contains **tested** software and documentation ready to be released.

## Steps

### Run the steps in this order

> **Note:** You almost always want to use the `-R` option to focus the `phase` activity to a specific repo.
>
> Use `-B major|minor|patch` (default: `patch`) to control which part of the version number is bumped.

0. **List Repos:** Get the ordered list of repo names to use with `-R` option in subsequent steps. This is referred to as `repo-list`
    > **Pro tip:** Keep this list in a separate window for easy viewing

    ```bash
    ./release-all.sh -L
    ```

    The output will show the repos in dependency order:

    ```text
    dws
    lustre_csi_driver
    lustre_fs_operator
    nnf_mfu
    nnf_ec
    nnf_storedversions_maint
    nnf_sos
    nnf_dm
    nnf_integration_test
    nnf_deploy
    nnf_doc
    ```

1. **Check Vendoring:** For each repo's master/main branch; determine whether any of them need to be re-vendored.
    > **Note:** Ensure each repo is error-free before proceeding to the next repo in `repo-list`
    >
    > **Note:** `nnf_sos` requires the `-M` flag because it vendors multiple API versions of `dws`:
    >
    > ```bash
    > ./release-all.sh -P master -R nnf_sos -M
    > ```
    >
    > **Important:** Run vendoring checks on **all** repos, not just the ones you plan to release. This catches stale submodule pointers in `nnf-deploy` (e.g., a force-push on a submodule repo can leave the pointer at an orphaned commit SHA).

    ```bash
    For each repo in `repo-list`
        ./release-all.sh -P master -R $repo
    ```

2. **Create Trial Release Branch:** Create the new release branch, merge master/main to that release branch, but don't push it yet. The point of this step is to look for merge conflicts between master/main and the release branch.

    > **Note:** `nnf_mfu` and `nnf_storedversions_maint` may report "No new changes to release" if master/main has no commits since the last release. This is normal — skip them in subsequent steps.
    >
    > **Note:** `nnf_doc` must be deferred until after `nnf_deploy` is tagged and its GitHub Release is published. The `nnf_doc` script updates `mkdocs.yml` with the latest `nnf-deploy` release version by querying GitHub Releases (not just tags). Follow this sequence:
    >
    > 1. Complete Steps 2–3d for all repos through `nnf_deploy`
    > 2. **Wait ~60 seconds** for `nnf_deploy`'s "Handle Release Tag" GitHub Actions workflow to publish the GitHub Release
    > 3. Verify: `gh release view $NNF_RELEASE -R NearNodeFlash/nnf-deploy` should succeed
    > 4. Then run `nnf_doc` through Steps 2–3d
    >
    > **Important:** `nnf_doc`'s repo is `NearNodeFlash/NearNodeFlash.github.io` and uses the `main` branch (not `master`).

    ```bash
    For each repo in `repo-list`
        ./release-all.sh -P release -R $repo
    ```

3. **Generate Release:** For each repo in `repo-list`, proceed through the following steps in sequence before moving on to the next repo.
    > **Note:** The next steps use the `gh` GitHub CLI tool and require a `GH_TOKEN` environment variable containing a `repo` scope classic token.

    **Step 3a — Push the release branch.** Choose one of the following based on whether step 2 had merge conflicts:

    - If the **Create Trial Release Branch** had **no errors**:

        ```bash
        ./release-all.sh -P release-push -R <repo>
        ```

    - If **Create Trial Release Branch** was unable to auto merge, manually fix and merge the release branch, then re-run this phase on the existing branch:

        ```bash
        cd workingspace/<repo>
        # Manually merge the changes from master/main to the release branch
        go mod tidy
        go mod vendor
        git status # confirm all issues have been addressed
        git add <all affected files>
        git commit -s # take the default commit message, don't bother editing it.
        ```

        Then re-run this phase on this branch, telling the tool to pick up where you left off:

        ```bash
        USE_EXISTING_WORKAREA=1 ./release-all.sh -P release-push -R <repo>
        ```

    **Step 3b** — Create PR for the pushed release branch:

    ```bash
    ./release-all.sh -P create-pr -R <repo>
    ```

    **Step 3c** — Merge PR for the pushed release branch:

    > **Warning:** Do NOT manually merge the PR. Let `release-all.sh` merge it. If you accidentally merge manually, the `tag-release` phase may not find the expected merge commit message — use `-x force-tag=vX.Y.Z` to recover (see step 3d).
    >
    > **Note:** `merge-pr` may produce no visible output even on success. Verify the merge completed:
    >
    > ```bash
    > gh api repos/<owner>/<repo>/pulls/<pr_number> 2>&1 | grep -o '"merged":[^,]*'
    > ```
    >
    > Expected output: `"merged":true`

    ```bash
    ./release-all.sh -P merge-pr -R <repo>
    ```

    **Step 3d** — Tag the release:

    > **Important:** This creates an **annotated** git tag. The CI/CD workflow (`handle_release_tag.yaml`) verifies that the tag is annotated and will reject lightweight tags. After tagging, the CI/CD workflow automatically creates the GitHub release with auto-generated release notes and attaches build artifacts (e.g., `manifests.tar` for `nnf-deploy`).
    >
    > **Note:** `tag-release` output will include "Bypassed rule violations for refs/tags/...". This is expected. All NNF repos have tag protection rulesets that block creation, update, and deletion of `v*` tags by default. Your account bypasses these rules because it has an admin or maintain role in the ruleset's bypass list. The tags are created correctly.

    ```bash
    ./release-all.sh -P tag-release -R <repo>
    ```

    If tagging fails because the most recent commit doesn't contain the expected merge message (e.g., due to a manual merge), use the force-tag override:

    ```bash
    ./release-all.sh -P tag-release -R <repo> -x force-tag=vX.Y.Z
    ```

## Finalize the release notes

Finalize the release by updating the `nnf-deploy` release notes to include the release notes from all submodules that were modified by this release. This also updates the release notes for any submodule that has CRDs, to include information about each version of the CRD offered by that submodule. Do this after the release steps have been completed for all repositories, including the NearNodeFlash.github.io repository.

> **Note:** `final-release-notes.sh` requires `yq`, `gh`, `jq`, and `perl` to be installed, and `GH_TOKEN` to be set.

1. Generate complete release notes for the specified `nnf-deploy` release for review:

    ```bash
    ./final-release-notes.sh -r $NNF_RELEASE
    ```

2. Review the generated notes, then commit them:

    ```bash
    ./final-release-notes.sh -r $NNF_RELEASE -C
    ```

## Verify the release

After all repos are released and release notes are finalized, compare the new NNF release manifest to the previous release manifest. This is a recommended verification step to confirm the release contains the expected changes and catch any problems.

Use the `-i` flag to display image version changes inline:

```console
./compare-releases.sh -i $PREVIOUS_RELEASE $NNF_RELEASE
```

Example output:

```console
Manifest diffs for v0.1.26 to v0.1.27 are in workingspace/manifest-v0.1.26-to-v0.1.27.diff (21426 lines, 8 files changed)
Changed files:
Files v0.1.26/nnf-dm/nnf-dm.yaml and v0.1.27/nnf-dm/nnf-dm.yaml differ
Files v0.1.26/nnf-sos/nnf-sos.yaml and v0.1.27/nnf-sos/nnf-sos.yaml differ
...

Image version changes:
-        image: ghcr.io/nearnodeflash/nnf-dm:0.1.25
+        image: ghcr.io/nearnodeflash/nnf-dm:0.1.26
-        image: ghcr.io/nearnodeflash/nnf-sos:0.1.31
+        image: ghcr.io/nearnodeflash/nnf-sos:0.1.32
```

Use `-d` to display the full diff inline. The diff file is always saved to `workingspace/manifest-<ver1>-to-<ver2>.diff`.

Peruse the release manifest differences:

```console
less workingspace/manifest-v0.1.26-to-v0.1.27.diff
```

Quickly determine the scope of the differences between the releases:

```console
brew install patchutils diffstat
lsdiff workingspace/manifest-v0.1.26-to-v0.1.27.diff
diffstat workingspace/manifest-v0.1.26-to-v0.1.27.diff
```
