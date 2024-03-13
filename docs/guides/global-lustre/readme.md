---
authors: Blake Devcich <blake.devcich@hpe.com>
categories: provisioning
---

# Global Lustre

## Background

Adding global lustre to rabbit systems allows access to external file systems. This is primarily
used for Data Movement, where a user can perform `copy_in` and `copy_out` directives with global
lustre being the source and destination, respectively.

Global lustre fileystems are represented by the `lustrefilesystems` resource in Kubernetes:

```shell
$ kubectl get lustrefilesystems -A
NAMESPACE   NAME       FSNAME   MGSNIDS          AGE
default     mylustre   mylustre 10.1.1.113@tcp   20d
```

An example resource is as follows:

```yaml
apiVersion: lus.cray.hpe.com/v1beta1
kind: LustreFileSystem
metadata:
  name: mylustre
  namespace: default
spec:
  mgsNids: 10.1.1.100@tcp
  mountRoot: /p/mylustre
  name: mylustre
  namespaces:
    default:
      modes:
        - ReadWriteMany
```

## Namespaces

Note the `spec.namespaces` field. For each namespace listed, the `lustre-fs-operator` creates a
PV/PVC pair in that namespace. This allows pods in that namespace to access global lustre. The
`default` namespace should appear in this list. This makes the `lustrefilesystem` resource available
to the `default` namespace, which makes it available to containers (e.g.  container workflows)
running in the `default` namespace.

The `nnf-dm-system` namespace is added automatically - no need to specify that manually here. The
NNF Data Movement Manager is responsible for ensuring that the `nnf-dm-system` is in
`spec.namespaces`. This is to ensure that the NNF DM Worker pods have global lustre mounted as long
as `nnf-dm` is deployed. **To unmount global lustre from the NNF DM Worker pods, the
`lustrefilesystem` resource must be deleted**.

The `lustrefilesystem` resource itself should be created in the `default` namespace (i.e.
`metadata.namespace`).

## NNF Data Movement Manager

The NNF Data Movement Manager is responsible for monitoring `lustrefilesystem` resources to mount
(or umount) the global lustre filesystem in each of the NNF DM Worker pods. These pods run on each
of the NNF nodes. This means with each addition or removal of `lustrefilesystems` resources, the DM
worker pods restart to adjust their mount points.

The NNF Data Movement Manager also places a finalizer on the `lustrefilesystem` resource to indicate
that the resource is in use by Data Movement. This is to prevent the PV/PVC being deleted while they
are being used by pods.

## Adding Global Lustre

As mentioned previously, the NNF Data Movement Manager monitors these resources and automatically
adds the `nnf-dm-system` namespace to all `lustrefilesystem` resources. Once this happens, a PV/PVC
is created for the `nnf-dm-system` namespace to access global lustre. The Manager updates the NNF DM
Worker pods, which are then restarted to mount the global lustre file system.

## Removing Global Lustre

When a `lustrefilesystem` is deleted, the NNF DM Manager takes notice and starts to unmount the file
system from the DM Worker pods - causing another restart of the DM Worker pods. Once this is
finished, the DM finalizer is removed from the `lustrefilesystem` resource to signal that it is no
longer in use by Data Movement.

If a `lustrefilesystem` does not delete, check the finalizers to see what might still be using it.
It is possible to get into a situation where `nnf-dm` has been undeployed, so there is nothing to
remove the DM finalizer from the `lustrefilesystem` resource. If that is the case, then manually
remove the DM finalizer so the deletion of the `lustrefilesystem` resource can continue.
