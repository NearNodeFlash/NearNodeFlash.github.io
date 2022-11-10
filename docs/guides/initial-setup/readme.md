---
authors: Tony Floeder <anthony.floeder@@hpe.com>
categories: setup
---

# Initial Setup Instructions

Instructions for the initial setup of a Rabbit are included in this document.

## LVM Configuration on Rabbit

??? "LVM Details"
    Running LVM commands (lvcreate/lvremove) on a Rabbit to create logical volumes is problematic if those commands run within a container. Rabbit Storage Orchestration   code contained in the `nnf-node-manager` Kubernetes pod executes LVM commands from within the container. The problem is that the LVM create/remove commands wait for a   UDEV confirmation cookie that is set when UDEV rules run within the host OS. These cookies are not synchronized with the containers where the LVM commands execute.

    3 options to solve this problem are:

    1. Disable UDEV sync at the host operating system level
    2. Disable UDEV sync using the `–noudevsync` command option for each LVM command
    3. Clear the UDEV cookie using the `dmsetup udevcomplete_all` command after the lvcreate/lvremove command.

    Taking these in reverse order using option 3 above which allows UDEV settings within the host OS to remain unchanged from the default, one would need to start the   `dmsetup` command on a separate thread because the LVM create/remove command waits for the UDEV cookie. This opens too many error paths, so it was rejected.

    Option 2 allows UDEV settings within the host OS to remain unchanged from the default, but the use of UDEV within production Rabbit systems is viewed as unnecessary   because the host OS is PXE-booted onto the node vs loaded from an device that is discovered by UDEV.

    Option 1 above is what we chose to implement because it is the simplest. The following sections discuss this setting.
</details>

In order for LVM commands to run within the container environment on a Rabbit, the following change is required to the `/etc/lvm/lvm.conf` file on Rabbit.

```bash
sed -i 's/udev_sync = 1/udev_sync = 0/g' /etc/lvm/lvm.conf
```

## Kubernetes Initial Setup

Installation of Kubernetes (k8s) nodes proceeds by installing k8s components onto the master node(s) of the cluster, then installing k8s components onto the worker nodes and joining those workers to the cluster. The k8s cluster setup for Rabbit requires 3 distinct k8s node types for operation:

- Master: 1 or more master nodes which serve as the Kubernetes API server and control access to the system. For HA, at least 3 nodes should be dedicated to this role.
- Worker: 1 or more worker nodes which run the system level controller manager (SLCM) and Data Workflow Services (DWS) pods. In production, at least 3 nodes should be dedicated to this role.
- Rabbit: 1 or more Rabbit nodes which run the node level controller manager (NLCM) code. The NLCM daemonset pods are exclusively scheduled on Rabbit nodes. All Rabbit nodes are joined to the cluster as k8s workers, and they are tainted to restrict the type of work that may be scheduled on them. The NLCM pod has a toleration that allows it to run on the tainted (i.e. Rabbit) nodes.

### Certificate manager

Webhooks require the Jetstack `cert-manager`. Installation is shown below.

```bash
export certver="v1.7.0"
# Required for webhooks
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/"$certver"/cert-manager.yaml
```

### Kubernetes Node Labels

| Node Type                      | Node Label            |
| :------------------------------| :-------------------- |
| Generic Kubernetes Worker Node | cray.wlm.manager=true |
|                                | cray.nnf.manager=true |
| Rabbit Node                    | cray.nnf.node=true    |
|                                | cray.nnf.x-name=$NODE |

### Kubernetes Node Taints

| Node Type                      | Node Label                    |
| :------------------------------| :---------------------------- |
| Rabbit Node                    | cray.nnf.node=true:NoSchedule |

See [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/). The [NearNodeFlash/nnf-deploy/init.sh script](https://github.com/NearNodeFlash/nnf-deploy/blob/master/init.sh) provides examples of labeling and tainting k8s nodes for use with Rabbit.

## Rabbit System Configuration

The SystemConfiguration Custom Resource Definition (CRD) is a DWS resource that describes the hardware layout of the whole system. It is expected that an administrator creates a single SystemConfiguration resource when the system is being set up. There is no need to update the SystemConfiguration resource unless hardware is added to or removed from the system.

??? "System Configuration Details"
    Rabbit software looks for a SystemConfiguration named `default` in the `default` namespace. This resource contains a list of compute nodes and storage nodes, and it describes the mapping between them. There are two different consumers of the SystemConfiguration resource in the NNF software:

    `NnfNodeReconciler` - The reconciler for the NnfNode resource running on the Rabbit nodes reads the SystemConfiguration resource. It uses the Storage to compute mapping information to fill in the HostName section of the NnfNode resource. This information is then used to populate the DWS Storage resource.

    `NnfSystemConfigurationReconciler` - This reconciler runs in the `nnf-controller-manager`. It creates a Namespace for each compute node listed in the SystemConfiguration. These namespaces are used by the client mount code.
</details>

Here is an example `SystemConfiguration`:

| Spec Section               | Notes                                                                                                              |
| :------------------------- |--------------------------------------------------------------------------------------------------------------------|
| computeNodes               | List of names of compute nodes in the system                                                                       |
| storageNodes               | List of Rabbits and the compute nodes attached                                                                     |
| storageNodes.computeAccess | List of {slot, compute name} elements that indicate physical slot index that the named compute node is attached to |

```yaml
apiVersion: dws.cray.hpe.com/v1alpha1
kind: SystemConfiguration
metadata:
  name: default
  namespace: default
spec:
  computeNodes:
  - name: compute-01
  - name: compute-02
  - name: compute-03
  - name: compute-04
  storageNodes:
  - computesAccess:
    - index: 0
      name: compute-01
    - index: 1
      name: compute-02
    - index: 6
      name: compute-03
    name: rabbit-name-01
    type: Rabbit
  - computesAccess:
    - index: 4
      name: compute-04
    name: rabbit-name-02
    type: Rabbit
```
