---
authors: Matt Richerson <matthew.richerson@hpe.com>
categories: provisioning
---

# Lustre External MGT

## Background

Lustre has a limitation where only a single MGT can be mounted on a node at a time. In some situations it may be desirable to share an MGT between multiple Lustre file systems to increase the number of Lustre file systems that can be created and to decrease scheduling complexity. This guide provides instructions on how to configure NNF to share MGTs. There are three methods that can be used:

1. Use a Lustre MGT from outside the NNF cluster
2. Create a persistent Lustre file system through DWS and use the MGT it provides
3. Create a pool of standalone persistent Lustre MGTs, and have the NNF software select one of them

These three methods are not mutually exclusive on the system as a whole. Individual file systems can use any of options 1-3 or create their own MGT.

## Configuration with an External MGT

### Storage Profile
An existing MGT external to the NNF cluster can be used to manage the Lustre file systems on the NNF nodes. An advantage to this configuration is that the MGT can be highly available through multiple MGSs. A disadvantage is that there is only a single MGT. An MGT shared between more than a handful of Lustre file systems is not a common use case, so the Lustre code may prove less stable.

The following yaml provides an example of what the `NnfStorageProfile` should contain to use an MGT on an external server.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: external-mgt
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: 1.2.3.4@eth0:1.2.3.5@eth0
    combinedMgtMdt: false
    standaloneMgtPoolName: ""
[...]
```

### NnfLustreMGT

A `NnfLustreMGT` resource tracks which fsnames have been used on the MGT to prevent fsname re-use. Any Lustre file systems that are created through the NNF software will request an fsname to use from a `NnfLustreMGT` resource. Every MGT must have a corresponding `NnfLustreMGT` resource. For MGTs that are hosted on NNF hardware, the `NnfLustreMGT` resources are created automatically. The NNF software also erases any unused fsnames from the MGT disk for any internally hosted MGTs.

For a MGT hosted on an external node, an admin must create an `NnfLustreMGT` resource. This resource ensures that fsnames will be created in a sequential order without any fsname re-use. However, after an fsname is no longer in use by a file system, it will not be erased from the MGT disk. An admin may decide to periodically run the `lctl erase_lcfg [fsname]` command to remove fsnames that are no longer in use.

Below is an example `NnfLustreMGT` resource. The `NnfLustreMGT` resource for external MGSs must be created in the `nnf-system` namespace.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfLustreMGT
metadata:
  name: external-mgt
  namespace: nnf-system
spec:
  addresses:
  - "1.2.3.4@eth0:1.2.3.5@eth0"
  fsNameStart: "aaaaaaaa"
  fsNameBlackList:
  - "mylustre"
  fsNameStartReference:
    name: external-mgt
    namespace: default
    kind: ConfigMap
```

* `addresses` - This is a list of LNet addresses that could be used for this MGT. This should match any values that are used in the `externalMgs` field in the `NnfStorageProfiles`.
* `fsNameStart` - The first fsname to use. Subsequent fsnames will be incremented based on this starting fsname (e.g, `aaaaaaaa`, `aaaaaaab`, `aaaaaaac`). fsnames use lowercase letters `'a'`-`'z'`. `fsNameStart` should be exactly 8 characters long.
* `fsNameBlackList` - This is a list of fsnames that should not be given to any NNF Lustre file systems. If the MGT is hosting any non-NNF Lustre file systems, their fsnames should be included in this blacklist.
* `fsNameStartReference` - This is an optional `ObjectReference` to a `ConfigMap` that holds a starting fsname. If this field is specified, it takes precedence over the `fsNameStart` field in the spec. The `ConfigMap` will be updated to the next available fsname every time an fsname is assigned to a new Lustre file system.

### ConfigMap

For external MGTs, the `fsNameStartReference` should be used to point to a `ConfigMap` in the `default` namespace. The `ConfigMap` should be left empty initially. The `ConfigMap` is used to hold the value of the next available fsname, and it should not be deleted or modified while a `NnfLustreMGT` resource is referencing it. Removing the `ConfigMap` will cause the Rabbit software to lose track of which fsnames have already been used on the MGT. This is undesireable unless the external MGT is no longer being used by Rabbit software or if an admin has erased all previously used fsnames with the `lctl erase_lcfg [fsname]` command.

When using the `ConfigMap`, the nnf-sos software may be undeployed and redeployed without losing track of the next fsname value. During an undeploy, the `NnfLustreMGT` resource will be removed. During a deploy, the `NnfLustreMGT` resource will read the fsname value from the `ConfigMap` if it is present. The value in the `ConfigMap` will override the fsname in the `fsNameStart` field.

## Configuration with Persistent Lustre

The MGT from a persistent Lustre file system hosted on the NNF nodes can also be used as the MGT for other NNF Lustre file systems. This configuration has the advantage of not relying on any hardware outside of the cluster. However, there is no high availability, and a single MGT is still shared between all Lustre file systems created on the cluster.

To configure a persistent Lustre file system that can share its MGT, a `NnfStorageProfile` should be used that does not specify `externalMgs`. The MGT can either share a volume with the MDT or not (`combinedMgtMdt`).

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: persistent-lustre-shared-mgt
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: ""
    combinedMgtMdt: false
    standaloneMgtPoolName: ""
[...]
```

The persistent storage is created with the following DW directive:

```bash
#DW create_persistent name=shared-lustre capacity=100GiB type=lustre profile=persistent-lustre-shared-mgt
```

After the persistent Lustre file system is created, an admin can discover the MGS address by looking at the `NnfStorage` resource with the same name as the persistent storage that was created (`shared-lustre` in the above example).

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorage
metadata:
  name: shared-lustre
  namespace: default
[...]
status:
  mgsNode: 5.6.7.8@eth1
[...]
```

A separate `NnfStorageProfile` can be created that specifies the MGS address.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: internal-mgt
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: 5.6.7.8@eth1
    combinedMgtMdt: false
    standaloneMgtPoolName: ""
[...]
```

With this configuration, an admin must determine that no file systems are using the shared MGT before destroying the persistent Lustre instance.

## Configuration with an Internal MGT Pool

Another method NNF supports is to create a number of persistent Lustre MGTs on NNF nodes. These MGTs are not part of a full file system, but are instead added to a pool of MGTs available for other Lustre file systems to use. Lustre file systems that are created will choose one of the MGTs at random to use and add a reference to make sure it isn't destroyed. This configuration has the advantage of spreading the Lustre management load across multiple servers. The disadvantage of this configuration is that it does not provide high availability.

To configure the system this way, the first step is to make a pool of Lustre MGTs. This is done by creating a persistent instance from a storage profile that specifies the `standaloneMgtPoolName` option. This option tells NNF software to only create an MGT, and to add it to a named pool. The following `NnfStorageProfile` provides an example where the MGT is added to the `example-pool` pool:

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: mgt-pool-member
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: ""
    combinedMgtMdt: false
    standaloneMgtPoolName: "example-pool"
[...]
```

A persistent storage MGTs can be created with the following DW directive:

```bash
#DW create_persistent name=mgt-pool-member-1 capacity=1GiB type=lustre profile=mgt-pool-member
```

Multiple persistent instances with different names can be created using the `mgt-pool-member` profile to add more than one MGT to the pool.

To create a Lustre file system that uses one of the MGTs from the pool, an `NnfStorageProfile` should be created that uses the special notation `pool:[pool-name]` in the `externalMgs` field.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: mgt-pool-consumer
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: "pool:example-pool"
    combinedMgtMdt: false
    standaloneMgtPoolName: ""
[...]
```

The following provides an example DW directive that uses an MGT from the MGT pool:

```bash
#DW jobdw name=example-lustre capacity=100GiB type=lustre profile=mgt-pool-consumer
```

MGT pools are named, so there can be separate pools with collections of different MGTs in them. A storage profile targeting each pool would be needed.