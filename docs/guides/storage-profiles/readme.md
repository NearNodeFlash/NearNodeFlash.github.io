---
authors: Nate Thornton <nate.thornton@hpe.com>, Dean Roehrich <dean.roehrich@hpe.com>, Matt Richerson <matthew.richerson@hpe.com>
categories: provisioning
---

# Storage Profiles

Storage Profiles provide a way to customize how storage is provisioned and configured on Rabbit nodes. They allow administrators to define specific configurations for different file system types, RAID configurations, and storage layouts that users can select when submitting jobs.

## What Are Storage Profiles?

An `NnfStorageProfile` is a Kubernetes Custom Resource that defines how storage should be configured on Rabbit nodes. Storage profiles control:

- **File system type configuration** - Commands and options for XFS, GFS2, Raw, and Lustre file systems
- **Block device configuration** - LVM commands for creating physical volumes, volume groups, and logical volumes
- **RAID configurations** - Settings for redundant storage using LVM RAID or ZFS RAID
- **Target layouts** - How Lustre targets (MGT, MDT, OST) are distributed across Rabbit nodes
- **User commands** - Custom commands that run at various points in the storage lifecycle

Storage profiles are stored in the `nnf-system` namespace and are referenced by name in `#DW` directives.

## Default vs. Non-Default Profiles

### Default Profile

Every NNF system must have exactly one storage profile marked as the default. The default profile is used when a `#DW` directive does not specify a profile. If zero or more than one profile is marked as default, new workflows will be rejected.

A profile is marked as default by setting `data.default: true`:

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha9
kind: NnfStorageProfile
metadata:
  name: default
  namespace: nnf-system
data:
  default: true
  # ... rest of profile configuration
```

### Querying Profiles

To list all storage profiles and see which is the default:

```shell
kubectl get nnfstorageprofiles -n nnf-system
```

Example output:

```
NAME        DEFAULT   AGE
default     true      14d
high-perf   false     7d
durable     false     7d
template    false     14d
```

### Setting the Default Profile

To set a profile as the default:

```shell
kubectl patch nnfstorageprofile high-perf -n nnf-system --type merge -p '{"data":{"default":true}}'
```

To clear the default flag from a profile:

```shell
kubectl patch nnfstorageprofile default -n nnf-system --type merge -p '{"data":{"default":false}}'
```

> **Note:** Ensure exactly one profile is marked as default at all times.

## Specifying a Profile in #DW Directives

To use a non-default storage profile, add the `profile` parameter to your `#DW` directive:

```shell
#DW jobdw type=xfs profile=high-perf capacity=100GB name=my-storage
```

```shell
#DW jobdw type=lustre profile=durable capacity=1TB name=my-lustre
```

```shell
#DW create_persistent type=lustre profile=persistent-lustre capacity=10TB name=shared-fs
```

If no `profile` parameter is specified, the default profile is used.

## File System Configuration

Storage profiles contain configuration sections for each supported file system type:

- `xfsStorage` - XFS file system configuration
- `gfs2Storage` - GFS2 file system configuration  
- `rawStorage` - Raw block device configuration
- `lustreStorage` - Lustre file system configuration

### XFS Storage

XFS is a high-performance journaling file system suitable for single-node or exclusive access workloads.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha9
kind: NnfStorageProfile
metadata:
  name: xfs-example
  namespace: nnf-system
data:
  default: false
  xfsStorage:
    # Block device configuration (LVM)
    blockDeviceCommands:
      sharedVg: true
      rabbitCommands:
        pvCreate: $DEVICE
        pvRemove: $DEVICE
        vgCreate: --addtag $JOBID $VG_NAME $DEVICE_LIST
        vgRemove: $VG_NAME
        lvCreate: --zero n --activate n --size $LV_SIZE --stripes $DEVICE_NUM --stripesize=32KiB --name $LV_NAME $VG_NAME
        lvRemove: $VG_NAME/$LV_NAME
        lvChange:
          activate: --activate y $VG_NAME/$LV_NAME
          deactivate: --activate n $VG_NAME/$LV_NAME
      computeCommands:
        lvChange:
          activate: --activate y $VG_NAME/$LV_NAME
          deactivate: --activate n $VG_NAME/$LV_NAME

    # File system commands
    fileSystemCommands:
      rabbitCommands:
        mkfs: $DEVICE
        mount: $DEVICE $MOUNT_PATH
      computeCommands:
        mount: $DEVICE $MOUNT_PATH

    # User commands run during setup/teardown
    userCommands:
      postSetup:
      - chown $USERID:$GROUPID $MOUNT_PATH

    # Capacity scaling factor (1.0 = request exactly what user specified)
    capacityScalingFactor: "1.0"
    
    # Extra allocation padding for block device overhead
    allocationPadding: 300MiB
```

### GFS2 Storage

GFS2 is a shared-disk cluster file system that allows multiple nodes to access the same file system simultaneously.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha9
kind: NnfStorageProfile
metadata:
  name: gfs2-example
  namespace: nnf-system
data:
  default: false
  gfs2Storage:
    blockDeviceCommands:
      sharedVg: true
      rabbitCommands:
        pvCreate: $DEVICE
        pvRemove: $DEVICE
        # GFS2 requires shared VG with --shared flag
        vgCreate: --shared --addtag $JOBID $VG_NAME $DEVICE_LIST
        vgRemove: $VG_NAME
        lvCreate: --zero n --activate n --size $LV_SIZE --stripes $DEVICE_NUM --stripesize=32KiB --name $LV_NAME $VG_NAME
        lvRemove: $VG_NAME/$LV_NAME
        lvChange:
          # GFS2 uses shared activation (ys)
          activate: --activate ys $VG_NAME/$LV_NAME
          deactivate: --activate n $VG_NAME/$LV_NAME
        vgChange:
          lockStart: --lock-start $VG_NAME
          lockStop: --lock-stop $VG_NAME
      computeCommands:
        lvChange:
          activate: --activate ys $VG_NAME/$LV_NAME
          deactivate: --activate n $VG_NAME/$LV_NAME
        vgChange:
          lockStart: --lock-start $VG_NAME
          lockStop: --lock-stop $VG_NAME

    fileSystemCommands:
      rabbitCommands:
        # GFS2 mkfs requires journal count, protocol, cluster name, and lock space
        mkfs: -j2 -p $PROTOCOL -t $CLUSTER_NAME:$LOCK_SPACE $DEVICE
        mount: $DEVICE $MOUNT_PATH
      computeCommands:
        mount: $DEVICE $MOUNT_PATH

    userCommands:
      postSetup:
      - chown $USERID:$GROUPID $MOUNT_PATH

    capacityScalingFactor: "1.0"
    allocationPadding: 300MiB
```

### Raw Storage

Raw storage provides direct block device access without a file system layer.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha9
kind: NnfStorageProfile
metadata:
  name: raw-example
  namespace: nnf-system
data:
  default: false
  rawStorage:
    blockDeviceCommands:
      sharedVg: true
      rabbitCommands:
        pvCreate: $DEVICE
        pvRemove: $DEVICE
        vgCreate: --addtag $JOBID $VG_NAME $DEVICE_LIST
        vgRemove: $VG_NAME
        lvCreate: --zero n --activate n --size $LV_SIZE --stripes $DEVICE_NUM --stripesize=32KiB --name $LV_NAME $VG_NAME
        lvRemove: $VG_NAME/$LV_NAME
        lvChange:
          activate: --activate y $VG_NAME/$LV_NAME
          deactivate: --activate n $VG_NAME/$LV_NAME
      computeCommands:
        lvChange:
          activate: --activate y $VG_NAME/$LV_NAME
          deactivate: --activate n $VG_NAME/$LV_NAME

    fileSystemCommands:
      rabbitCommands:
        # Raw uses bind mount to expose the block device
        mount: -o bind $DEVICE $MOUNT_PATH
      computeCommands:
        mount: -o bind $DEVICE $MOUNT_PATH

    capacityScalingFactor: "1.0"
    allocationPadding: 300MiB
```

### Lustre Storage

Lustre is a high-performance parallel distributed file system designed for large-scale cluster computing.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha9
kind: NnfStorageProfile
metadata:
  name: lustre-example
  namespace: nnf-system
data:
  default: false
  lustreStorage:
    # Whether to combine MGT and MDT on the same target
    combinedMgtMdt: true
    
    # Capacity for MGT device
    capacityMgt: 5GiB
    
    # Capacity for MDT device (also used for combined MGT+MDT)
    capacityMdt: 5GiB
    
    # MDT should not share a Rabbit with other targets
    exclusiveMdt: false
    
    # Scaling factor for OST capacity
    capacityScalingFactor: "1.0"

    # MGT target commands
    mgtCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --mgs --backfstype=$BACKFS --mkfsoptions="nnf:jobid=$JOBID" $ZVOL_NAME
      mountTarget: $ZVOL_NAME $MOUNT_PATH

    # MDT target commands  
    mdtCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --mdt --backfstype=$BACKFS --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX --mkfsoptions="nnf:jobid=$JOBID" $ZVOL_NAME
      mountTarget: $ZVOL_NAME $MOUNT_PATH
      postActivate:
      - mountpoint $MOUNT_PATH

    # Combined MGT+MDT target commands
    mgtMdtCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --mgs --mdt --backfstype=$BACKFS --fsname=$FS_NAME --index=$INDEX --mkfsoptions="nnf:jobid=$JOBID" $ZVOL_NAME
      mountTarget: $ZVOL_NAME $MOUNT_PATH
      postActivate:
      - mountpoint $MOUNT_PATH

    # OST target commands
    ostCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --ost --backfstype=$BACKFS --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX --mkfsoptions="nnf:jobid=$JOBID" $ZVOL_NAME
      mountTarget: $ZVOL_NAME $MOUNT_PATH
      postActivate:
      - mountpoint $MOUNT_PATH

    # Client mount commands
    clientCommandLines:
      mountRabbit: $MGS_NID:/$FS_NAME $MOUNT_PATH
      mountCompute: $MGS_NID:/$FS_NAME $MOUNT_PATH
      rabbitPostSetup:
      - lfs setstripe -E 64K -L mdt -E -1 -c -1 $MOUNT_PATH

    # Target placement options (see Target Layouts section)
    mgtOptions:
      colocateComputes: false
      count: 1
    mdtOptions:
      colocateComputes: false
      count: 1
    mgtMdtOptions:
      colocateComputes: false
      count: 1
    ostOptions:
      colocateComputes: true
      scale: 5

    # Commands to run on MGT after all targets are activated
    preMountMGTCommands:
    - lctl set_param -P osc.$FS_NAME-*.max_rpcs_in_flight=64
```

## Target Layouts

Target layout options control how Lustre targets (MGT, MDT, OST) are distributed across Rabbit nodes. These settings help optimize performance based on workload characteristics.

### Layout Options

Each target type (mgtOptions, mdtOptions, mgtMdtOptions, ostOptions) supports:

| Option | Description |
|--------|-------------|
| `count` | Static number of targets to create |
| `scale` | Dynamic value (1-10) that the WLM uses to determine target count |
| `colocateComputes` | If true, targets are placed on Rabbits connected to job's compute nodes |
| `storageLabels` | List of labels to restrict which Storage resources can be used |

> **Note:** Only one of `count` or `scale` can be set for each target type.

### Understanding colocateComputes

When `colocateComputes: true`:
- Storage is restricted to Rabbit nodes with physical connections to the job's compute nodes
- This typically means Rabbits in the same chassis as the compute nodes
- Best for minimizing network hops and maximizing bandwidth

When `colocateComputes: false`:
- Storage can be placed on any available Rabbit node
- Useful for separating metadata targets from data targets
- Required for `create_persistent` directives since they may not have compute nodes

### Scale vs Count

**Scale** is useful when you want storage to automatically adjust based on job size:
- Value of 1: Minimum targets needed to satisfy capacity
- Value of 10: Maximum targets, potentially one per Rabbit connected to the job
- The WLM interprets scale values based on allocation size, compute count, and Rabbit count

**Count** is useful when you need precise control:
- Specific number of targets regardless of job size
- Consistent performance characteristics across different jobs
- Useful for single-shared-file workloads with low metadata requirements

### Example Layouts

**High-performance scaled to job size:**
```yaml
ostOptions:
  scale: 10
  colocateComputes: true
mdtOptions:
  count: 2
  colocateComputes: true
```

**Static Configuration:**
```yaml
ostOptions:
  count: 4
  colocateComputes: true
mdtOptions:
  count: 1
  colocateComputes: true
```

## RAID Configurations

Storage profiles support RAID configurations for both LVM-based file systems (XFS, Raw) and ZFS-based Lustre targets.

### LVM RAID (XFS and Raw)

LVM RAID logical volumes provide redundancy for XFS and Raw allocations.

> **Note:** GFS2 cannot use RAID logical volumes because the LV is shared between multiple nodes.

To create a RAID logical volume, specify `--type raid[x]`, `--activate y`, and `--nosync` in the `lvCreate` command:

```yaml
xfsStorage:
  blockDeviceCommands:
    rabbitCommands:
      pvCreate: $DEVICE
      pvRemove: $DEVICE
      vgCreate: --addtag $JOBID $VG_NAME $DEVICE_LIST
      vgRemove: $VG_NAME
      # RAID5 example: one parity device, remaining are data stripes
      lvCreate: |
        --activate y --zero n --nosync --type raid5 
        --size $LV_SIZE --stripes $DEVICE_NUM-1 
        --stripesize=32KiB --name $LV_NAME $VG_NAME
      lvRemove: $VG_NAME/$LV_NAME
      lvChange:
        activate: --activate y $VG_NAME/$LV_NAME
        deactivate: --activate n $VG_NAME/$LV_NAME
      # Commands for rebuilding after drive replacement
      lvmRebuild:
        vgExtend: $VG_NAME $DEVICE
        vgReduce: --removemissing $VG_NAME
        lvRepair: $VG_NAME/$LV_NAME
```

> **Note:** The `--nosync` option allows the RAID volume to be used immediately without waiting for initial synchronization.

### ZFS RAID (Lustre)

ZFS RAID provides redundancy for Lustre targets using zpool virtual devices.

```yaml
lustreStorage:
  ostCommandlines:
    # RAIDZ example (single parity, similar to RAID5)
    zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME raidz $DEVICE_LIST
    mkfs: --ost --backfstype=$BACKFS --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $ZVOL_NAME
    mountTarget: $ZVOL_NAME $MOUNT_PATH
    # Command for replacing a failed device
    zpoolReplace: $POOL_NAME $OLD_DEVICE $NEW_DEVICE
```

## User Commands

Storage profiles support custom commands that run at various points during the storage lifecycle. These allow administrators to customize behavior beyond the standard provisioning steps.

There are two categories of user commands with different execution contexts:

1. **Block Device and File System Commands** - For compute nodes, these run during the PreRun and PostRun phases. For Rabbit nodes, these Run during PreRun, PostRun, DataIn, and DataOut phases depending on which other DW directives are specified (data movement and user containers).
2. **Storage-Level Commands** - Run during storage setup and teardown phases

### Block Device and File System User Commands

The user commands in `blockDeviceCommands` and `fileSystemCommands` are run when storage is being activated/deactivated and mounted/unmounted for use:

| Location | Workflow Phase | Description |
|----------|----------------|-------------|
| Rabbit | DataIn | Storage is activated and mounted for data staging into the allocation |
| Rabbit | DataOut | Storage is activated and mounted for data staging out of the allocation |
| Rabbit | PreRun | Storage is activated and mounted for access in a user container |
| Rabbit | PostRun | Storage is unmounted and deactivated after the user container exits |
| Compute | PreRun | Storage is activated and mounted before the user's application runs |
| Compute | PostRun | Storage is unmounted and deactivated after the user's application completes |

These commands are useful for operations that need to happen each time storage is accessed, such as:
- Setting up environment-specific configurations
- Running health checks before/after use
- Synchronizing data or caches

#### Block Device User Commands

```yaml
xfsStorage:
  blockDeviceCommands:
    # Commands run on Rabbit during PreRun/PostRun/DataIn/DataOut phases
    rabbitCommands:
      userCommands:
        preActivate:
        - echo "Rabbit: About to activate block device"
        postActivate:
        - echo "Rabbit: Block device activated"
        preDeactivate:
        - echo "Rabbit: About to deactivate block device"
        postDeactivate:
        - echo "Rabbit: Block device deactivated"
    # Commands run on Compute during PreRun/PostRun phases
    computeCommands:
      userCommands:
        preActivate:
        - echo "Compute: About to activate block device"
        postActivate:
        - echo "Compute: Block device activated"
        preDeactivate:
        - echo "Compute: About to deactivate block device"
        postDeactivate:
        - echo "Compute: Block device deactivated"
```

#### File System User Commands

```yaml
xfsStorage:
  fileSystemCommands:
    # Commands run on Rabbit during DataIn/DataOut phases
    rabbitCommands:
      userCommands:
        preMount:
        - echo "Rabbit: About to mount file system"
        postMount:
        - echo "Rabbit: File system mounted"
        preUnmount:
        - echo "Rabbit: About to unmount file system"
        postUnmount:
        - echo "Rabbit: File system unmounted"
    # Commands run on Compute during PreRun/PostRun phases
    computeCommands:
      userCommands:
        preMount:
        - echo "Compute: About to mount file system"
        postMount:
        - echo "Compute: File system mounted"
        preUnmount:
        - echo "Compute: About to unmount file system"
        postUnmount:
        - echo "Compute: File system unmounted"
```

### Storage-Level User Commands

The `userCommands` section at the storage level (e.g., `xfsStorage.userCommands`) contains commands that run during the **setup and teardown phases** of the workflow. These run on the Rabbit nodes when storage is first provisioned and when it is finally destroyed.

| Command | Phase | Description |
|---------|-------|-------------|
| `postSetup` | Setup | Runs after storage is fully provisioned and the file system is mounted on the Rabbit |
| `preTeardown` | Teardown | Runs before storage is destroyed, while the file system is still mounted |
| `postActivate` | Setup | Runs after the file system is activated during initial setup |
| `preDeactivate` | Teardown | Runs before the file system is deactivated during final teardown |

These commands are useful for one-time operations such as:
- Setting ownership and permissions on newly created storage
- Initializing directory structures
- Cleaning up or archiving data before destruction

```yaml
xfsStorage:
  userCommands:
    # Run once after storage is fully set up (file system mounted on Rabbit)
    postSetup:
    - chown $USERID:$GROUPID $MOUNT_PATH
    - chmod 750 $MOUNT_PATH
    - mkdir -p $MOUNT_PATH/input $MOUNT_PATH/output
    
    # Run once before storage is torn down (file system still mounted)
    preTeardown:
    - echo "Final cleanup of $MOUNT_PATH"
    
    # Run once after file system is activated during setup
    postActivate:
    - echo "File system activated for first time"
    
    # Run once before file system is deactivated during teardown
    preDeactivate:
    - echo "About to deactivate file system for last time"
```

### Lustre-Specific User Commands

User commands can also be specified for Lustre file systems, however there are no block device activate/deactivate hooks.

```yaml
lustreStorage:
  # Commands for each target type
  mgtCommandlines:
    postActivate:
    - mountpoint $MOUNT_PATH
    preDeactivate:
    - echo "Deactivating MGT"
  
  mdtCommandlines:
    postActivate:
    - mountpoint $MOUNT_PATH
  
  ostCommandlines:
    postActivate:
    - mountpoint $MOUNT_PATH

  # Client-side commands
  clientCommandLines:
    rabbitPreMount:
    - echo "About to mount Lustre client on Rabbit"
    rabbitPostMount:
    - lfs setstripe -c -1 $MOUNT_PATH
    rabbitPreUnmount:
    - sync
    rabbitPostUnmount:
    - echo "Lustre client unmounted"
    
    computePreMount:
    - echo "About to mount Lustre client on Compute"
    computePostMount:
    - echo "Lustre client mounted"
    computePreUnmount:
    - sync
    computePostUnmount:
    - echo "Lustre client unmounted"

    # Setup/teardown with Lustre client mounted on Rabbit
    rabbitPostSetup:
    - lfs setstripe -E 64K -L mdt -E -1 -c -1 $MOUNT_PATH
    rabbitPreTeardown:
    - lfs getstripe $MOUNT_PATH

  # Commands run on MGT after all targets are up
  preMountMGTCommands:
  - lctl set_param -P osc.$FS_NAME-*.max_rpcs_in_flight=64
  - lctl set_param -P osc.$FS_NAME-*.max_dirty_mb=2000
```

## Command Line Variables

Storage profile commands can use variables that are expanded at runtime. Variables use the `$VARIABLE_NAME` syntax.

### Global Variables

Available in all commands:

| Variable | Description |
|----------|-------------|
| `$JOBID` | Job ID from the Workflow |
| `$USERID` | User ID of the job submitter |
| `$GROUPID` | Group ID of the job submitter |

### LVM Variables

#### Physical Volume Commands

| Variable | Description |
|----------|-------------|
| `$DEVICE` | Path to allocated device (e.g., `/dev/nvme0n1`) |

#### Volume Group Commands

| Variable | Description |
|----------|-------------|
| `$VG_NAME` | Volume group name (controlled by Rabbit software) |
| `$DEVICE_LIST` | Space-separated list of devices |
| `$DEVICE_NUM` | Count of devices |
| `$DEVICE_NUM-1` | Device count minus 1 (for RAID5) |
| `$DEVICE_NUM-2` | Device count minus 2 (for RAID6) |
| `$DEVICE` | New device path (used in vgExtend for RAID rebuild) |

#### Logical Volume Commands

| Variable | Description |
|----------|-------------|
| `$VG_NAME` | Volume group name |
| `$LV_NAME` | Logical volume name |
| `$DEVICE_NUM` | Count of devices |
| `$DEVICE_NUM-1` | Device count minus 1 |
| `$DEVICE_NUM-2` | Device count minus 2 |
| `$DEVICE1`, `$DEVICE2`, ..., `$DEVICEn` | Individual devices from `$DEVICE_LIST` |
| `$PERCENT_VG` | Size as percentage of VG |
| `$LV_SIZE` | Size in kB format for lvcreate |

### File System Variables

#### XFS/Raw mkfs

| Variable | Description |
|----------|-------------|
| `$DEVICE` | Path to the logical volume device |

#### GFS2 mkfs

| Variable | Description |
|----------|-------------|
| `$DEVICE` | Path to the logical volume device |
| `$CLUSTER_NAME` | Cluster name (controlled by Rabbit software) |
| `$LOCK_SPACE` | Lock space key (controlled by Rabbit software) |
| `$PROTOCOL` | Locking protocol (controlled by Rabbit software) |

#### Mount/Unmount

| Variable | Description |
|----------|-------------|
| `$DEVICE` | Device path to mount |
| `$MOUNT_PATH` | Path to mount on |

### ZFS/Lustre Variables

#### zpool create

| Variable | Description |
|----------|-------------|
| `$POOL_NAME` | Pool name (controlled by Rabbit software) |
| `$DEVICE_LIST` | Space-separated list of devices |
| `$DEVICE_NUM` | Count of devices |
| `$DEVICE1`, `$DEVICE2`, ..., `$DEVICEn` | Individual devices |

#### zpool replace

| Variable | Description |
|----------|-------------|
| `$POOL_NAME` | Pool name |
| `$DEVICE_LIST` | List of devices |
| `$DEVICE_NUM`, `$DEVICE_NUM-1`, `$DEVICE_NUM-2` | Device counts |
| `$OLD_DEVICE` | Degraded device to replace |
| `$NEW_DEVICE` | Replacement device |

#### Lustre mkfs

| Variable | Description |
|----------|-------------|
| `$FS_NAME` | Lustre fsname picked by NNF software |
| `$MGS_NID` | NID of the MGS |
| `$ZVOL_NAME` | ZFS volume name (`pool/dataset`) |
| `$INDEX` | Target index number |
| `$TARGET_NAME` | Target name (e.g., `mylus-OST0003`) |
| `$BACKFS` | Backing file system type |

#### Lustre Client

| Variable | Description |
|----------|-------------|
| `$MGS_NID` | NID of the MGS |
| `$FS_NAME` | File system name |
| `$MOUNT_PATH` | Client mount path |
| `$NUM_MDTS` | Number of MDTs |
| `$NUM_MGTS` | Number of MGTs |
| `$NUM_MGTMDTS` | Number of combined MGT/MDTs |
| `$NUM_OSTS` | Number of OSTs |
| `$NUM_NNFNODES` | Number of NNF nodes |

### NnfSystemStorage Variables

For system storage allocations:

| Variable | Description |
|----------|-------------|
| `$COMPUTE_HOSTNAME` | Hostname of the compute node using the allocation |

### User Command Variables

Different variables are available depending on which user command hook is being executed.

#### Block Device User Commands

The following variables are available to `blockDeviceCommands.rabbitCommands.userCommands` and `blockDeviceCommands.computeCommands.userCommands` (preActivate, postActivate, preDeactivate, postDeactivate):

| Variable | Description |
|----------|-------------|
| `$JOBID` | Job ID from the Workflow |
| `$USERID` | User ID of the job submitter |
| `$GROUPID` | Group ID of the job submitter |
| `$VG_NAME` | Volume group name |
| `$LV_NAME` | Logical volume name |

#### File System User Commands

The following variables are available to `fileSystemCommands.rabbitCommands.userCommands` and `fileSystemCommands.computeCommands.userCommands` (preMount, postMount, preUnmount, postUnmount):

| Variable | Description |
|----------|-------------|
| `$JOBID` | Job ID from the Workflow |
| `$USERID` | User ID of the job submitter |
| `$GROUPID` | Group ID of the job submitter |
| `$DEVICE` | Device path being mounted |
| `$MOUNT_PATH` | Path where the file system is mounted |

#### Storage-Level User Commands

The following variables are available to `userCommands` at the storage level (postSetup, preTeardown, postActivate, preDeactivate):

| Variable | Description |
|----------|-------------|
| `$JOBID` | Job ID from the Workflow |
| `$USERID` | User ID of the job submitter |
| `$GROUPID` | Group ID of the job submitter |
| `$MOUNT_PATH` | Path where the file system is mounted |

#### Lustre Target User Commands

The following variables are available to Lustre target commands (mgtCommandlines, mdtCommandlines, mgtMdtCommandlines, ostCommandlines) for postActivate and preDeactivate:

| Variable | Description |
|----------|-------------|
| `$JOBID` | Job ID from the Workflow |
| `$MOUNT_PATH` | Path where the target is mounted |
| `$FS_NAME` | Lustre file system name |
| `$TARGET_NAME` | Target name (e.g., `mylus-OST0003`) |

#### Lustre Client User Commands

The following variables are available to `clientCommandLines` user commands:

**For rabbitPreMount, rabbitPostMount, rabbitPreUnmount, rabbitPostUnmount, computePreMount, computePostMount, computePreUnmount, computePostUnmount:**

| Variable | Description |
|----------|-------------|
| `$JOBID` | Job ID from the Workflow |
| `$USERID` | User ID of the job submitter |
| `$GROUPID` | Group ID of the job submitter |
| `$MGS_NID` | NID of the MGS |
| `$FS_NAME` | Lustre file system name |
| `$MOUNT_PATH` | Path where the client is mounted |

**For rabbitPostSetup and rabbitPreTeardown:**

| Variable | Description |
|----------|-------------|
| `$JOBID` | Job ID from the Workflow |
| `$USERID` | User ID of the job submitter |
| `$GROUPID` | Group ID of the job submitter |
| `$MGS_NID` | NID of the MGS |
| `$FS_NAME` | Lustre file system name |
| `$MOUNT_PATH` | Path where the client is mounted |
| `$NUM_MDTS` | Number of MDTs |
| `$NUM_MGTS` | Number of MGTs |
| `$NUM_MGTMDTS` | Number of combined MGT/MDTs |
| `$NUM_OSTS` | Number of OSTs |
| `$NUM_NNFNODES` | Number of NNF nodes |

#### Lustre preMountMGTCommands

The following variables are available to `preMountMGTCommands`:

| Variable | Description |
|----------|-------------|
| `$JOBID` | Job ID from the Workflow |
| `$FS_NAME` | Lustre file system name |

## Advanced Configuration

### External MGS

To use an existing external MGS instead of creating one:

```yaml
lustreStorage:
  # Use existing MGS by NID
  externalMgs: "10.0.0.1@tcp"
  
  # Or reference an MGS pool created with standaloneMgtPoolName
  externalMgs: "pool:my-mgs-pool"
```

### ZFS Dataset Properties

Set ZFS properties via `--mkfsoptions`:

```yaml
lustreStorage:
  ostCommandlines:
    mkfs: --ost --mkfsoptions="recordsize=1024K -o compression=lz4" --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $ZVOL_NAME
```

### Persistent Lustre Mount Options

Use `--mountfsoptions` in mkfs for persistent mount options:

```yaml
lustreStorage:
  ostCommandlines:
    mkfs: --ost --mountfsoptions="errors=remount-ro,mballoc" --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $ZVOL_NAME
```

### Capacity Scaling and Padding

```yaml
xfsStorage:
  # Request 10% more capacity than specified by user
  capacityScalingFactor: "1.1"
  
  # Add fixed padding for LVM/filesystem overhead
  allocationPadding: 500MiB
```

### Storage Labels

Restrict allocations to specific storage resources:

```yaml
lustreStorage:
  ostOptions:
    storageLabels:
    - high-performance
    - nvme-only
```

## Pinned Profiles

When a workflow references a storage profile, the NNF software creates a "pinned" copy of the profile. This ensures that:

- Profile changes don't affect running workflows
- The exact configuration is preserved for the workflow's lifetime
- Profiles marked as `pinned: true` cannot also be `default: true`

Do not manually set `pinned: true` on profiles you create.