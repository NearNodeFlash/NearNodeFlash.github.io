---
authors: Matt Richerson <matthew.richerson@hpe.com>
categories: provisioning
---

# Lustre External MGS

## Background

Lustre has a limitation where only a single MGT can be mounted on a node at a single time. In the NNF cluster, this means the total number of Lustre file systems is limited to the number of NNF nodes. It also places extra scheduling constraints on the WLM to ensure that the MGTs don't conflict.

A Lustre MGS is able to provide management for multiple separate Lustre file systems. The NNF software can be configured to take advantage of this to extend the maximum number of Lustre file systems beyond the number of NNF nodes. To do this, one or more Lustre MGSs must be specified that have a lifetime longer than any of the Lustre file systems that are using it. This can be done in a few different ways hrough the NNF software:

1. Use a Lustre MGS from outside the NNF cluster
2. Create a persistent Lustre file system through DWS and use the MGS it provides
3. Create a pool of standalone persistent Lustre MGTs, and have the NNF software select one of them as the MGS

These three methods are not mutually exclusive on the system as a whole. Individual file systems can use any of options 1-3 or create their own MGT.

## Configuration with an External MGS

An existing MGS external to the NNF cluster can be used to manage the Lustre file systems on the NNF nodes. An advantage to this configuration is that the MGS can be highly available. A disadvantage is that there is only a single MGS. An MGS serving more than a handful of Lustre file systems is not a common use case, so the Lustre code may prove less stable. Also, some Lustre operations from the clients may be slower if the MGS is located outside of the high speed network the compute nodes are on.

The following yaml provides an example of what the `NnfStorageProfile` should contain to use an external MGS.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: external-mgs
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

The MGS from a persistent Lustre file system hosted on the NNF nodes can also be used as an external MGS. This configuration has the advantage of not relying on any hardware outside of the cluster as well as hosting the MGS inside the high speed network. However, there is no high availability, and a single MGS is still serving all the Lustre file systems created on the cluster.

To configure a persistent Lustre file system that can share its MGS, a `NnfStorageProfile` should be used that does not specify an external MGS. The MGT can either share a volume with the MDT or not (`combinedMgtMdt`).

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: persistent-lustre-shared-mgs
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: ""
    combinedMgtMdt: true
    standaloneMgtPoolName: ""
[...]
```

The persistent storage is created with the following DW directive

```bash
#DW create_persistent name=shared-lustre capacity=100GiB type=lustre profile=persistent-lustre-shared-mgs
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
  name: internal-mgs
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: 5.6.7.8@eth1
    combinedMgtMdt: false
    standaloneMgtPoolName: ""
[...]
```

With this configuration, an admin must determine that no file systems are using the shared MGS before destroying the persistent Lustre instance.

## Configuration with an Internal MGS Pool

Another method NNF supports is to create a number of persistent Lustre MGTs on NNF nodes. These MGTs are not part of a full file system, but are instead added to a pool of MGTs available for other Lustre file systems to use. Lustre file systems that are created will choose one of the MGSs at random to use and add a reference to make sure it isn't destroyed. This configuration has the advantage of spreading the Lustre management load across multiple servers and keeping MGS traffic within the high speed network. The disadvantage of this configuration is that is does not provide high availability.

To configure the system this way, the first step is to make a pool of Lustre MGTs. This is done by creating a persistent instance from a storage profile that specifies the `standaloneMgtPoolName` option. This option tells NNF software to only create an MGT, and to add it to a named pool. The following `NnfStorageProfile` provides an example where the MGT is added to the `example-pool` pool:

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: mgs-pool-member
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: ""
    combinedMgtMdt: false
    standaloneMgtPoolName: "example-pool"
[...]
```

The persistent storage is created with the following DW directive:

```bash
#DW create_persistent name=mgt-pool-member-1 capacity=1GiB type=lustre profile=mgt-pool-member
```

Multiple persistent instances can be created using the `mgt-pool-member` profile to add more than one MGS to the pool. To create a Lustre file system that uses one of the MGSs from the pool, an `NnfStorageProfile` should be created that uses the special notation `pool:[pool-name]` in the `externalMgs` field.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfStorageProfile
metadata:
  name: mgs-pool-consumer
  namespace: nnf-system
data:
[...]
  lustreStorage:
    externalMgs: "pool:example-pool"
    combinedMgtMdt: false
    standaloneMgtPoolName: ""
[...]
```

The following provides an example DW directive that uses an MGS from the MGS pool:

```bash
#DW jobdw name=example-lustre capacity=100GiB type=lustre profile=mgt-pool-consumer
```

MGS pools are named, so there can be separate pools with collections of different MGSs in them. A storage profile targeting each pool would be needed.