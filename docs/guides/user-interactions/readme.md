---
authors: Matt Richerson <matthew.richerson@hpe.com>
categories: provisioning
---

# Rabbit User Interactions

## Overview

A user may include one or more Data Workflow directives in their job script to request Rabbit services. Directives take the form `#DW [command] [command args]`, and are passed from the workload manager to the Rabbit software for processing. The directives can be used to allocate Rabbit file systems, copy files, and run user containers on the Rabbit nodes.

Once the job is running on compute nodes, the application can find access to Rabbit specific resources through a set of environment variables that provide mount and network access information.

## Commands

### jobdw

The `jobdw` directive command tells the Rabbit software to create a file system on the Rabbit hardware for the lifetime of the user's job. At the end of the job, any data that is not moved off of the file system either by the application or through a `copy_out` directive will be lost. Multiple `jobdw` directives can be listed in the same job script. 

#### Command Arguments
| Argument | Required | Value | Notes |
|----------|----------|-------|-------|
| `type` | Yes | `raw`, `xfs`, `gfs2`, `lustre` | Type defines how the storage should be formatted. For Lustre file systems, a single file system is created that is mounted by all computes in the job. For raw, xfs, and GFS2 storage, a separate file system is allocated for each compute node. | 
| `capacity` | Yes | Allocation size with units. `1TiB`, `100GB`, etc. | Capacity interpretation varies by storage type. For Lustre file systems, capacity is the aggregate OST capacity. For raw, xfs, and GFS2 storage, capacity is the capacity of the file system for a single compute node. Capacity suffixes are: `KB`, `KiB`, `MB`, `MiB`, `GB`, `GiB`, `TB`, `TiB` |
| `name` | Yes | String including numbers and '-' | This is a name for the storage allocation that is unique within a job |
| `profile` | No | Profile name | This specifies which profile to use when allocating storage. Profiles include `mkfs` and `mount` arguments, file system layout, and many other options. Profiles are created by admins. When no profile is specified, the default profile is used. More information about storage profiles can be found in the [Storage Profiles](../storage-profiles/readme.md) guide. |
| `requires` | No | `copy-offload` | Using this option results in the copy offload daemon running on the compute nodes. This is for users that want to initiate data movement to or from the Rabbit storage from within their application. See the [Required Daemons](../directive-breakdown/readme.md#requireddaemons) section of the [Directive Breakdown](../directive-breakdown/readme.md) guide for a description of how the user may request the daemon, in the case where the WLM will run it only on demand. | 

#### Examples

```
#DW jobdw type=xfs capacity=10GiB name=scratch
```

This directive results in a 10GiB xfs file system created for each compute node in the job using the default storage profile.

```
#DW jobdw type=lustre capacity=1TB name=dw-temp profile=high-metadata
```

This directive results in a single 1TB Lustre file system being created that can be accessed from all the compute nodes in the job. It is using a storage profile that an admin created to give high Lustre metadata performance.

```
#DW jobdw type=gfs2 capacity=50GB name=checkpoint requires=copy-offload
```

This directive results in a 50GB GFS2 file system created for each compute node in the job using the default storage profile. The copy-offload daemon is started on the compute node to allow the application to request the Rabbit to move data from the GFS2 file system to another file system while the application is running using the Copy Offload API.

### create_persistent

The `create_persistent` command results in a storage allocation on the Rabbit nodes that lasts beyond the lifetime of the job. This is useful for creating a file system that can share data between jobs. Only a single `create_persistent` directive is allowed in a job, and it cannot be in the same job as a `destroy_persistent` directive. See [persistentdw](readme.md#persistentdw) to utilize the storage in a job.

#### Command Arguments
| Argument | Required | Value | Notes |
|----------|----------|-------|-------|
| `type` | Yes | `raw`, `xfs`, `gfs2`, `lustre` | Type defines how the storage should be formatted. For Lustre file systems, a single file system is created. For raw, xfs, and GFS2 storage, a separate file system is allocated for each compute node in the job. | 
| `capacity` | Yes | Allocation size with units. `1TiB`, `100GB`, etc. | Capacity interpretation varies by storage type. For Lustre file systems, capacity is the aggregate OST capacity. For raw, xfs, and GFS2 storage, capacity is the capacity of the file system for a single compute node. Capacity suffixes are: `KB`, `KiB`, `MB`, `MiB`, `GB`, `GiB`, `TB`, `TiB` |
| `name` | Yes | Lowercase string including numbers and '-' | This is a name for the storage allocation that is unique within the system |
| `profile` | No | Profile name | This specifies which profile to use when allocating storage. Profiles include `mkfs` and `mount` arguments, file system layout, and many other options. Profiles are created by admins. When no profile is specified, the default profile is used. The profile used when creating the persistent storage allocation is the same profile used by jobs that use the persistent storage. More information about storage profiles can be found in the [Storage Profiles](../storage-profiles/readme.md) guide.|

#### Examples

```
#DW create_persistent type=xfs capacity=100GiB name=scratch
```

This directive results in a 100GiB xfs file system created for each compute node in the job using the default storage profile. Since xfs file systems are not network accessible, subsequent jobs that want to use the file system must have the same number of compute nodes, and be scheduled on compute nodes with access to the correct Rabbit nodes. This means the job with the `create_persistent` directive must schedule the desired number of compute nodes even if no application is run on the compute nodes as part of the job.

```
#DW create_persistent type=lustre capacity=10TiB name=shared-data profile=read-only
```

This directive results in a single 10TiB Lustre file system being created that can be accessed later by any compute nodes in the system. Multiple jobs can access a Rabbit Lustre file system at the same time. This job can be scheduled with a single compute node (or zero compute nodes if the WLM allows), without any limitations on compute node counts for subsequent jobs using the persistent Lustre file system.

### destroy_persistent
The `destroy_persistent` command will delete persistent storage that was allocated by a corresponding `create_persistent`. If the persistent storage is currently in use by a job, then the job containing the `destroy_persistent` command will fail. Only a single `destroy_persistent` directive is allowed in a job, and it cannot be in the same job as a `create_persistent` directive.

#### Command Arguments
| Argument | Required | Value | Notes |
|----------|----------|-------|-------|
| `name` | Yes | Lowercase string including numbers and '-' | This is a name for the persistent storage allocation that will be destroyed |

#### Examples

```
#DW destroy_persistent name=shared-data
```

This directive will delete the persistent storage allocation with the name `shared-data`

### persistentdw
The `persistentdw` command makes an existing persistent storage allocation available to a job. The persistent storage must already be created from a `create_persistent` command in a different job script. Multiple `persistentdw` commands can be used in the same job script to request access to multiple persistent allocations.

Persistent Lustre file systems can be accessed from any compute nodes in the system, and the compute node count for the job can vary as needed. Multiple jobs can access a persistent Lustre file system concurrently if desired. Raw, xfs, and GFS2 file systems can only be accessed by compute nodes that have a physical connection to the Rabbits hosting the storage, and jobs accessing these storage types must have the same compute node count as the job that made the persistent storage.

#### Command Arguments
| Argument | Required | Value | Notes |
|----------|----------|-------|-------|
| `name` | Yes | Lowercase string including numbers and '-' | This is a name for the persistent storage that will be accessed |
| `requires` | No | `copy-offload` | Using this option results in the copy offload daemon running on the compute nodes. This is for users that want to initiate data movement to or from the Rabbit storage from within their application. See the [Required Daemons](../directive-breakdown/readme.md#requireddaemons) section of the [Directive Breakdown](../directive-breakdown/readme.md) guide for a description of how the user may request the daemon, in the case where the WLM will run it only on demand. |

#### Examples

```
#DW persistentdw name=shared-data requires=copy-offload
```

This directive will cause the `shared-data` persistent storage allocation to be mounted onto the compute nodes for the job application to use. The copy-offload daemon will be started on the compute nodes so the application can request data movement during the application run.

### copy_in/copy_out

The `copy_in` and `copy_out` directives are used to move data to and from the storage allocations on Rabbit nodes. The `copy_in` directive requests that data be moved into the Rabbit file system before application launch, and the `copy_out` directive requests data to be moved off of the Rabbit file system after application exit. This is different from data-movement that is requested through the copy-offload API, which occurs during application runtime. Multiple `copy_in` and `copy_out` directives can be included in the same job script. More information about data movement can be found in the [Data Movement](../data-movement/readme.md) documentation.

#### Command Arguments
| Argument | Required | Value | Notes |
|----------|----------|-------|-------|
| `source` | Yes | `[path]`, `$DW_JOB_[name]/[path]`, `$DW_PERSISTENT_[name]/[path]` | `[name]` is the name of the Rabbit persistent or job storage as specified in the `name` argument of the `jobdw` or `persistentdw` directive. Any `'-'` in the name from the `jobdw` or `persistentdw` directive should be changed to a `'_'` in the `copy_in` and `copy_out` directive. |
| `destination` | Yes | `[path]`, `$DW_JOB_[name]/[path]`, `$DW_PERSISTENT_[name]/[path]` | `[name]` is the name of the Rabbit persistent or job storage as specified in the `name` argument of the `jobdw` or `persistentdw` directive. Any `'-'` in the name from the `jobdw` or `persistentdw` directive should be changed to a `'_'` in the `copy_in` and `copy_out` directive. |
| `profile` | No | Profile name | This specifies which profile to use when copying data. Profiles specify the copy command to use, MPI arguments, and how output gets logged. If no profile is specified then the default profile is used. Profiles are created by an admin. |

#### Examples

```
#DW jobdw type=xfs capacity=10GiB name=fast-storage
#DW copy_in source=/lus/backup/johndoe/important_data destination=$DW_JOB_fast_storage/data
```

This set of directives creates an xfs file system on the Rabbits for each compute node in the job, and then moves data from `/lus/backup/johndoe/important_data` to each of the xfs file systems. `/lus/backup` must be set up in the Rabbit software as a [Global Lustre](../global-lustre/readme.md) file system by an admin. The copy takes place before the application is launched on the compute nodes.

```
#DW persistentdw name=shared-data1
#DW persistentdw name=shared-data2

#DW copy_out source=$DW_PERSISTENT_shared_data1/a destination=$DW_PERSISTENT_shared_data2/a profile=no-xattr
#DW copy_out source=$DW_PERSISTENT_shared_data1/b destination=$DW_PERSISTENT_shared_data2/b profile=no-xattr
```

This set of directives copies two directories from one persistent storage allocation to another persistent storage allocation using the `no-xattr` profile to avoid copying xattrs. This data movement occurs after the job application exits on the compute nodes, and the two copies do not occur in a deterministic order.

```
#DW persistentdw name=shared-data
#DW jobdw type=lustre capacity=1TiB name=fast-storage profile=high-metadata

#DW copy_in source=/lus/shared/johndoe/shared-libraries destination=$DW_JOB_fast_storage/libraries
#DW copy_in source=$DW_PERSISTENT_shared_data/ destination=$DW_JOB_fast_storage/data

#DW copy_out source=$DW_JOB_fast_storage/data destination=/lus/backup/johndoe/very_important_data profile=no-xattr
```

This set of directives makes use of a persistent storage allocation and a job storage allocation. There are two `copy_in` directives, one that copies data from the global lustre file system to the job allocation, and another that copies data from the persistent allocation to the job allocation. These copies do not occur in a deterministic order. The `copy_out` directive occurs after the application has exited, and copies data from the Rabbit job storage to a global lustre file system.

### container

The `container` directive is used to launch user containers on the Rabbit nodes. The containers have access to `jobdw`, `persistentdw`, or global Lustre storage as specified in the `container` directive. More documentation for user containers can be found in the [User Containers](../user-containers/readme.md) guide. Only a single `container` directive is allowed in a job.

#### Command Arguments
| Argument | Required | Value | Notes |
|----------|----------|-------|-------|
| `name` | Yes | Lowercase string including numbers and '-' | This is a name for the container instance that is unique within a job |
| `profile` | Yes | Profile name | This specifies which container profile to use. The container profile contains information about which container to run, which file system types to expect, which network ports are needed, and many other options. An admin is responsible for creating the container profiles. |
| `DW_JOB_[expected]` | No | `jobdw` storage allocation `name` | The container profile will list `jobdw` file systems that the container requires. `[expected]` is the name as specified in the container profile |
| `DW_PERSISTENT_[expected]` | No | `persistentdw` storage allocation `name` | The container profile will list `persistentdw` file systems that the container requires. `[expected]` is the name as specified in the container profile |
| `DW_GLOBAL_[expected]` | No | Global lustre path | The container profile will list global Lustre file systems that the container requires. `[expected]` is the name as specified in the container profile |

#### Examples

```
#DW jobdw type=xfs capacity=10GiB name=fast-storage
#DW container name=backup profile=automatic-backup DW_JOB_source=fast-storage DW_GLOBAL_destination=/lus/backup/johndoe
```

These directives create an xfs Rabbit job allocation and specify a container that should run on the Rabbit nodes. The container profile specified two file systems that the container needs, `DW_JOB_source` and `DW_GLOBAL_destination`. `DW_JOB_source` requires a `jobdw` file system and `DW_GLOBAL_destination` requires a global Lustre file system. 

## Environment Variables

The WLM makes a set of environment variables available to the job application running on the compute nodes that provide Rabbit specific information. These environment variables are used to find the mount location of Rabbit file systems and port numbers for user containers.

| Environment Variable | Value | Notes |
|----------------------|-------|-------|
| `DW_JOB_[name]` | Mount path of a `jobdw` file system | `[name]` is from the `name` argument in the `jobdw` directive. Any `'-'` characters in the `name` will be converted to `'_'` in the environment variable. There will be one of these environment variables per `jobdw` directive in the job. |
| `DW_PERSISTENT_[name]` | Mount path of a `persistentdw` file system | `[name]` is from the `name` argument in the `persistentdw` directive. Any `'-'` characters in the `name` will be converted to `'_'` in the environment variable. There will be one of these environment variables per `persistentdw` directive in the job. |
| `NNF_CONTAINER_PORTS` | Comma separated list of ports | These ports are used together with the IP address of the local Rabbit to communicate with a user container specified by a `container` directive. More information can be found in the [User Containers](../user-containers/readme.md) guide.