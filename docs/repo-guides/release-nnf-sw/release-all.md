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
  - [NearNodeFlash/nnf-mfu](https://github.com/NearNodeFlash/nnf-mfu)
  - [NearNodeFlash/nnf-ec](https://github.com/NearNodeFlash/nnf-ec)
  - [NearNodeFlash/nnf-sos](https://github.com/NearNodeFlash/nnf-sos)
  - [NearNodeFlash/nnf-dm](https://github.com/NearNodeFlash/nnf-dm)
  - [NearNodeFlash/nnf-integration-test](https://github.com/NearNodeFlash/nnf-integration-test)

- [NearNodeFlash/NearNodeFlash.github.io](https://github.com/NearNodeFlash/NearNodeFlash.github.io)

## Overview of release-all tool

`release-all.sh` automates most of the steps of releasing NNF software and adds additional checks for common issues.

## Assumptions

- `master` or `main` branch for each repository contains **tested** software and documentation ready to be released.
- You've installed the GitHub CLI tool, `gh`.
  - This tool requires a GH_TOKEN environment variable containing a `repo` scope classic token.

## Steps

### Run the steps in this order

> **Note:** You almost always want to use the -R option to focus the `phase` activity to a specific repo.

0. **List Repos:** Get the ordered list of repo names to use with -R option in subsequent steps. This is referred to as `repo-list`
    > **Pro tip:** Keep this list in a separate window for easy viewing
    ./release-all.sh -L

1. **Check Vendoring:** For each repo's master/main branch; determine whether any of them need to be re-vendored.
    > **Note:** Ensure each repo is error-free before proceeding to the next repo in `repo-list`

    ```bash
    For each repo in `repo-list`
        ./release-all.sh -P master -R $repo
    ```

2. **Create Trial Release Branch:** Create the new release branch, merge master/main to that release branch, but don't push it yet. The point of this step is to look for merge conflicts between master/main and the release branch.

    ```bash
    For each repo in `repo-list`
        ./release-all.sh -P release -R $repo
    ```

3. **Generate Release:** For each repo in `repo-list`, proceed through the following steps in sequence before moving on to the next repo.
    > **Note:** The next steps use the gh(1) GitHub CLI tool and require a GH_TOKEN environment variable containing a 'repo' scope classic token.
    1. If the **Create Trial Release Branch** had no errors:

        ```bash
        ./release-all.sh -P release-push -R <repo>
        ```

    2. If **Create Trial Release Branch** was unable to auto merge, manually fix and merge the release branch and re-run this phase on that existing branch:

        ```bash
        cd workingspace/repo
        # Manually merge the changes from master/main to the release branch
        go mod tidy
        go mod vendor
        git status # confirm all issues have been address
        git add <all affected files>
        git commit -s # take the default commit message, don't bother editing it.
        ```

        Then re-run this phase on this branch, telling the tool to pick up where you left off:

        ```bash
        USE_EXISTING_WORKAREA=1 ./release-all.sh -P release-push -R <repo>
        ```

    3. Create PR for the pushed release branch:

       ```bash
       ./release-all.sh -P create-pr -R <repo>
       ```

    3. Merge PR for the pushed release branch:
    **Note: Do NOT manually merge the PR, let `release-all.sh` merge it.**

       ```bash
       ./release-all.sh -P merge-pr -R <repo>
       ```

    4. Tag the release:

       ```bash
       ./release-all.sh -P tag-release -R <repo>
       ```

## Finalize the release notes

Finalize the release by updating the `nnf-deploy` release notes to include the release notes from all submodules that were modified by this release. Do this after the release steps have been completed for all repositories, including the NearNodeFlash.github.io repository.

1. Generate complete release notes for the specified `nnf-deploy` release for review:
**Note: If this release does not include a new release of the NearNodeFlash.github.io docs, then specify `-D` to skip the docs.**

    ```bash
    ./final-release-notes.sh -r $NNF_RELEASE [-D]
    ```

2. Generate and commit the release notes to the specified `nnf-deploy` release:

    ```bash
    ./final-release-notes.sh -r $NNF_RELEASE -C [-D]
    ```

## Compare release manifests

Compare the new NNF release manifest to a previous NNF release manifest. This can be useful for a variety of purposes. For example, this is a quick way to check for any problems in the release or to see which submodules were updated in the release.

```console
./compare-releases.sh v0.1.6 v0.1.7
```

The output:

```console
Manifest diffs for v0.1.6 to v0.1.7 are in workingspace/manifest-v0.1.6-to-v0.1.7.diff
```

Peruse the release manifest differences:

```console
less workingspace/manifest-v0.1.6-to-v0.1.7.diff
```

Quickly see which submodules were updated between the releases:

```console
grep image: workingspace/manifest-v0.1.6-to-v0.1.7.diff
```

Quickly determine the scope of the differences between the releases:

```console
brew install patchutils diffstat
lsdiff workingspace/manifest-v0.1.6-to-v0.1.7.diff
diffstat workingspace/manifest-v0.1.6-to-v0.1.7.diff
```
