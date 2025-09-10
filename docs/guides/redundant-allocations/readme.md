---
authors: Matt Richerson <matt.richerson@hpe.com>
categories: provisioning
---

# Redundant Allocations

## Background

Lustre, XFS, and Raw allocations can be created using a redundant configuration either through zpools or LVM. This guide documents how these configurations might be used.

## Creating a Redundant Allocation
 
An allocation may choose to use a redundant configuration to allow access to data even when a drive has failed. In addition, rebuild commands can be specified to allow a replacement drive to be added to the RAID.

The [Storage Profiles](../storage-profiles/readme.md) section details the command lines needed to create an allocation using a RAID device.

## Rebuilding a Redundant Allocation

Choosing whether to allow a redundant allocation to be rebuilt with a new drive depends on the file system and allocation type.

### LVM

For XFS and Raw allocations using LVM, the RAID device can only be rebuilt when the Rabbit node has the LV activated. For `jobdw` allocations, this means that the RAID cannot be rebuilt while the compute nodes have the LV activated between `PreRun` and `PostRun`. For this reason, the most common way to use RAID configurations in this situation will be without rebuilding enabled.

If an XFS or Raw allocation is made with `create_persistent`, then the rebuild commands should be specified to allow the RAID to be rebuilt when no compute nodes have the LV activated.

### Zpool

For Lustre allocations using zpool, there are no restrictions on when rebuild commands can be used. The RAID can be rebuilt for job and persistent instances regardless of whether the compute nodes have the file system mounted.

### Replacing a Drive

If a drive has failed and needs to be replaced, the Rabbit-p and Rabbit-s should be powered off to replace the drive. After powering the Rabbit back on, the `nnf-node-manager` pod will restart on the Rabbit. On initialization, Rabbit software will find the new drive and add an NVMe namespace for each allocation. If the rebuild commands have been specified, the Rabbit software will run them to add the new NVMe namespace into the RAID device.

## Allocation Status

If the allocation is a `PersistentStorageInstance`, the status of the RAID device is available in the `Status.State` field. If all the RAIDs in the persistent storage are healthy, `Status.State=Active`. If any of the RAIDs are degraded, `Status.State=Degraded`.