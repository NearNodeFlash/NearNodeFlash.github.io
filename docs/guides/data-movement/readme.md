---
authors: Blake Devcich <blake.devcich@hpe.com>
categories: provisioning
---

# Data Movement Configuration

Data Movement can be configured in multiple ways:

1. Server side (`NnfDataMovementProfile`)
2. Copy offload API server

The first method is a "global" configuration - it affects all data movement operations that use a
particular `NnfDataMovementProfile` (or the default). The second is done per the `copy offload` API,
which allows for some configuration on a per-case basis, but is limited in scope. Both methods are
meant to work in tandem.

## Data Movement Profiles

The server side configuration is controlled by creating `NnfDataMovementProfiles` resources in
Kubernetes. These work similar to `NnfStorageProfiles`. See [here](../storage-profiles/readme.md)
for understanding how to use profiles, set a default, etc.

For an in-depth understanding of the capabilities offered by Data Movement profiles, we recommend
referring to the following resources:

- [Type definition](https://github.com/NearNodeFlash/nnf-sos/blob/master/api/v1alpha6/nnfdatamovementprofile_types.go#L27) for `NnfDataMovementProfile`
- [Sample](https://github.com/NearNodeFlash/nnf-sos/blob/master/config/samples/nnf_v1alpha6_nnfdatamovementprofile.yaml) for `NnfDataMovementProfile`
- [Online Examples](https://github.com/NearNodeFlash/nnf-sos/blob/master/config/examples/nnf_nnfdatamovementprofile.yaml) for `NnfDataMovementProfile`

## Copy Offload API Server

The `copy offload` API allows the user's compute application to specify options for particular Data Movement operations. These settings are on a per-request basis and supplement the configuration in the `NnfDataMovementProfile`.

The copy offload API requires the `copy-offload` server to be running on the Rabbit node. This server is implemented as a [User Container](../user-containers/readme.md) and is activated by the user's job script. The user's compute application must be linked with the `libcopyoffload` library.

See [Copy Offload](../data-movement/copy-offload.md) for details about the usage and lifecycle of the copy offload API server.

## SELinux and Data Movement

Careful consideration must be taken when enabling SELinux on compute nodes. Doing so will result in
SELinux Extended File Attributes (xattrs) being placed on files created by applications running on
the compute node, which may not be supported by the destination file system (e.g. Lustre).

Depending on the configuration of `dcp`, there may be an attempt to copy these xattrs. You may need
to disable this by using `dcp --xattrs none` to avoid errors. For example, the `command` in the
`NnfDataMovementProfile` or `dcpOptions` in the [DataMovementCreateRequest
API](copy-offload-api.html#datamovement.DataMovementCreateRequest) could be used to set this
option.

See the [`dcp` documentation](https://mpifileutils.readthedocs.io/en/latest/dcp.1.html) for more
information.

## `sshd` Configuration for Data Movement Workers

The `nnf-dm-worker-*` pods run `sshd` in order to listen for `mpirun` jobs to perform data movement.
The number of simultaneous connections is limited via the sshd configuration (i.e. `MaxStartups`).
**If you see error messages in Data Movement where mpirun cannot communicate with target nodes,
and you have ruled out any networking issues, this may be due to sshd configuration.** `sshd` still
start rejecting connections once the limit is reached.

The `sshd_config` is stored in the `nnf-dm-worker-config` `ConfigMap` so that it can be changed on
a running system without needing to roll new images. This also enables site-specific configuration.

## Enabling Core Dumps

### Mounting core dump Volumes

First, you must determine how your nodes handle core dumps. For example, if `systemd-coredump` is
used, then core dumps inside containers will be moved to the host node automatically. If that is
not the case, then a directory on the host nodes will need to be mounted into the Data Movement
containers. This directory will contain any core dumps collected by data movement operations, mainly
`mpirun` or `dcp`.

For Data Movement, the pods are running on two types of Kubernetes nodes:

- `nnf-dm-worker` pods on Rabbit nodes
- `nnf-dm-controller` pods on Kubernetes worker nodes

For all of these nodes, a core dump directory will need to be present and consistent across the
nodes. Once in place, we can then edit the Kubernetes configuration to mount this directory from
the host node to the containers using a [`hostPath`
Volume](https://kubernetes.io/docs/concepts/storage/volumes/#hostpath).

Adding this configuration will be done via the gitops repository for the system. Patches will be used
to patch the `nnf-dm` containers to mount the core dump directory via a `hostPath` volume.

An example of this configuration is provided in
[`argocd-boilerplate`](https://github.com/NearNodeFlash/argocd-boilerplate/tree/main/environments/example-env/nnf-dm).
There are two patch files that add Volumes to mount `/localdisk/dumps` from the host node at the
same location inside the containers.

- [`dm-controller-coredumps.yaml`](https://github.com/NearNodeFlash/argocd-boilerplate/blob/main/environments/example-env/nnf-dm/dm-controller-coredumps.yaml)
- [`dm-manager-coredumps.yaml`](https://github.com/NearNodeFlash/argocd-boilerplate/blob/main/environments/example-env/nnf-dm/dm-manager-coredumps.yaml)

[`kustomization.yaml`](https://github.com/NearNodeFlash/argocd-boilerplate/blob/main/environments/example-env/nnf-dm/kustomization.yaml#L13C1-L24C29)
then applies these patches to the correct resources.

### Editing the Data Movement Command

Once the volume is in place, the Data Movement command must be updated to first `cd` into this
directory. This ensures that the core dump is placed in that directory, making it accessible on the
host node.

To achieve this, update the Data Movement profiles in your gitops repository to include a preceding
`cd /localdisk/dumps && ...` in the `command` before the Data Movement command. For example, the default profile in `environments/<system>/nnf-sos/default-nnfdatamovementprofile.yaml` would look like the following:

```yaml
kind: NnfDataMovementProfile
metadata:
  name: default
  namespace: nnf-system
data:
  command: ulimit -n 2048 && cd /localdisk/dumps && mpirun --allow-run-as-root --hostfile $HOSTFILE dcp --progress
    1 --uid $UID --gid $GID $SRC $DEST
```

Note that core patterns for containers are inherited from the host and that Linux containers do not
support a container-only core pattern without also affecting the host node. This is why we must use
a preceding `cd <dir>` in the Data Movement command.

### Data Movement Debug Images

To help with debugging symbols, it is a good idea to use the `debug` version of the two images used by the Data Movement containers:

- `nnf-mfu-debug`
- `nnf-dm-debug`

Both of these images include debugging symbols for [Open MPI](https://www.open-mpi.org/) and [mpiFileUtils](https://mpifileutils.readthedocs.io/en/v0.11.1/).

To use these images, edit the `environments/<system>/nnf-dm/kustomization.yaml` in your gitops repository and add the following:

```yaml
# Use images with mpifileutils/mpirun debug symbols
images:
- name: ghcr.io/nearnodeflash/nnf-dm
  newName: ghcr.io/nearnodeflash/nnf-dm-debug
- name: ghcr.io/nearnodeflash/nnf-mfu
  newName: ghcr.io/nearnodeflash/nnf-mfu-debug
```

This will override the default images and use the debug symbols instead.
