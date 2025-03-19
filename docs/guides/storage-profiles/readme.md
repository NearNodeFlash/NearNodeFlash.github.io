---
authors: Nate Thornton <nate.thornton@hpe.com>, Dean Roehrich <dean.roehrich@hpe.com>
categories: provisioning
---

# Storage Profile Overview

Storage Profiles allow for customization of the Rabbit storage provisioning process. Examples of content that can be customized via storage profiles is

1. The RAID type used for storage
2. Any mkfs or LVM args used
3. An external MGS NID for Lustre
4. A boolean value indicating the Lustre MGT and MDT should be combined on the same target device 

DW directives that allocate storage on Rabbit nodes allow a `profile` parameter to be specified to control how the storage is configured. NNF software provides a set of canned profiles to choose from, and the administrator may create more profiles.

The administrator shall choose one profile to be the default profile that is used when a profile parameter is not specified.

## Specifying a Profile

To specify a profile name on a #DW directive, use the `profile` option

```shell
#DW jobdw type=lustre profile=durable capacity=5GB name=example
```

## Setting A Default Profile

A default profile must be defined at all times. Any #DW line that does not specify a profile will use the default profile. If a default profile is not defined, then any new workflows will be rejected. If more than one profile is marked as default then any new workflows will be rejected.

To query existing profiles

```shell
$ kubectl get nnfstorageprofiles -A
NAMESPACE    NAME          DEFAULT   AGE
nnf-system   durable       true      14s
nnf-system   performance   false     6s
```

To set the default flag on a profile

```shell
kubectl patch nnfstorageprofile performance -n nnf-system --type merge -p '{"data":{"default":true}}'
```

To clear the default flag on a profile

```shell
kubectl patch nnfstorageprofile durable -n nnf-system --type merge -p '{"data":{"default":false}}'
```

## Creating The Initial Default Profile

Create the initial default profile from scratch or by using the [NnfStorageProfile/template](https://github.com/NearNodeFlash/nnf-sos/blob/master/config/examples/nnf_v1alpha1_nnfstorageprofile.yaml) resource as a template. If `nnf-deploy` was used to install nnf-sos then the default profile described below will have been created automatically.

To use the `template` resource begin by obtaining a copy of it either from the nnf-sos repo or from a live system. To get it from a live system use the following command:

```shell
kubectl get nnfstorageprofile -n nnf-system template -o yaml > profile.yaml
```

Edit the `profile.yaml` file to trim the metadata section to contain only a name and namespace. The namespace must be left as nnf-system, but the name should be set to signify that this is the new default profile. In this example we will name it `default`.  The metadata section will look like the following, and will contain no other fields:

```yaml
metadata:
  name: default
  namespace: nnf-system
```

Mark this new profile as the default profile by setting `default: true` in the data section of the resource:

```yaml
data:
  default: true
```

Apply this resource to the system and verify that it is the only one marked as the default resource:

```shell
kubectl get nnfstorageprofile -A
```

The output will appear similar to the following:

```shell
NAMESPACE    NAME       DEFAULT   AGE
nnf-system   default    true      9s
nnf-system   template   false     11s
```

The administrator should edit the `default` profile to record any cluster-specific settings.
Maintain a copy of this resource YAML in a safe place so it isn't lost across upgrades.

### Keeping The Default Profile Updated

An upgrade of nnf-sos may include updates to the `template` profile. It may be necessary to manually copy these updates into the `default` profile.

## Profile Parameters

### XFS

The following shows how to specify command line options for pvcreate, vgcreate, lvcreate, and mkfs for XFS storage. Optional mount options are specified one per line

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: xfs-stripe-example
  namespace: nnf-system
data:
[...]
  xfsStorage:
    commandlines:
      pvCreate: $DEVICE
      vgCreate: $VG_NAME $DEVICE_LIST
      lvCreate: -l 100%VG --stripes $DEVICE_NUM --stripesize=32KiB --name $LV_NAME $VG_NAME
      mkfs: $DEVICE
    options:
      mountRabbit:
      - noatime
      - nodiratime
[...]
```

### GFS2

The following shows how to specify command line options for pvcreate, lvcreate, and mkfs for GFS2.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: gfs2-stripe-example
  namespace: nnf-system
data:
[...]
  gfs2Storage:
    commandlines:
      pvCreate: $DEVICE
      vgCreate: $VG_NAME $DEVICE_LIST
      lvCreate: -l 100%VG --stripes $DEVICE_NUM --stripesize=32KiB --name $LV_NAME $VG_NAME
      mkfs: -j2 -p $PROTOCOL -t $CLUSTER_NAME:$LOCK_SPACE $DEVICE
[...]
```

### Lustre / ZFS

The following shows how to specify a zpool virtual device (vdev). In this case the default vdev is a stripe. See [zpoolconcepts(7)](https://openzfs.github.io/openzfs-docs/man/7/zpoolconcepts.7.html) for virtual device descriptions.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: zpool-stripe-example
  namespace: nnf-system
data:
[...]
  lustreStorage:
    mgtCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --mgs $VOL_NAME
    mdtCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --mdt --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $VOL_NAME
    mgtMdtCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --mgs --mdt --fsname=$FS_NAME --index=$INDEX $VOL_NAME
    ostCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --ost --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $VOL_NAME
[...]
```

#### ZFS dataset properties

The following shows how to specify ZFS dataset properties in the `--mkfsoptions` arg for mkfs.lustre. See [zfsprops(7)](https://openzfs.github.io/openzfs-docs/man/7/zfsprops.7.html).

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: zpool-stripe-example
  namespace: nnf-system
data:
[...]
  lustreStorage:
[...]
    ostCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --ost --mkfsoptions="recordsize=1024K -o compression=lz4" --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $VOL_NAME
[...]
```

#### Mount Options for Targets

##### Persistent Mount Options

Use the mkfs.lustre `--mountfsoptions` parameter to set persistent mount options for Lustre targets.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: target-mount-option-example
  namespace: nnf-system
data:
[...]
  lustreStorage:
[...]
    ostCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --ost --mountfsoptions="errors=remount-ro,mballoc" --mkfsoptions="recordsize=1024K -o compression=lz4" --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $VOL_NAME
[...]
```

##### Non-Persistent Mount Options

Non-persistent mount options can be specified with the ostOptions.mountTarget parameter to the NnfStorageProfile:

```yaml

apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: target-mount-option-example
  namespace: nnf-system
data:
[...]
  lustreStorage:
[...]
    ostCommandlines:
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
      mkfs: --ost --mountfsoptions="errors=remount-ro" --mkfsoptions="recordsize=1024K -o compression=lz4" --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $VOL_NAME
    ostOptions:
      mountTarget:
      - mballoc
[...]
```

#### Target Layout

Users may want Lustre file systems with different performance characteristics. For example, a user job with a single compute node accessing the Lustre file system would see acceptable performance from a single OSS. An FPP workload might want as many OSSs as posible to avoid contention.

The `NnfStorageProfile` allows admins to specify where and how many Lustre targets are allocated by the WLM. During the proposal phase of the workflow, the NNF software uses the information in the `NnfStorageProfile` to add extra constraints in the `DirectiveBreakdown`. The WLM uses these constraints when picking storage.

The `NnfStorageProfile` has three fields in the `mgtOptions`, `mdtOptions`, and `ostOptions` to specify target layout. The fields are:

- `count` - A static value for how many Lustre targets to create.
- `scale` - A value from 1-10 that the WLM can use to determine how many Lustre targets to allocate. This is up to the WLM and the admins to agree on how to interpret this field. A value of 1 might indicate the minimum number of NNF nodes needed to reach the minimum capacity, while 10 might result in a Lustre target on every Rabbit attached to the computes in the job. Scale takes into account allocation size, compute node count, and Rabbit count.
- `colocateComputes` - true/false value. When "true", this adds a location constraint in the `DirectiveBreakdown` that limits the WLM to picking storage with a physical connection to the compute resources. In practice this means that Rabbit storage is restricted to the chassis used by the job. This can be set individually for each of the Lustre target types. When this is "false", any Rabbit storage can be picked, even if the Rabbit doesn't share a chassis with any of the compute nodes in the job.

Only one of `scale` and `count` can be set for a particular target type.

The `DirectiveBreakdown` for `create_persistent` #DWs won't include the constraint from `colocateCompute=true` since there may not be any compute nodes associated with the job.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: high-metadata
  namespace: default
data:
  default: false
...
  lustreStorage:
    combinedMgtMdt: false
    capacityMdt: 500GiB
    capacityMgt: 1GiB
[...]
    ostOptions:
      scale: 5
      colocateComputes: true
    mdtOptions:
      count: 10
```

##### Example Layouts

`scale` with `colocateComputes=true` will likely be the most common layout type to use for `jobdw` directives. This will result in a Lustre file system whose performance scales with the number of compute nodes in the job.

`count` may be used when a specific performance characteristic is desired such as a single shared file workload that has low metadata requirements and only needs a single MDT. It may also be useful when a consistently performing file system is required across different jobs.

`colocatedComputes=false` may be useful for placing MDTs on NNF nodes without an OST (within the same file system).

The `count` field may be useful when creating a persistent file system since the job with the `create_persistent` directive may only have a single compute node.

In general, `scale` gives a simple way for users to get a filesystem that has performance consistent with their job size. `count` is useful for times when a user wants full control of the file system layout.

## Command Line Variables

### global
- `$JOBID` - expands to the Job ID from the Workflow
- `$USERID` - expands to the User ID of the user who submitted the job
- `$GROUPID` - expands to the Group ID of the user who submitted the job

### LVM PV commands

- `$DEVICE` - expands to the `/dev/<path>` value for one device that has been allocated

### LVM VG commands

- `$VG_NAME` - expands to a volume group name that is controlled by Rabbit software.
- `$DEVICE_LIST` - expands to a list of space-separated `/dev/<path>` devices. This list will contain the devices that were iterated over for the pvcreate step.
- `$DEVICE_NUM` - expands to the count of devices in `$DEVICE_LIST`

### LVM LV Commands

- `$VG_NAME` - see vgcreate above.
- `$LV_NAME` - expands to a logical volume name that is controlled by Rabbit software.
- `$DEVICE_NUM` - expands to a number indicating the number of devices allocated for the volume group.
- `$DEVICE1, $DEVICE2, ..., $DEVICEn` - each expands to one of the devices from the `$DEVICE_LIST` above.
- `$PERCENT_VG` - expands to the size that each LV should be based on a percentage of the total VG size
- `$LV_SIZE` - expands to the size of the LV in kB in the format expected by `lvcreate`

### XFS mkfs

- `$DEVICE` - expands to the `/dev/<path>` value for the logical volume that was created by the lvcreate step above.

### GFS2 mkfs

- `$DEVICE` - expands to the `/dev/<path>` value for the logical volume that was created by the lvcreate step above.
- `$CLUSTER_NAME` - expands to a cluster name that is controlled by Rabbit Software
- `$LOCK_SPACE` - expands to a lock space key that is controlled by Rabbit Software.
- `$PROTOCOL` - expands to a locking protocol that is controlled by Rabbit Software.

### zpool create

- `$DEVICE_LIST` - expands to a list of space-separated `/dev/<path>` devices. This list will contain the devices that were allocated for this storage request.
- `$POOL_NAME` - expands to a pool name that is controlled by Rabbit software.
- `$DEVICE_NUM` - expands to a number indicating the number of devices allocated for this storage request.
- `$DEVICE1, $DEVICE2, ..., $DEVICEn` - each expands to one of the devices from the `$DEVICE_LIST` above.

### lustre mkfs

- `$FS_NAME` - expands to the filesystem name that was passed to Rabbit software from the workflow's #DW line.
- `$MGS_NID` - expands to the NID of the MGS. If the MGS was orchestrated by nnf-sos then an appropriate internal value will be used.
- `$ZVOL_NAME` - expands to the volume name that will be created. This value will be `<pool_name>/<dataset>`, and is controlled by Rabbit software.
- `$INDEX` - expands to the index value of the target and is controlled by Rabbit software.
- `$TARGET_NAME` - expands to the name of the lustre target of the form `[fsname]-[target-type][index]` (e.g., `mylus-OST0003`)
- `$BACKFS` - expands to the type of file system backing the Lustre target

### Mount/Unmount

- `$DEVICE` - expands to the device path to mount
- `$MOUNT_PATH` - expands to the path to mount on

### PostMount/PreUnmount and PostActivate/PreDeactivate

- `$MOUNT_PATH` - expands to the mount path of the fileystem to perform certain actions on the mounted filesystem

#### Lustre Specific

These variables are for lustre only and can be used to perform PostMount activities such are setting lustre striping.

- `$NUM_MDTS` - expands to the number of MDTs for the lustre filesystem
- `$NUM_MGTS` - expands to the number of MGTs for the lustre filesystem
- `$NUM_MGTMDTS` - expands to the number of combined MGTMDTs for the lustre filesystem
- `$NUM_OSTS` - expands to the number of OSTs for the lustre filesystem
- `$NUM_NNFNODES` - expands to the number of NNF Nodes for the lustre filesystem

### NnfSystemStorage specific

- `$COMPUTE_HOSTNAME` - Expands to the hostname of the compute node that will use the allocation. This can be used to add a tag during the lvcreate
```
lvCreate --zero n --activate n --extents $PERCENT_VG --addtag $COMPUTE_HOSTNAME ...
```