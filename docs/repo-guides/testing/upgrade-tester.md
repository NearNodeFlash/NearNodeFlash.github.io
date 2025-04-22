# Upgrade Tester

The `upgrade-gitops-maker.sh` and `upgrade-tester.sh` tools are used together to execute upgrades across a series of releases. The former populates a gitops repo with the NNF releases, and the latter installs those releases.

## Basic flow

- Create the gitops repo. Use `upgrade-gitops-maker.sh` to create a gitops repo containing the release manifests.
- Create a KIND environment for use with NNF.
- Create a token for the gitops repo. This token is used to give ArgoCD access to the repo.
- Run `upgrade-tester.sh` to deploy a specified series of releases, performing release-to-release upgrades.

## Create a gitops repository

Use `upgrade-gitops-maker.sh` to create a gitops repository that is populated with the NNF releases. The [argocd-boilerplate](https://github.com/NearNodeFlash/argocd-boilerplate) is used to create the gitops repo.

This tool uses the [GitHub CLI tool](https://cli.github.com), and it must have a token with permission to create and write to the user's private repositories. It begins by creating the private repository on the user's GitHub account and then pushing to it as it builds up the releases.

```console
git clone git@github.com:NearNodeFlash/nnf-integration-test.git
cd nnf-integration-test/upgrade-tester
REPO_NAME=penguin
./upgrade-gitops-maker.sh -n $REPO_NAME
```

The new repo is named `gitops-$REPO_NAME`. The `upgrade-tester.sh` tool is in the `test-tools/` directory.

When complete, each release is placed in its own branch. *Note: This is an [anti-pattern for gitops repos](https://developers.redhat.com/articles/2022/07/20/git-workflows-best-practices-gitops-deployments), but it works well for this tool's purposes.*

The [CRD Upgrade Helpers](../release-nnf-sw/crd-upgrade-helpers.md) are added to some of the releases that did not originally have them, where their help has been necessary to allow upgrades to succeed. These branches have the `-svm` or `-nsvm` suffix.

Release branches `rel-v0.1.13-svm` and `rel-v0.1.14-svm` include the `storage-version-migrator` CRD upgrade helper. Release **v0.1.15** shipped with `storage-version-migrator` by default, so release branch `rel-v0.1.15-nsvm` includes the `nnf-storedversions-maint` CRD upgrade helper. All releases after **v0.1.15** ship with both CRD upgrade helpers and do not require `-svm` or `-nsvm` branches.

The `boilerplate-main` branch is pointing at [argocd-boilerplate](https://github.com/NearNodeFlash/argocd-boilerplate) and is described in [Tracking the ArgoCD Boilerplate Repo](https://github.com/NearNodeFlash/argocd-boilerplate/blob/main/Boilerplate-tracking.md). The `main` branch, in this case, contains only a few initial steps common to all releases and is not meant to be used.

```console
$ git branch 
  boilerplate-main
* main
  rel-v0.1.11
  rel-v0.1.12
  rel-v0.1.13
  rel-v0.1.13-svm
  rel-v0.1.14
  rel-v0.1.14-svm
  rel-v0.1.15
  rel-v0.1.15-nsvm
```

## Create a KIND cluster

Use the [nnf-deploy](https://github.com/NearNodeFlash/nnf-deploy) tools to create the KIND cluster and configure ArgoCD.

```console
git clone git@github.com:NearNodeFlash/nnf-deploy.git
cd nnf-deploy
./tools/kind.sh create
```

### Configure ArgoCD

Configure ArgoCD by giving it access to the gitops repo created earlier, using the token you created for that repo. At a minimum, the token must grant read-only access to the repo's contents. See [Using with KIND or a private repo](https://github.com/NearNodeFlash/argocd-boilerplate?tab=readme-ov-file#using-with-kind-or-a-private-repo) for details about creating the token.

```console
REPO_NAME=penguin
export ARGOCD_OPTS='--port-forward --port-forward-namespace argocd'
./tools/kind.sh argocd_attach $NEW_ARGO_PASSWORD
argocd repo add "$HTTPS_REPO_CLONE_URL" --username "$GH_USER" --password "$REPO_TOKEN" --name "gitops-$REPO_NAME"
```

## Run the upgrade test

The `upgrade-tester.sh` tool deploys specific releases and waits for each one to succeed. The user must specify the releases to be tested, identifying them by branch name. The tool uses `git checkout` to select a release and `./tools/deploy-env.sh` to deploy the bootstraps for that release. ArgoCD is monitored to determine when each upgrade has completed.

```console
git clone "$HTTPS_REPO_CLONE_URL" "$REPO_NAME"
cd $REPO_NAME
./test-tools/upgrade-tester.sh rel-v0.1.11 rel-v0.1.12 rel-v0.1.13-svm
```

## References

[NNF Releases](https://github.com/NearNodeFlash/nnf-deploy/releases)

[argocd-boilerplate](https://github.com/NearNodeFlash/argocd-boilerplate)

[nnf-deploy](https://github.com/NearNodeFlash/nnf-deploy)

[CRD Upgrade Helpers](../release-nnf-sw/crd-upgrade-helpers.md)

[GitHub CLI tool](https://cli.github.com)

[Kubernetes-in-Docker (KIND)](https://kind.sigs.k8s.io)
