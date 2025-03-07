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

  - [DataWorkflowServices/dws](https://github.com/DataWorkflowServices/dws)
  - [HewlettPackard/lustre-csi-driver](https://github.com/HewlettPackard/lustre-csi-driver)
  - [NearNodeFlash/lustre-fs-operator](https://github.com/NearNodeFlash/lustre-fs-operator)
  - [NearNodeFlash/nnf-mfu](https://github.com/NearNodeFlash/nnf-mfu)
  - [NearNodeFlash/nnf-ec](https://github.com/NearNodeFlash/nnf-ec)
  - [NearNodeFlash/nnf-sos](https://github.com/NearNodeFlash/nnf-sos)
  - [NearNodeFlash/nnf-dm](https://github.com/NearNodeFlash/nnf-dm)
  - [NearNodeFlash/nnf-integration-test](https://github.com/NearNodeFlash/nnf-integration-test)

- [NearNodeFlash/NearNodeFlash.github.io](https://github.com/NearNodeFlash/NearNodeFlash.github.io)

## Primer

This document is based on the process set forth by the [DataWorkflowServices Release
Process](https://dataworkflowservices.github.io/latest/repo-guides/create-a-release/readme/).
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

5. Perform repo-specific updates:

    1. For `lustre-csi-driver`, `lustre-fs-operator`, `dws`, `nnf-sos`, and `nnf-dm` there are additional files that need to
    track the version number as well, which allow them to be installed with `kubectl apply -k`.

    |Repo                 |Update|
    |---------------------|------|
    |`nnf-mfu`            |The new version of `nnf-mfu` is referenced by the `NNFMFU` variable in several places:<br><br>`nnf-sos`<br>1. `Makefile` replace `NNFMFU` with `nnf-mfu's` tag.<br><br>`nnf-dm`<br>1. In `Dockerfile` and `Makefile`, replace `NNFMFU_VERSION` with the new version.<br>2. In `config/manager/kustomization.yaml`, replace `nnf-mfu`'s `newTag: <X.Y.Z>.`<br><br>`nnf-deploy`<br>1. In `config/repositories.yaml` replace `NNFMFU_VERSION` with the new version.|
    |`lustre-fs-operator` |update `config/manager/kustomization.yaml` with the correct version.<br><br>`nnf-deploy`<br>1. In `config/repositories.yaml` replace the lustre-fs-operator version.|
    |`dws`                |update `config/manager/kustomization.yaml` with the correct version.|
    |`nnf-sos`            |update `config/manager/kustomization.yaml` with the correct version.|
    |`nnf-dm`             |update `config/manager/kustomization.yaml` with the correct version.|
    |`lustre-csi-driver`  |update `deploy/kubernetes/base/kustomization.yaml` and `charts/lustre-csi-driver/values.yaml` with the correct version.<br><br>`nnf-deploy`<br>1. In `config/repositories.yaml` replace the lustre-csi-driver version.|

6. **Target the `releases/v0` branch** with a Pull Request from your branch.  When merging the Pull
Request, **you must use a Merge Commit.**

    !!! note
        **Do not** Rebase or Squash! Those actions remove the records that Git uses to
        determine which commits have been merged, and then when the next release is created Git will
        treat everything like a conflict. Additionally, this will cause auto-generated release notes
        to include the previous release.

7. Once merged, update the release branch locally and create an annotated tag. Each repo has a workflow job named `create_release` that will create a release automatically when the new tag is pushed.

    ```shell
    git checkout releases/v0
    git pull
    git tag -a v0.0.3 -m "Release v0.0.3"
    git push origin --tags
    ```

8. GOTO Step 1 and repeat this process for each remaining component.

## Release `nnf-deploy`

Once the individual components are released, we need to update the submodules
in `nnf-deploy's` `master` branch before we create the release branch. This ensures
that everything is current on `master` for `nnf-deploy`.

1. Update the submodules for `nnf-deploy` on master:

    ```shell
    cd nnf-deploy
    git checkout master
    git pull
    git submodule foreach git checkout master
    git submodule foreach git pull
    ```

2. Create a branch to capture the submodule changes for the PR to `master`

    ```shell
    git checkout -b update-submodules
    ```

3. Commit the changes and open a Pull Request against the `master` branch.

4. Once merged, follow steps 1-3 from the previous section to create a release branch off of `releases/v0` and
   update it with changes from `master`.

5. There will be conflicts for the submodules after step 3. **This is expected.** Update the
   submodules to the new tags and then commit the changes.  If each tag was committed properly, the
   following command can do this for you:

    ```shell
    git submodule foreach 'git checkout `git describe --match="v*" HEAD`'
    ```

6. Add each submodule to the commit with `git add`.

7. Verify that each submodule is now at the proper tagged version.

    ```shell
    git submodule
    ```

8. Update `config/repositories.yaml` with the referenced versions for:

    1. `lustre-csi-driver`
    2. `lustre-fs-operator`
    3. `nnf-mfu`  (Search for NNFMFU_VERSION)

9. Tidy and make `nnf-deploy` to avoid embarrassment.

    ```shell
    go mod tidy
    make
    ```

10. Do another `git add` for any changes, particularly `go.mod` and/or `go.sum`.

11. Verify that `git status` is happy with `nnf-deploy` and then finalize the merge
    from master by with a `git commit`.

12. Follow steps 6-7 from the previous section to finalize the release of `nnf-deploy`.

## Release `NearNodeFlash.github.io`

**Please review and update the documentation for changes you may have made.**

After nnf-deploy has a release tag, you may release the documentation. Use the same steps found above in "Release Each Component". Note that the default branch for this repo is "main" instead of "master".

Give this release a tag that matches the nnf-deploy release, to show that they go together. Create the release by using the "Create release" or "Draft a new release" button in the GUI, or by using the `gh release create` CLI command. Whether using the GUI or the CLI, mark the release as "latest" and select the appropriate option to generate release notes.

Wait for the `mike` tool in `.github/workflow/release.yaml` to finish building the new doc. You can check its status by going to the `gh-pages` branch in the repo. When you visit the release at [https://nearnodeflash.github.io](https://nearnodeflash.github.io), you should see the new release in the drop-down menu and the new release should be the default display.

**The software is now released!**

## Clone a release

The follow commands clone release `v0.0.7` into `nnf-deploy-v0.0.7`

```shell
export NNF_VERSION=v0.0.7

git clone --recurse-submodules git@github.com:NearNodeFlash/nnf-deploy nnf-deploy-$NNF_VERSION
cd nnf-deploy-$NNF_VERSION
git -c advice.detachedHead=false checkout $NNF_VERSION --recurse-submodules

git submodule status
```
