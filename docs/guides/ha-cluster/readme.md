---
authors: Tony Floeder <anthony.floeder@hpe.com>
categories: setup
---

# High Availability Cluster Setup for Rabbit Nodes

NNF software supports provisioning of Red Hat GFS2 (Global File System 2) storage. GFS2 allows multiple nodes to share storage at a block level as if the storage were connected locally to each cluster node. To use GFS2, each Rabbit node and its associated compute nodes must form a high-availability cluster using Pacemaker and Corosync.

## Table of Contents

- [Background: Pacemaker and Corosync](#background-pacemaker-and-corosync)
- [Cluster Architecture](#cluster-architecture)
- [Cluster Setup](#cluster-setup)
- [Quorum Configuration](#quorum-configuration)
  - [Why the Rabbit Needs 17 Votes](#why-the-rabbit-needs-17-votes)
  - [Configuring Quorum Votes](#configuring-quorum-votes)
- [Fencing with fence_recorder](#fencing-with-fence_recorder)
  - [How It Works](#how-it-works)
  - [Installation](#installation)
  - [STONITH Configuration](#stonith-configuration)
  - [Configuration Options](#configuration-options)
  - [Verifying Configuration](#verifying-configuration)
- [Request/Response Protocol](#requestresponse-protocol)
  - [Request File Format](#request-file-format)
  - [Response File Format](#response-file-format)
  - [Atomic File Writing](#atomic-file-writing)
- [Log Files](#log-files)
- [Troubleshooting](#troubleshooting)
  - [Check STONITH Status](#check-stonith-status)
  - [Common Issues](#common-issues)
  - [Testing Fence Operations](#testing-fence-operations)
- [GFS2 File System Configuration](#gfs2-file-system-configuration)
- [Dynamic Cluster Lifecycle](#dynamic-cluster-lifecycle)
- [References](#references)

## Background: Pacemaker and Corosync

**Corosync** provides the cluster communication layer—it handles node membership, messaging between nodes, and quorum decisions. When a node becomes unresponsive, Corosync detects this and informs Pacemaker.

**Pacemaker** is the cluster resource manager. It decides where resources run, handles failover when nodes fail, and coordinates fencing (STONITH) to protect shared storage from corruption.

**Fencing (STONITH)** ensures that when a node fails, it is forcibly removed from the cluster before other nodes access its shared resources. Without fencing, a failed node could corrupt shared storage if it continues writing after the cluster assumes it's dead.

For comprehensive documentation, see:

- [Red Hat: Overview of High Availability](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_high_availability_clusters/assembly_overview-of-high-availability-configuring-and-managing-high-availability-clusters)
- [Red Hat: Fencing in a Red Hat High Availability Cluster](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_high_availability_clusters/assembly_configuring-fencing-configuring-and-managing-high-availability-clusters)

## Cluster Architecture

Each Rabbit node forms a separate HA cluster with its 16 compute nodes:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        Rabbit Cluster (17 nodes)                        │
│                                                                         │
│                         ┌──────────────┐                                │
│                         │ rabbit-node-1│                                │
│                         │   (Rabbit)   │                                │
│                         └──────────────┘                                │
│                                │                                        │
│        ┌───────────┬───────────┼───────────┬────────────┐               │
│        │           │           │           │            │               │
│        ▼           ▼           ▼           ▼            ▼               │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐         │
│   │compute-1│ │compute-2│ │  · · ·  │ │compute-15│ │compute-16│         │
│   └─────────┘ └─────────┘ └─────────┘ └──────────┘ └──────────┘         │
│                                                                         │
│                All 17 nodes communicate via Corosync                    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Cluster Setup

Red Hat provides comprehensive instructions for cluster setup:

- [Installing Cluster Software](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_high_availability_clusters/assembly_creating-high-availability-cluster-configuring-and-managing-high-availability-clusters#proc_installing-cluster-software-creating-high-availability-cluster)
- [Creating a High Availability Cluster](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_high_availability_clusters/assembly_creating-high-availability-cluster-configuring-and-managing-high-availability-clusters)

Each cluster should be named after the Rabbit node hostname. The following examples use `rabbit-node-1` with compute nodes numbered 1-16:

```bash
# On each node, install cluster packages
dnf install pcs pacemaker fence-agents-all

# Enable and start pcsd
systemctl enable --now pcsd

# Set hacluster password (same on all nodes)
echo 'password' | passwd --stdin hacluster

# From the Rabbit node, authenticate all 17 nodes
pcs host auth rabbit-node-1 \
    rabbit-compute-1 rabbit-compute-2 rabbit-compute-3 rabbit-compute-4 \
    rabbit-compute-5 rabbit-compute-6 rabbit-compute-7 rabbit-compute-8 \
    rabbit-compute-9 rabbit-compute-10 rabbit-compute-11 rabbit-compute-12 \
    rabbit-compute-13 rabbit-compute-14 rabbit-compute-15 rabbit-compute-16 \
    -u hacluster -p password

# Create the cluster with all nodes
pcs cluster setup rabbit-node-1 \
    rabbit-node-1 \
    rabbit-compute-1 rabbit-compute-2 rabbit-compute-3 rabbit-compute-4 \
    rabbit-compute-5 rabbit-compute-6 rabbit-compute-7 rabbit-compute-8 \
    rabbit-compute-9 rabbit-compute-10 rabbit-compute-11 rabbit-compute-12 \
    rabbit-compute-13 rabbit-compute-14 rabbit-compute-15 rabbit-compute-16

pcs cluster start --all
pcs cluster enable --all
```

## Quorum Configuration

Quorum determines how many nodes must agree before the cluster can take action. By default, each node gets one vote and quorum requires a majority. However, in the Rabbit cluster architecture, the Rabbit node owns all NVMe storage—compute nodes only access storage through the Rabbit. This creates an asymmetric relationship that requires special quorum configuration.

### Why the Rabbit Needs 17 Votes

The Rabbit node must **always** have quorum because:

1. **Storage ownership**: The Rabbit owns all NVMe namespaces. If compute nodes could fence the Rabbit, they would lose access to all storage anyway.

2. **Preventing split-brain**: If the Rabbit becomes isolated from compute nodes (network partition), compute nodes should not be able to form their own quorum and attempt to fence the Rabbit.

3. **Fencing authority**: Only the Rabbit (via NNF software) can properly detach storage from failed compute nodes. Compute nodes cannot fence each other directly.

With 17 votes for the Rabbit and 1 vote per compute node:

| Scenario | Votes | Quorum (17 required) | Result |
|----------|-------|----------------------|--------|
| Rabbit alone | 17 | ✓ Yes | Rabbit can fence any compute node |
| All 16 computes, no Rabbit | 16 | ✗ No | Computes cannot take action |
| Rabbit + any computes | 17+ | ✓ Yes | Normal operation |

### Configuring Quorum Votes

After cluster setup, configure voting weights:

```bash
# Stop the cluster to modify corosync.conf
pcs cluster stop --all

# Edit corosync.conf on the Rabbit node to set votes
# The nodelist section should look like:
#
# nodelist {
#     node {
#         ring0_addr: rabbit-node-1
#         nodeid: 1
#         quorum_votes: 17
#     }
#     node {
#         ring0_addr: rabbit-compute-1
#         nodeid: 2
#         quorum_votes: 1
#     }
#     ... (repeat for all compute nodes)
# }

# After editing, sync the configuration to all nodes
pcs cluster sync

# Start the cluster
pcs cluster start --all

# Verify quorum configuration
corosync-quorumtool
```

The output should show the Rabbit with 17 votes and each compute with 1 vote, for a total of 33 votes and quorum at 17.

## Fencing with fence_recorder

The `fence_recorder` agent coordinates fencing with external NNF software using a request/response file pattern. When Pacemaker decides to fence a compute node, `fence_recorder`:

1. Writes a fence request file
2. Waits for the NNF software to process the request and write a response
3. Returns success or failure to Pacemaker

This allows the NNF software to perform storage cleanup (detaching NVMe namespaces) before the fence operation completes.

> **Note:** Although the fence action is named "reboot", the NNF software does **not** actually reboot the compute node. Instead, the Rabbit's NNF software detaches all NVMe namespaces from the target compute node, preventing it from accessing any shared storage. This is sufficient for GFS2's requirements—the failed node can no longer corrupt shared data, regardless of whether it is still running.

### How It Works

```text
┌──────────────────────┐
│  Pacemaker/Corosync  │
│  (Cluster Manager)   │
└──────────┬───────────┘
           │ Calls fence_recorder
           ▼
┌──────────────────────┐       ┌───────────────────────────────┐
│   fence_recorder     │──────▶│   Request File                │
│   (Fence Agent)      │       │   requests/<node>-<uuid>.json │
└──────────────────────┘       └───────────────────────────────┘
           │                                  │
           │ Waits for response               │ NNF software reads request
           │                                  ▼
           │                   ┌───────────────────────────────┐
           │                   │   NNF Software                │
           │                   │   - Detaches storage          │
           │                   │   - Updates node status       │
           │                   └───────────────────────────────┘
           │                                  │
           ▼                                  │ Writes response
┌───────────────────────────────┐             │
│   Response File               │◀────────────┘
│   responses/<node>-<uuid>.json│
└───────────────────────────────┘
           │
           │ Exit 0 (success) or 1 (failure)
           ▼
┌──────────────────────┐
│      Pacemaker       │
└──────────────────────┘
```

### Installation

Install `fence_recorder` on all nodes in the cluster:

```bash
# Copy the agent to each node
sudo cp fence_recorder /usr/sbin/fence_recorder
sudo chmod 755 /usr/sbin/fence_recorder

# Create the request/response directories on each rabbit node
sudo mkdir -p /localdisk/fence-recorder/{requests,responses}
sudo chmod 755 /localdisk/fence-recorder/{requests,responses}

# Create log directory
sudo mkdir -p /var/log/cluster
sudo chmod 755 /var/log/cluster
```

### STONITH Configuration

Create a STONITH resource for each compute node. Run these commands from any node in the cluster:

```bash
# Create STONITH resources for all 16 compute nodes (1-16)
for i in $(seq 1 16); do
    pcs stonith create compute-${i}-fence-recorder fence_recorder \
        port=compute-${i} \
        pcmk_host_list=compute-${i} \
        request_dir=/localdisk/fence-recorder/requests \
        response_dir=/localdisk/fence-recorder/responses \
        log_dir=/var/log/cluster \
        op monitor interval=120s timeout=10s
done

# Enable fencing
pcs property set stonith-enabled=true
```

Alternatively, create resources individually:

```bash
# Example: Create STONITH for rabbit-compute-1
pcs stonith create compute-1-fence-recorder fence_recorder \
    port=rabbit-compute-1 \
    pcmk_host_list=compute-1 \
    request_dir=/localdisk/fence-recorder/requests \
    response_dir=/localdisk/fence-recorder/responses \
    log_dir=/var/log/cluster \
    op monitor interval=120s timeout=10s
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `port` | (required) | Target node name to fence |
| `pcmk_host_list` | (required) | Node this STONITH resource can fence |
| `request_dir` | `/var/run/fence_recorder/requests` | Directory for fence request files |
| `response_dir` | `/var/run/fence_recorder/responses` | Directory for fence response files |
| `log_dir` | `/var/log/cluster` | Directory for log files |

### Verifying Configuration

```bash
# Check STONITH status
pcs stonith status

# View STONITH configuration
pcs stonith config

# Test that fence_recorder can generate metadata
fence_recorder --action metadata
```

## Request/Response Protocol

### Request File Format

When a fence operation is triggered, `fence_recorder` writes a JSON request file:

**Location**: `<request_dir>/<node>-<uuid>.json`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-01-10T14:30:00-06:00",
  "action": "reboot",
  "target_node": "rabbit-compute-1",
  "recorder_node": "rabbit-node-1"
}
```

### Response File Format

The NNF software writes a response file after processing:

**Location**: `<response_dir>/<node>-<uuid>.json`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "action_performed": "reboot",
  "target_node": "rabbit-compute-1",
  "message": "Successfully fenced node",
  "timestamp": "2025-01-10T14:30:15-06:00"
}
```

### Atomic File Writing

Both request and response files use atomic rename to ensure consumers only see complete files:

1. Write to temporary file: `.<filename>.tmp`
2. Close the file
3. Rename to final name: `<filename>`

File watchers should ignore files starting with `.` (hidden/temporary files).

## Log Files

Log files are written to the configured log directory:

| File | Format | Description |
|------|--------|-------------|
| `fence-events.log` | Timestamped text | Main operational log |
| `fence-events-readable.log` | Key=value | Grep-friendly format |
| `fence-events-detailed.jsonl` | JSON Lines | Machine-parseable format |

## Troubleshooting

### Check STONITH Status

```bash
# View current status
pcs stonith status

# Check for failed resources
pcs status

# View detailed configuration
pcs stonith config <resource-name>
```

### Common Issues

**STONITH resource stopped or failed:**

```bash
# Clean up failed resource state
pcs resource cleanup <resource-name>

# Check logs for errors
journalctl -u pacemaker | grep -i stonith
```

**Timeout waiting for response:**

```bash
# Check if NNF software is processing requests
ls -la /localdisk/fence-recorder/requests/
ls -la /localdisk/fence-recorder/responses/

# Check fence_recorder logs
tail -f /var/log/cluster/fence-events.log
```

**Module not found error:**
Ensure the fencing library path is correct in `/usr/sbin/fence_recorder`. The `sys.path.append` line should point to `/usr/share/fence`.

### Testing Fence Operations

```bash
# Test metadata generation
fence_recorder --action metadata

# Test monitor action (non-destructive)
fence_recorder --action monitor -n rabbit-compute-1 \
    --request-dir=/localdisk/fence-recorder/requests \
    --response-dir=/localdisk/fence-recorder/responses
```

## GFS2 File System Configuration

After the cluster is configured with fencing, you can configure GFS2 file systems. See Red Hat documentation:

- [Configuring a GFS2 File System in a Cluster](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_high_availability_clusters/assembly_configuring-gfs2-in-a-cluster-configuring-and-managing-high-availability-clusters)

## Dynamic Cluster Lifecycle

Unlike traditional HA clusters that run continuously on all nodes, NNF manages Pacemaker cluster services dynamically on compute nodes based on workflow requirements. Cluster services run **continuously on the Rabbit** but are **started and stopped dynamically on compute nodes**.

### When Cluster Services Start on Compute Nodes

NNF software starts Pacemaker/Corosync cluster services on compute nodes when:

1. A workflow requests GFS2 storage
2. The NNF software provisions the GFS2 file system
3. Compute nodes need to mount the shared storage

At this point, cluster services are started on participating compute nodes, they join the Rabbit's cluster, fencing is enabled, and the GFS2 file system is mounted.

> See [Storage Profiles](https://nearnodeflash.github.io/latest/guides/storage-profiles/readme/) for more information about how to start cluster services using the `PreActivate` command.

### When Cluster Services Stop on Compute Nodes

When the GFS2 workflow completes:

1. The GFS2 file system is unmounted from all compute nodes
2. Storage resources are cleaned up
3. Pacemaker/Corosync cluster services are stopped on compute nodes
4. The Rabbit continues running cluster services

> See [Storage Profiles](https://nearnodeflash.github.io/latest/guides/storage-profiles/readme/) for more information about how to stop cluster services using the `PostDeactivate` command.

This dynamic lifecycle means:

- **Rabbit runs cluster services continuously**: Always ready to accept compute nodes
- **Compute node services are transient**: They run only for the duration of GFS2 workflows
- **Resource efficiency**: Cluster overhead on compute nodes is incurred only when needed
- **Reduced complexity**: No long-running cluster services to maintain on compute nodes between jobs

> **Note:** The cluster configuration (node membership, quorum votes, STONITH resources) is set up during system provisioning and persists on all nodes. Only the cluster *services* on compute nodes are started and stopped dynamically.

## References

- [Red Hat: Configuring and Managing High Availability Clusters](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_high_availability_clusters/)
- [Red Hat: Fencing in a Cluster](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_high_availability_clusters/assembly_configuring-fencing-configuring-and-managing-high-availability-clusters)
- [ClusterLabs fence-agents](https://github.com/ClusterLabs/fence-agents)
