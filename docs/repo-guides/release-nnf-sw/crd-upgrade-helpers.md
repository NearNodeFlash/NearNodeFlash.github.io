# CRD Upgrade Helpers

Two services must be installed on the cluster to assist in upgrading CustomResourceDefinitions (CRD), and the resources associated with them, as the CRDs acquire new API versions or remove old API versions. The first service is [kube-storage-version-migrator](https://github.com/NearNodeFlash/kube-storage-version-migrator/tree/nnf-main) (see the `nnf-main` branch), which updates existing custom resources to ensure they are stored in the **etcd** database at the API version that is the CRD's latest `storage` version. It does this whenever a CRD is updated with a new API version. The second service is [nnf-storedversions-maint](https://github.com/NearNodeFlash/nnf-storedversions-maint), which updates the `status.storedVersions` list in the CRD to remove the unused API versions. This maintenance is necessary to allow older API versions to be removed during future upgrades of those CRDs.

Together, these services implement [Upgrade existing objects to a new stored version](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/#upgrade-existing-objects-to-a-new-stored-version) in the Kubernetes documentation.

## ArgoCD/GitOps

The ArgoCD `Application` bootstraps for the two services can be found in the [argocd-boilerplate](https://github.com/NearNodeFlash/argocd-boilerplate) repository under `environments/example-env/0-bootstrap1/`. NNF release manifests include the manifests for these services.

## Debugging

Monitor the progress of `kube-storage-version-migrator` or `nnf-storedversions-maint` by watching their logs and by watching changes to a specific CRD.

For example, we may want to check the status of the `NnfStorageProfile` CRD after an upgrade that has added a new API version named "v1alpha7".

Begin by finding the full name of the CRD:

```console
kubectl get crds -o custom-columns=NAME:.metadata.name | grep nnfstorageprofile
```

That will return a name of "nnfstorageprofiles.nnf.cray.hpe.com". Next, query the `status.storedVersions` list on that CRD:

```console
kubectl get crds nnfstorageprofiles.nnf.cray.hpe.com -o json | jq -rM '.status.storedVersions'
```

That might return a list of API versions:

```console
[
  "v1alpha6",
  "v1alpha7"
]
```

This indicates that `kube-storage-version-migrator` has not finished migrating the resources of this type, or that `nnf-storedversions-maint` hasn't caught up.

Check the progress of `kube-storage-version-migrator`. Begin by looking for the `StorageVersionMigration` resource it uses to track this CRD:

```console
kubectl get storageversionmigrations --no-headers -o custom-columns=NAME:.metadata.name | grep nnfstorageprofile
```

In this case it might return a name that looks like "nnfstorageprofiles.nnf.cray.hpe.com-mcsnm". Note the auto-generated suffix. The migrator replaces this resource any time it works on the CRD, and then it'll get a new suffix.

Dump out the `StorageVersionMigration` resource to see the currrent status:

```console
apiVersion: migration.k8s.io/v1alpha1
kind: StorageVersionMigration
metadata:
  creationTimestamp: "2025-04-28T21:12:23Z"
  generateName: nnfstorageprofiles.nnf.cray.hpe.com-
  generation: 1
  name: nnfstorageprofiles.nnf.cray.hpe.com-mcsnm
  resourceVersion: "35307472"
  uid: ead6c3cf-8554-4400-aeea-e8ea5a59bf40
spec:
  resource:
    group: nnf.cray.hpe.com
    resource: nnfstorageprofiles
    version: v1alpha7
status:
  conditions:
  - lastUpdateTime: "2025-04-28T21:12:26Z"
    status: "True"
    type: Succeeded
```

That looks like it completed the migration of these resources to the new "v1alpha7" API version. In this case, the "lastUpdateTime" just happens to be a few seconds ago.

The `nnf-storedversions-maint` should have had a chance to respond to this by now, so look at the CRD again:

```console
kubectl get crds nnfstorageprofiles.nnf.cray.hpe.com -o json | jq -rM '.status.storedVersions'
```

The list contains only the "v1alpha7" API:

```console
[
  "v1alpha7"
]
```

These activities can also be followed in the logs of the respective services.

## References

### Kubernetes

[Versions in CustomResourceDefinitions](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/)

[Upgrade existing objects to a new stored version](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/#upgrade-existing-objects-to-a-new-stored-version)

[kube-storage-version-migrator](https://github.com/kubernetes-sigs/kube-storage-version-migrator) migrates stored data in etcd to the latest storage version.

### NNF

[kube-storage-version-migrator](https://github.com/NearNodeFlash/kube-storage-version-migrator/tree/nnf-main) (see the `nnf-main` branch) migrates stored data in etcd to the latest storage version.

[nnf-storedversions-maint](https://github.com/NearNodeFlash/nnf-storedversions-maint) removes old API versions from a CRD's `status.storedVersions` field.

[CRD Version Bumper](../crd-bumper/readme.md) tools to add a new API version to a CRD, or to remove an old API version.
