---
authors: Matt Richerson <matt.richerson@hpe.com>
categories: provisioning
---

# System Storage

## Background

System storage allows an admin to configure Rabbit storage without a DWS workflow. This is useful for making storage that is outside the scope of any job. One use case for system storage is to create a pair of LVM VGs on the Rabbit nodes that can be used to work around an `lvmlockd` bug. The lockspace for the VGs can be started on the compute nodes, holding the `lvm_global` lock open while other Rabbit VG lockspaces are started and stopped.

## NnfSystemStorage Resource

System storage is created through the `NnfSystemStorage` resource. By default, system storage creates an allocation on all Rabbits in the system and exposes the storage to all compute. This behavior can be modified through different fields in the `NnfSystemStorage` resource. A `NnfSystemStorage` storage resource has the following fields in its `Spec` section:

| Field | Required | Default | Value | Notes |
|-------|----------|---------|-------|-------|
| `SystemConfiguration` | No | Empty | `ObjectReference` to the `SystemConfiguration` to use | By default, the `default`/`default` `SystemConfiguration` is used |
| `IncludeRabbits` | No |Empty | A list of Rabbit node names | Rather than use all the Rabbits in the `SystemConfiguration`, only use the Rabbits contained in this list |
| `ExcludeRabbits` | No |Empty | A list of Rabbit node names | Use all the Rabbits in the `SystemConfiguration` except those contained in this list. |
| `IncludeComputes` | No | Empty | A list of compute node names | Rather than use the `SystemConfiguration` to determine which computes are attached to the Rabbit nodes being used, only use the compute nodes contained in this list |
| `ExcludeComputes` | No | Empty | A list of compute node names | Use the `SystemConfiguration` to determine which computes are attached to the Rabbits being used, but omit the computes contained in this list |
| `ComputesTarget` | Yes | `all` | `all`,`even`,`odd`,`pattern` | Only use certain compute nodes based on their index as determined from the `SystemConfiguration`. `all` uses all computes. `even` uses computes with an even index. `odd` uses computes with an odd index. `pattern` uses computes with the indexes specified in `Spec.ComputesPattern` |
| `ComputesPattern` | No | Empty | A list of integers [0-15] | If `ComputesTarget` is `pattern`, then the storage is made available on compute nodes with the indexes specified in this list. |
| `Capacity` | Yes | `1073741824` | Integer | Number of bytes to allocate per Rabbit |
| `Type` | Yes | `raw` | `raw`, `xfs`, `gfs2` | Type of file system to create on the Rabbit storage |
| `StorageProfile` | Yes | None | `ObjectReference` to an `NnfStorageProfile`. This storage profile must be marked as `pinned` |
| `MakeClientMounts` | Yes | `false` | Create `ClientMount` resources to mount the storage on the compute nodes. If this is `false`, then the devices are made available to the compute nodes without mounting the file system |
| `ClientMountPath` | No | None | Path to mount the file system on the compute nodes |

`NnfSystemResources` can be created in any namespace.

### Example

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfSystemStorage
metadata:
  name: gfs2-systemstorage
  namespace: systemstorage
spec:
  excludeRabbits:
  - "rabbit-1"
  - "rabbit-9"
  - "rabbit-14"
  excludeComputes:
  - "compute-32"
  - "compute-49"
  type: "gfs2"
  capacity: 10000000000
  computesTarget: "pattern"
  computesPattern:
  - 0
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
  - 7
  makeClientMounts: true
  clientMountPath: "/mnt/nnf/gfs2"
  storageProfile:
    name: gfs2-systemstorage
    namespace: systemstorage
    kind: NnfStorageProfile
```

## lvmlockd Workaround

System storage can be used to workaround an `lvmlockd` bug that occurs when trying to start the `lvm_global` lockspace. The `lvm_global` lockspace is started only when there is a volume group lockspace that is started. After the last volume group lockspace is stopped, then the `lvm_global` lockspace is stopped as well. To prevent the `lvm_global` lockspace from being started and stopped so often, a volume group is created on the Rabbits and shared with the computes. The compute nodes can start the volume group lockspace and leave it open.

The system storage can also be used to check whether the PCIe cables are attached correctly between the Rabbit and compute nodes. If the cables are incorrect, then the PCIe switch will make NVMe namespaces available to the wrong compute node. An incorrect cable can only result in compute nodes that have PCIe connections switched with the other compute node in its pair. By creating two system storages, one for compute nodes with an even index, and one for compute nodes with an odd index, the PCIe connection can be verified by checking that the correct system storage is visible on a compute node.

### Example

The following example resources show how to create two system storages to use for the `lvmlockd` workaround. Each system storage creates a `raw` allocation with a volume group but no logical volume. This is the minimum LVM set up needed to start a lockspace on the compute nodes. A `NnfStorageProfile` is created for each of the system storages. The `NnfStorageProfile` specifies a tag during the `vgcreate` that is used to differentiate between the two VGs. These resources are created in the `systemstorage` namespace, but they could be created in any namespace.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: lvmlockd_even
  namespace: systemstorage
data:
  xfsStorage:
    capacityScalingFactor: "1.0"
  lustreStorage:
    capacityScalingFactor: "1.0"
  gfs2Storage:
    capacityScalingFactor: "1.0"
  default: false
  pinned: true
  rawStorage:
    capacityScalingFactor: "1.0"
    commandlines:
      pvCreate: $DEVICE
      pvRemove: $DEVICE
      sharedVg: true
      vgChange:
        lockStart: --lock-start $VG_NAME
        lockStop: --lock-stop $VG_NAME
      vgCreate: --shared --addtag lvmlockd_even $VG_NAME $DEVICE_LIST
      vgRemove: $VG_NAME
```

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: lvmlockd_odd
  namespace: systemstorage
data:
  xfsStorage:
    capacityScalingFactor: "1.0"
  lustreStorage:
    capacityScalingFactor: "1.0"
  gfs2Storage:
    capacityScalingFactor: "1.0"
  default: false
  pinned: true
  rawStorage:
    capacityScalingFactor: "1.0"
    commandlines:
      pvCreate: $DEVICE
      pvRemove: $DEVICE
      sharedVg: true
      vgChange:
        lockStart: --lock-start $VG_NAME
        lockStop: --lock-stop $VG_NAME
      vgCreate: --shared --addtag lvmlockd_odd $VG_NAME $DEVICE_LIST
      vgRemove: $VG_NAME
```

Note that the `NnfStorageProfile` resources are marked as `default: false` and `pinned: true`. This is required for `NnfStorageProfiles` that are used for system storage. The `commandLine` fields for LV commands are left empty so that no LV is created.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfSystemStorage
metadata:
  name: lvmlockd_even
  namespace: systemstorage
spec:
  type: "raw"
  computesTarget: "even"
  makeClientMounts: false
  storageProfile:
    name: lvmlockd_even
    namespace: systemstorage
    kind: NnfStorageProfile
```

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfSystemStorage
metadata:
  name: lvmlockd_odd
  namespace: systemstorage
spec:
  type: "raw"
  computesTarget: "odd"
  makeClientMounts: false
  storageProfile:
    name: lvmlockd_odd
    namespace: systemstorage
    kind: NnfStorageProfile
```

The two `NnfSystemStorage` resources each target all of the Rabbits but a different set of compute nodes. This will result in each Rabbit having two VGs and each compute node having one VG.

After the `NnfSystemStorage` resources are created, the Rabbit software will create the storage on the Rabbit nodes and make the LVM VG available to the correct compute nodes. At this point, the `status.ready` field will be `true`. If an error occurs, the `.status.error` field will describe the error.