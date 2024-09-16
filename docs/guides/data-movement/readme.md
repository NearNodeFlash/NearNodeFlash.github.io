---
authors: Blake Devcich <blake.devcich@hpe.com>
categories: provisioning
---

# Data Movement Overview

## Configuration

Data Movement can be configured in multiple ways:

1. Server side (`NnfDataMovementProfile`)
2. Per Copy Offload API Request arguments

The first method is a "global" configuration - it affects all data movement operations that use a
particular `NnfDataMovementProfile` (or the default). The second is done per the Copy Offload API,
which allows for some configuration on a per-case basis, but is limited in scope. Both methods are
meant to work in tandem.

### Data Movement Profiles

The server side configuration is controlled by creating `NnfDataMovementProfiles` resources in
Kubernetes. These work similar to `NnfStorageProfiles`. See [here](../storage-profiles/readme.md)
for understanding how to use profiles, set a default, etc.

For an in-depth understanding of the capabilities offered by Data Movement profiles, we recommend
referring to the following resources:

- [Type definition](https://github.com/NearNodeFlash/nnf-sos/blob/master/api/v1alpha1/nnfdatamovementprofile_types.go#L27) for `NnfDataMovementProfile`
- [Sample](https://github.com/NearNodeFlash/nnf-sos/blob/master/config/samples/nnf_v1alpha1_nnfdatamovementprofile.yaml) for `NnfDataMovementProfile`
- [Online Examples](https://github.com/NearNodeFlash/nnf-sos/blob/master/config/examples/nnf_v1alpha1_nnfdatamovementprofile.yaml) for `NnfDataMovementProfile`

### Copy Offload API Daemon

The `CreateRequest` API call that is used to create Data Movement with the Copy Offload API has some
options to allow a user to specify some options for that particular Data Movement operation. These
settings are on a per-request basis. These supplement the configuration in the
`NnfDataMovementProfile`.

The Copy Offload API requires the `nnf-dm` daemon to be running on the compute node. This daemon may
be configured to run full-time, or it may be left in a disabled state if the WLM is expected to run
it only when a user requests it. See [Compute Daemons](../compute-daemons/readme.md) for the systemd
service configuration of the daemon. See `RequiredDaemons` in [Directive
Breakdown](../directive-breakdown/readme.md) for a description of how the user may request the
daemon in the case where the WLM will run it only on demand.

See the [DataMovementCreateRequest API](copy-offload-api.html#datamovement.DataMovementCreateRequest)
definition for what can be configured.

### SELinux and Data Movement

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

### `sshd` Configuration for Data Movement Workers

The `nnf-dm-worker-*` pods run `sshd` in order to listen for `mpirun` jobs to perform data movement.
The number of simultaneous connections is limited via the sshd configuration (i.e. `MaxStartups`).
**If you see error messages in Data Movement where mpirun cannot communicate with target nodes,
and you have ruled out any networking issues, this may be due to sshd configuration.** `sshd` still
start rejecting connections once the limit is reached.

The `sshd_config` is stored in the `nnf-dm-worker-config` `ConfigMap` so that it can be changed on
a running system without needing to roll new images. This also enables site-specific configuration.
