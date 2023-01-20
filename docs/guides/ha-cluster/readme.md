---
authors: Nate Thornton <nate.thornton@hpe.com>
categories: setup
---

# High Availability Cluster

NNF software supports provisioning of Red Hat GFS2 (Global File System 2) storage. Per RedHat:
> GFS2 allows multiple nodes to share storage at a block level as if the storage were connected locally to each cluster node. GFS2 cluster file system requires a cluster infrastructure.

Therefore, in order to use GFS2, the NNF node and its associated compute nodes must form a high availability cluster.

## Cluster Setup

Red Hat provides instructions for [creating a high availability cluster with Pacemaker](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_creating-high-availability-cluster-configuring-and-managing-high-availability-clusters#doc-wrapper), including instructions for [installing cluster software](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_creating-high-availability-cluster-configuring-and-managing-high-availability-clusters#proc_installing-cluster-software-creating-high-availability-cluster) and
[creating a high availability cluster](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_creating-high-availability-cluster-configuring-and-managing-high-availability-clusters).


## Fencing Agents

Fencing is the process of restricting and releasing access to resources that a failed cluster node may have access to. Since a failed node may be unresponsive, an external device must exist that can restrict access to shared resources of that node, or to issue a hard reboot of the node. More information can be found form Red Hat: [1.2.1 Fencing](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_overview-of-high-availability-configuring-and-managing-high-availability-clusters#fencing).

HPE hardware implements software known as the Hardware System Supervisor (HSS), which itself conforms to the SNIA Redfish/Swordfish standard. This provides the means to manage hardware outside the host OS.

### Compute Fencing

The [Redfish fencing agent](https://github.com/ClusterLabs/fence-agents/tree/main/agents/redfish) from [ClusterLabs](https://github.com/ClusterLabs/fence-agents) should be used for Compute nodes in the cluster. Configure the agent with the following parameters:

| Argument | Definition |
| -------- | ---------- |
| `ip=[ADDRESS]` | The IP address or hostname of the HSS controller |
| `port=80` | The Port of the HSS controller. Must be `80` |
| `systems-uri=/redfish/v1/Systems/1` | The URI of the Systems object. Must be `/redfish/v1/Systems/1` |
| `ssl-insecure=true` | Instructs the use of an insecure SSL exchange. Must be `true` |
| `username=[USER]` | The user name for connecting to the HSS controller |
| `password=[PASSWORD]` | the password for connecting to the HSS controller |

For example, setting up the Redfish fencing agent on "rabbit-compute-2" with the redfish service at "192.168.0.1"

```shell
pcs stonith create rabbit-compute-2 fence_redfish pcmk_host_list=rabbit-compute-2 ip=192.168.0.1 systems-uri=/redfish/v1/Systems/1 username=root password=password ssl_insecure=true
```

### NNF Fencing

#### Source
The NNF Fencing agent is available at https://github.com/NearNodeFlash/fence-agents under the `nnf` branch.

```shell
git clone https://github.com/NearNodeFlash/fence-agents --branch nnf
```
#### Build

Refer to the NNF.md file at the root directory of the fence-agents repository

#### Setup
Configure the NNF agent with the following parameters:

| Argument | Definition |
| -------- | ---------- |
| `kubernetes-service-host=[ADDRESS]` | The IP address of the kubeapi server |
| `kubernetes-service-port=[PORT]` | The listening port of the kubeapi server |
| `service-token-file=[PATH]` | The location of the service token file. The file must be present on all nodes within the cluster |
| `service-cert-file=[PATH]` | The location of the service certificate file. The file must be present on all nodes within the cluster |
| `nnf-node-name=[NNF-NODE-NAME]` | Name of the NNF node as it is appears in the System Configuration |
| `api-version=[VERSION]` | The API Version of the NNF Node resource. Defaults to "v1alpha1" |

For example, setting up the NNF fencing agent on `rabbit-node-1` with a kubernetes service API running at `192.168.0.1:6443` and the service token and certificate copied to `/etc/nnf/fence/`.

```
pcs stonith create rabbit-node-1 fence_nnf pcmk_host_list=rabbit-node-1 kubernetes-service-host=192.168.0.1 kubernetes-service-port=6443 service-token-file=/etc/nnf/fence/service.token service-cert-file=/etc/nnf/fence/service.cert nnf-node-name=rabbit-node-1
```

#### Recovery
Since the NNF node is connected to 16 compute blades, careful coordination around fencing of a NNF node is required to minimize the impact of the outage. When a Rabbit node is fenced, the corresponding DWS Storage resource (`storages.dws.cray.hpe.com`) status changes. The workload manager must observe this change and follow the procedure below to recover from the fencing status.

1. Observed the `storage.Status` changed and that `storage.Status.RequiresReboot == True`
2. Set the `storage.Spec.State := Disabled`
4. Wait for a change to the Storage status `storage.Status.State == Disabled`
5. Reboot the NNF node
6. Set the `storage.Spec.State := Enabled`
7. Wait for `storage.Status.State == Enabled`

### Dummy Fencing

The [dummy fencing agent](https://github.com/ClusterLabs/fence-agents/tree/main/agents/dummy) from ClusterLabs can be used for nodes in the cluster for an early access development system.

## Configuring a GFS2 file system in a cluster

Follow steps 1-8 of the procedure from Red Hat: [Configuring a GFS2 file system in a cluster](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_high_availability_clusters/assembly_configuring-gfs2-in-a-cluster-configuring-and-managing-high-availability-clusters#doc-wrapper).
