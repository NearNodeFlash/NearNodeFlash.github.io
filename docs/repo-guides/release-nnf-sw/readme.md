---
authors: Blake Devcich <blake.devcich@hpe.com>
categories: release, repo
---

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
    - [HewlettPackard/dws](https://github.com/HewlettPackard/dws)
    - [NearNodeFlash/lustre-fs-operator](https://github.com/NearNodeFlash/lustre-fs-operator)
    - [HewlettPackard/lustre-csi-driver](https://github.com/HewlettPackard/lustre-csi-driver)
    - [NearNodeFlash/nnf-mfu](https://github.com/NearNodeFlash/nnf-mfu)
    - [NearNodeFlash/nnf-sos](https://github.com/NearNodeFlash/nnf-sos)
    - [NearNodeFlash/nnf-dm](https://github.com/NearNodeFlash/nnf-dm)
- [NearNodeFlash/NearNodeFlash.github.io](https://github.com/NearNodeFlash/NearNodeFlash.github.io)

[nnf-ec](https://github.com/NearNodeFlash/nnf-ec) is vendored in as part of `nnf-sos` and does not
need to be released separately.

## Primer

This document is based on the process set forth by the [DataWorkflowServices Release
Process](https://dataworkflowservices.github.io/v0.0.1/repo-guides/create-a-release/readme/).
Please read that as a background for this document before going any further.

## Requirements

To create tags and releases, you will need maintainer or admin rights on the repos.

## Release Each Component In `nnf-deploy`

You'll first need to create releases for each component contained in `nnf-deploy`. This section
describes that process.

Each release branch needs to be updated with what is on master. To do that, we'll need the latest
copy of master, and it will ultimately be merged to the `releases/v0` branch via a Pull Request.
Once merged, an annotated tag is created and then a release.

Each component has its own version number that needs to be incremented. **Make sure you change the
version numbers** in the commands below to match the new version for the component. The `v0.0.3` is
just an example.

1. Ensure your branches are up to date:

    ```shell
    git checkout master
    git pull
    git checkout releases/v0
    git pull
    ```

2. Create a branch to merge into the release branch:

    ```shell
    git checkout -b release-v0.0.3
    ```

3. Merge in the updates from the `master` branch. There **should not** be any conflicts, but it's
   not unheard of. Tread carefully if there are conflicts.

    ```shell
    git merge master
    ```

4. Verify that there are no differences between your branch and the master branch:

    ```shell
    git diff master
    ```

    If there are any differences, they must be trivial. Some READMEs may have extra lines at the
    end.

5. For `lustre-csi-driver` and `lustre-fs-operator`, there are additional files that need to track
   the version number as well, which allow them to be installed with `kubectl apply -k`.

    a. For `lustre-fs-operator`, update `config/manager/kustomization.yaml` with the correct
    version.

    . For `lustre-csi-driver`, update `deploy/kubernetes/base/kustomization.yaml` and
    `charts/lustre-csi-driver/values.yaml` with the correct version.

6. Create a Pull Request from your branch and **target the release branch**. When merging the Pull
Request, **you must use a Merge Commit.**

    !!! note

        **Do not** Rebase or Squash! Those actions will remove the records that Git uses to determine which
        commits have been merged, and then when the next release is created Git will treat everything
        like a conflict. Additionally, this will cause auto-generated release notes to include the previous release.

7. Once merged, update the release branch locally and then create an annotated tag:

    ```shell
    git checkout releases/v0
    git tag -a v0.0.3 -m "Release v0.0.3"
    git push origin --tags
    ```

8. Now that there is a tag, a release can be created via the [GitHub CLI](https://cli.github.com/).
   Alternatively, use the [Web UI](https://github.com/NearNodeFlash/nnf-dm/releases/new).

    ```bash
    gh release create --generate-notes --verify-tag -p v0.0.3 -t "Release v0.0.3"
    ```

9. Repeat this process for each remaining component.

## Release `nnf-deploy`

Once the individual components are released, we need to update the submodules and
`config/repositories.yaml` in the **master** branch before we start on the release branch. This makes
sure that everything is now current on master.

1. Update the submodules on master:

    ```shell
    git checkout master
    git pull
    ./update.sh
    ```

2. Update `config/repositories.yaml` and update the referenced versions for:

   a. `lustre-csi-driver`

   b. `lustre-fs-operator`

   c. `nnf-mfu`

3. Commit the changes and open a Pull Request against the `master` branch.

4. Once merged, follow steps 1-3 from the previous section to update the release branch with master.

5. There will be conflicts on the submodules after step 3. This is expected. We will update the
   submodules to the new tags and then commit the changes.  If each tag was committed properly, the
   following command can do this for you:

    ```shell
    git submodule foreach 'git checkout `git describe --match="v*" HEAD`'
    ```

    Verify that each submodule is now at the proper tagged version.

    ```shell
    git submodule status
    ```

6. Do a `git add` for each of the submodules.

7. Run `go mod tidy` and then `make`. Do another `git add` for any changes, particularly`go.mod` and/or `go.sum`.

8. Verify that `git status` is happy with `nnf-deploy` and then finalize the merge from master by
   doing a `git commit`.

9. Follow steps 6-8 from the previous section to finalize the release of `nnf-deploy`.

The software is now released!
