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
    externalMgs: 1.2.3.4@eth0
    combinedMgtMdt: false
    standaloneMgtPoolName: ""
[...]
```

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