# NVMe Disk replacement process

## Hardware process

Since Rabbit does not support hot-swap of NVMe drives, in the wake of an NVMe drive failure
the Rabbit-s must be powered down for failing drives to be replaced. After NVMe disks are
replaced and Rabbit is powered up, any NVMe-hosted filesystems without redundant data will be lost.
Filesystems created with redundant information, may be recoverable as long as the redundancy is
greater than the number of NVMe devices replaced.

## Background

Rabbit storage is created through the interaction of a number of components within the NNF software stack.
All information is communicated to the NNF software via the `Workflow` resource. This resource in turn provides
a `Servers` resource which is modified to specify the Rabbits on which storage is required for the workflow.
Once the `Servers` resource has been modified to specify the Rabbits on which storage is required, the
lower layers of NNF Software engage.

## NnfStorage, NnfNodeStorage, NnfNodeBlockStorage, and nnf-ec

`NnfStorage` resource serves as the collection point for control of the storage allocation and deallocation. 

The `nnf-ec` component of NNF is responsible for managing NVMe namespaces that provide storage for
filesystems. The `NnfNodeBlockStorage` resource reflects the information provided by `nnf-ec` such
that OS-level device names associated with a storage pool's namespaces is available for filesystem
create/mount/unmount operations. The `NnfNodeStorage` resource reflects the
