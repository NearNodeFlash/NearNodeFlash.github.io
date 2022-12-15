---
authors: Matt Richerson <matthew.richerson@hpe.com>
state: discussion
---
Storage Profiles for Lustre Layout
=============================================

Layout of the Lustre targets can have a large effect on file system performance. Currently, the only parameters exposed for tuning a Lustre file system are for the individual target. This RFC proposes adding fields to the NnfStorageProfile to influence where and how many Lustre targets are allocated.

Proposal
--------

Users may want Lustre file systems with different performance characteristics. For example, a user job with a single compute node accessing the Lustre file system would see acceptable performance from a single OSS. A FPP workload might want as many OSSs as posible to avoid contention. Currently, the WLM does not have enough information in the DirectiveBreakdown to differentiate these two cases.

The NnfStorageProfile will be modified to allow admins to specify where and how many Lustre targets are allocated by the WLM. An end user then chooses an appropriate storage profile for their workload and includes it on the #DW line. During the proposal phase of the workflow, the Rabbit software will use the information in the NnfStorageProfile to add extra constraints to the allocations in the DirectiveBreakdown. The WLM uses these constraints when picking storage.

The NnfStorageProfile is changed to allow three new fields in the mgtOptions, mdtOptions, and ostOptions. The new fields are:

- count - A static value for how many Lustre targets to use.
- scale - A value from 1-10 that the WLM can use to determine how many Lustre targets to allocate. This is up to the WLM and the admins to agree on how to interpret this field. I imagine a combination of compute node count and allocation size would be used. Using scale=10 as an example, a single compute node job allocating 10TiB might only get 1 OSS. In contrast, a 5000 compute node job allocating 10 TiB might get 20 OSSs. A 5000 compute node job allocating 100TiB might get 100 OSSs.
- limit - Limit which storage can be picked. Currently the only values are "None" and "computePhysical". "computePhysical" adds a location constraint in the DirectiveBreakdown that limits the WLM to picking storage with a physical connection to storage. In practice this means that only Rabbit storage in the same chassis as the compute nodes a job is using can be picked. This can be set individually for each of the Lustre target types. When limit is "none", any Rabbit storage can be picked, even if the Rabbit doesn't share a chassis with any of the compute nodes in the job.

Only one of "scale" and "count" can be set for a particular target type.

The DirectiveBreakdown for "create_persistent" #DWs won't include the constraint from "limit=computePhysical" since there may not be any compute nodes associated with the job.

Example
-------

Below is an example of an NnfStorageProfile (showing only the Lustre section) using the new options. The "capacity" and "exclusive" fields are moved under the "*Options" field to put all target options in the same spot.

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
    mdtCommandlines:
      mkfs: --mdt --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $VOL_NAME
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
    mgtCommandlines:
      mkfs: --mgs $VOL_NAME
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
    mgtMdtCommandlines:
      mkfs: --mgs --mdt --fsname=$FS_NAME --index=$INDEX $VOL_NAME
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
    ostCommandlines:
      mkfs: --ost --fsname=$FS_NAME --mgsnode=$MGS_NID --index=$INDEX $VOL_NAME
      zpoolCreate: -O canmount=off -o cachefile=none $POOL_NAME $DEVICE_LIST
    mgtMdtOptions: {}
    ostOptions:
      scale: 5
      limit: computePhysical
      exclusive: false
    mdtOptions:
      capacity: 500GiB
      count: 10
      exclusive: false
    mgtOptions:
      capacity: 1GiB
      exclusive: false
```

A user job using the above NnfStorageProfile will have the following DirectiveBreakdown created for the WLM to use when making allocations. The information provided in the NnfStorageProfile above shows up as constraints in each of the allocation sets. The "limit=computePhysical" option for the OSTs shows up as a location constraint referencing the Computes resource and having type=physical. This means that the storage the WLM picks must have a physical connection to the compute nodes used in the Computes resource. This locality information can be found in the Storages resources (part of the inventory).

```yaml
apiVersion: dws.cray.hpe.com/v1alpha1
kind: DirectiveBreakdown
metadata:
  name: example-0
  namespace: default
spec:
  directive: '#DW jobdw type=lustre capacity=50GB profile=high-metadata name=science'
  userID: 1001
status:
  compute:
    constraints:
      location:
      - reference:
          kind: Servers
          name: example-0
          namespace: default
        type: network
  ready: true
  storage:
    allocationSets:
    - allocationStrategy: AllocateAcrossServers
      constraints:
        scale: 5
        labels:
        - dws.cray.hpe.com/storage=Rabbit
        location:
        - reference:
            kind: Computes
            name: example
            namespace: default
          type: physical
      label: ost
      minimumCapacity: 50000000000
    - allocationStrategy: AllocateAcrossServers
      constraints:
        count: 10
        labels:
        - dws.cray.hpe.com/storage=Rabbit
      label: mdt
      minimumCapacity: 536870912000
    - allocationStrategy: AllocateSingleServer
      constraints:
        colocation:
        - key: lustre-mgt
          type: exclusive
        labels:
        - dws.cray.hpe.com/storage=Rabbit
      label: mgt
      minimumCapacity: 1073741824
    lifetime: job
    reference:
      kind: Servers
      name: example-0
      namespace: default
```
