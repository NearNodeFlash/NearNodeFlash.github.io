# CRD Upgrade Helpers

Two services must be installed on the cluster to assist in upgrading CustomResourceDefinitions (CRD), and the resources associated with them, as the CRDs acquire new API versions or remove old API versions. The first service is [kube-storage-version-migrator](https://github.com/NearNodeFlash/kube-storage-version-migrator/tree/nnf-main) (see the `nnf-main` branch), which updates existing custom resources to ensure they are stored in the **etcd** database at the API version that is the CRD's latest `storage` version. It does this whenever a CRD is updated with a new API version. The second service is [nnf-storedversions-maint](https://github.com/NearNodeFlash/nnf-storedversions-maint), which updates the `status.storedVersions` list in the CRD to remove the unused API versions. This maintenance is necessary to allow older API versions to be removed during future upgrades of those CRDs.

Together, these services implement [Upgrade existing objects to a new stored version](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/#upgrade-existing-objects-to-a-new-stored-version) in the Kubernetes documentation.

## ArgoCD/GitOps

The ArgoCD `Application` bootstraps for the two services can be found in the [argocd-boilerplate](https://github.com/NearNodeFlash/argocd-boilerplate) repository under `environments/example-env/0-bootstrap1/`. NNF release manifests include the manifests for these services.

## References

### Kubernetes

[Versions in CustomResourceDefinitions](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/)

[Upgrade existing objects to a new stored version](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/#upgrade-existing-objects-to-a-new-stored-version)

[kube-storage-version-migrator](https://github.com/kubernetes-sigs/kube-storage-version-migrator) migrates stored data in etcd to the latest storage version.

### NNF

[kube-storage-version-migrator](https://github.com/NearNodeFlash/kube-storage-version-migrator/tree/nnf-main) (see the `nnf-main` branch) migrates stored data in etcd to the latest storage version.

[nnf-storedversions-maint](https://github.com/NearNodeFlash/nnf-storedversions-maint) removes old API versions from a CRD's `status.storedVersions` field.

[CRD Version Bumper](../crd-bumper/readme.md) tools to add a new API version to a CRD, or to remove an old API version.
