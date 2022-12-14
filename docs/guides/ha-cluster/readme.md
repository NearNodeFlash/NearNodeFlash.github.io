---
authors: Nate Thornton <nate.thornton@hpe.com>
categories: setup
---

# High Availability Cluster

Rabbit software supports provisioning of Red Hat GFS2 (Global File System 2) storage. Per Red Hat:
> GFS2 allows multiple nodes to share storage at a block level as if the storage were connected locally to each cluster node. GFS2 cluster file system requires a cluster infrastructure.

Therefore, in order to use GFS2, the Rabbit and its associated compute nodes must form a high availability cluster.

## Cluster Setup

Red Hat provides instructions for [creating a high availability cluster with Pacemaker](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_creating-high-availability-cluster-configuring-and-managing-high-availability-clusters#doc-wrapper), including instructions for [installing cluster software](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_creating-high-availability-cluster-configuring-and-managing-high-availability-clusters#proc_installing-cluster-software-creating-high-availability-cluster) and
[creating a high availability cluster](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_creating-high-availability-cluster-configuring-and-managing-high-availability-clusters).


## Fencing Agents

Fencing is the process of restricting and releasing access to resources that a failed cluster node may have access to. Since a failed node may be unresponsive, an external device must exist that can restrict access to shared resources of that node, or to issue a hard reboot of the node. More information can be found form Red Hat: [1.2.1 Fencing](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_overview-of-high-availability-configuring-and-managing-high-availability-clusters#fencing).

HPE hardware implements software known as the Hardware System Supervisor (HSS), which itself conforms to the SNIA Redfish/Swordfish standard. This provides the means to manage hardware outside the host OS.

### Compute Fencing

!!! warning
    Usage of the Redfish fencing agent is not yet verified

The [Redfish fencing agent](https://github.com/ClusterLabs/fence-agents/tree/main/agents/redfish) from [ClusterLabs](https://github.com/ClusterLabs/fence-agents) should be used for Compute nodes in the cluster. Configure the agent with the following parameters:

| Argument | Definition |
| -------- | ---------- |
| `--ip=[ADDRESS]` | The IP address or hostname of the compute node's HSS node controller |
|`--systems-uri=[URI]` | The URI of the Systems object. Must be `/redfish/v1/Systems/Node0` |
|`--ssl-insecure` | Instructs the use of an insecure SSL exchange |


### Rabbit Fencing

!!! info
    Rabbit fencing agent is in active development; the description below is subject to change.

Since the Rabbit node is connected to 16 compute blades, careful coordination around fencing of a Rabbit node is required to minimize the impact of the outage. When a Rabbit node is fenced, the corresponding Kubernetes Storage resource (`storages.dws.cray.hpe.com`) is updated with a status of 'Fenced'. The workload manager must observe this change and handle the movement of resources off the Rabbit node and clear the 'Fenced' status before forcibly rebooting the node.

Configure the Rabbit agent with the following parameters:

| Argument | Definition |
| -------- | ---------- |
| `--kubernetes-service-host=[ADDRESS]` | The IP address of the kubeapi server |
| `--kubernetes-service-port=[PORT]` | The listening port of the kube api server |
| `--service-token-file=[PATH]` | The location of the service token file. The file must be present on all nodes within the cluster |
| `--service-cert-file=[PATH]` | The location of the service certificate file. The file must be present on all nodes within the cluster |
| `--nnf-node-name=[RABBIT-NODE-NAME]` | Name of the rabbit node |

### Dummy Fencing

The [dummy fencing agent](https://github.com/ClusterLabs/fence-agents/tree/main/agents/dummy) from ClusterLabs can be used for nodes in the cluster for an early access development system.

## Configuring a GFS2 file system in a cluster

Follow steps 1-8 of the procedure from Red Hat: [Configuring a GFS2 file system in a cluster](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_configuring-gfs2-in-a-cluster-configuring-and-managing-high-availability-clusters#doc-wrapper).
