---
authors: Matt Richerson <matthew.richerson@hpe.com>
categories: provisioning
---

# Directive Breakdown

## Background

The `#DW` directives in a job script are not intended to be interpreted by the workload manager. The workload manager passes the `#DW` directives to the NNF software through the DWS `workflow` resource, and the NNF software determines what resources are needed to satisfy the directives. The NNF software communicates this information back to the workload manager through the DWS `DirectiveBreakdown` resource. This document describes how the WLM should interpret the information in the `DirectiveBreakdown`.

## DirectiveBreakdown Overview

The DWS `DirectiveBreakdown` contains all the information necessary to inform the WLM how to pick storage and compute nodes for a job. The `DirectiveBreakdown` resource is created by the NNF software during the `Proposal` phase of the DWS workflow. The `spec` section of the `DirectiveBreakdown` is filled in with the `#DW` directive by the NNF software, and the `status` section contains the information for the WLM. The WLM should wait until the `status.ready` field is true before interpreting the rest of the `status` fields.

The contents of the `DirectiveBreakdown` will look different depending on the file system type and options specified by the user. The `status` section contains enough information that the WLM may be able to figure out the underlying file system type requested by the user, but the WLM should not make any decisions based on the file system type. Instead, the WLM should make storage and compute allocation decisions based on the generic information provided in the `DirectiveBreakdown` since the storage and compute allocations needed to satisfy a `#DW` directive may differ based on options other than the file system type.

## Storage Nodes

The `status.storage` section of the `DirectiveBreakdown` describes how the storage allocations should be made and any constraints on the NNF nodes that can be picked. The `status.storage` section will exist only for `jobdw` and `create_persistent` directives. An example of the `status.storage` section is included below.

```yaml
...
spec:
  directive: '#DW jobdw capacity=1GiB type=xfs name=example'
    userID: 7900
status:
...
  ready: true
  storage:
    allocationSets:
    - allocationStrategy: AllocatePerCompute
      constraints:
        labels:
        - dataworkflowservices.github.io/storage=Rabbit
      label: xfs
      minimumCapacity: 1073741824
    lifetime: job
    reference:
      kind: Servers
      name: example-0
      namespace: default
...
```

* `status.storage.allocationSets` is a list of storage allocation sets that are needed for the job. An allocation set is a group of individual storage allocations that all have the same parameters and requirements. Depending on the storage type specified by the user, there may be more than one allocation set. Allocation sets should be handled independently.

* `status.storage.allocationSets.allocationStrategy` specifies how the allocations should be made.
    * `AllocatePerCompute` - One allocation is needed per compute node in the job. The size of an individual allocation is specified in `status.storage.allocationSets.minimumCapacity`
    * `AllocateAcrossServers` - One or more allocations are needed with an aggregate capacity of `status.storage.allocationSets.minimumCapacity`. This allocation strategy does not imply anything about how many allocations to make per NNF node or how many NNF nodes to use. The allocations on each NNF node should be the same size.
    * `AllocateSingleServer` - One allocation is needed with a capacity of `status.storage.allocationSets.minimumCapacity`

* `status.storage.allocationSets.constraints` is a set of requirements for which NNF nodes can be picked. More information about the different constraint types is provided in the [Storage Constraints](readme.md#storage-constraints) section below.

* `status.storage.allocationSets.label` is an opaque string that the WLM uses when creating the spec.allocationSets entry in the DWS `Servers` resource.

* `status.storage.allocationSets.minimumCapacity` is the allocation capacity in bytes. The interpretation of this field depends on the value of `status.storage.allocationSets.allocationStrategy`

* `status.storage.lifetime` is used to specify how long the storage allocations will last.
    * `job` - The allocation will last for the lifetime of the job
    * `persistent` - The allocation will last for longer than the lifetime of the job

* `status.storage.reference` is an object reference to a DWS `Servers` resource where the WLM can specify allocations

### Storage Constraints

Constraints on an allocation set provide additional requirements for how the storage allocations should be made on NNF nodes.

* `labels` specifies a list of labels that must all be on a DWS `Storage` resource in order for an allocation to exist on that `Storage`.
```yaml
constraints:
  labels:
  - dataworkflowservices.github.io/storage=Rabbit
  - mysite.org/pool=firmware_test
```
```yaml
apiVersion: dataworkflowservices.github.io/v1alpha2
kind: Storage
metadata:
  labels:
    dataworkflowservices.github.io/storage: Rabbit
    mysite.org/pool: firmware_test
    mysite.org/drive-speed: fast
  name: rabbit-node-1
  namespace: default
  ...
```

* `colocation` specifies how two or more allocations influence the location of each other. The colocation constraint has two fields, `type` and `key`. Currently, the only value for `type` is `exclusive`. `key` can be any value. This constraint means that the allocations from an allocation set with the colocation constraint can't be placed on an NNF node with another allocation whose allocation set has a colocation constraint with the same key. Allocations from allocation sets with colocation constraints with different keys or allocation sets without the colocation constraint are okay to put on the same NNF node.
```yaml
constraints:
  colocation:
    type: exclusive
    key: lustre-mgt
```

* `count` this field specifies the number of allocations to make when `status.storage.allocationSets.allocationStrategy` is `AllocateAcrossServers`
```yaml
constraints:
  count: 5
```

* `scale` is a unitless value from 1-10 that is meant to guide the WLM on how many allocations to make when `status.storage.allocationSets.allocationStrategy` is `AllocateAcrossServers`. The actual number of allocations is not meant to correspond to the value of scale. Rather, 1 would indicate the minimum number of allocations to reach `status.storage.allocationSets.minimumCapacity`, and 10 would be the maximum number of allocations that make sense given the `status.storage.allocationSets.minimumCapacity` and the compute node count. The NNF software does not interpret this value, and it is up to the WLM to define its meaning.
```yaml
constraints:
  scale: 8
```

## Compute Nodes

The `status.compute` section of the `DirectiveBreakdown` describes how the WLM should pick compute nodes for a job. The `status.compute` section will exist only for `jobdw` and `persistentdw` directives. An example of the `status.compute` section is included below.

```yaml
...
spec:
  directive: '#DW jobdw capacity=1TiB type=lustre name=example'
    userID: 3450
status:
...
  compute:
    constraints:
      location:
      - access:
        - priority: mandatory
          type: network
        - priority: bestEffort
          type: physical
        reference:
          fieldPath: servers.spec.allocationSets[0]
          kind: Servers
          name: example-0
          namespace: default
      - access:
        - priority: mandatory
          type: network
        reference:
          fieldPath: servers.spec.allocationSets[1]
          kind: Servers
          name: example-0
          namespace: default
...
```

The `status.compute.constraints` section lists any constraints on which compute nodes can be used. Currently the only constraint type is the `location` constraint. `status.compute.constraints.location` is a list of location constraints that all must be satisfied.

A location constraint consists of an `access` list and a `reference`.

* `status.compute.constraints.location.reference` is an object reference with a `fieldPath` that points to an allocation set in the `Servers` resource. If this is from a `#DW jobdw` directive, the `Servers` resource won't be filled in until the WLM picks storage nodes for the allocations.
* `status.compute.constraints.location.access` is a list that specifies what type of access the compute nodes need to have to the storage allocations in the allocation set. An allocation set may have multiple access types that are required
    * `status.compute.constraints.location.access.type` specifies the connection type for the storage. This can be `network` or `physical`
    * `status.compute.constraints.location.access.priority` specifies how necessary the connection type is. This can be `mandatory` or `bestEffort`

## RequiredDaemons

The `status.requiredDaemons` section of the `DirectiveBreakdown` tells the WLM about any driver-specific daemons it must enable for the job; it is assumed that the WLM knows about the driver-specific daemons and that if the users are specifying these then the WLM knows how to start them. The `status.requiredDaemons` section will exist only for `jobdw` and `persistentdw` directives. An example of the `status.requiredDaemons` section is included below.

```yaml
status:
...
  requiredDaemons:
  - copy-offload
...
```

The allowed list of required daemons that may be specified is defined in the [nnf-ruleset.yaml for DWS](https://github.com/NearNodeFlash/nnf-sos/blob/master/config/dws/nnf-ruleset.yaml), found in the `nnf-sos` repository. The `ruleDefs.key[requires]` statement is specified in two places in the ruleset, one for `jobdw` and the second for `persistentdw`. The ruleset allows a list of patterns to be specified, allowing one for each of the allowed daemons.

The `DW` directive will include a comma-separated list of daemons after the `requires` keyword. The following is an example:

```bash
#DW jobdw type=xfs capacity=1GB name=stg1 requires=copy-offload
```

The `DWDirectiveRule` resource currently active on the system can be viewed with:

```console
kubectl get -n dws-system dwdirectiverule nnf -o yaml
```

### Valid Daemons

Each site should define the list of daemons that are valid for that site and recognized by that site's WLM. The initial `nnf-ruleset.yaml` defines only one, called `copy-offload`. When a user specifies `copy-offload` in their `DW` directive, they are stating that their compute-node application will use the Copy Offload API Daemon described in the [Data Movement Configuration](../data-movement/readme.md).
