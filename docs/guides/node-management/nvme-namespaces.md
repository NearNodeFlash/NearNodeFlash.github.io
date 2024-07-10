# Debugging NVMe Namespaces

## Total Space Available or Used

Find the total space available, and the total space used, on a Rabbit node using the Redfish API. One way to access the API is to use the `nnf-node-manager` pod on that node.

To view the space on node ee50, find its `nnf-node-manager` pod and then exec into it to query the Redfish API:

```console
[richerso@ee1:~]$ kubectl get pods -A -o wide | grep ee50 | grep node-manager
nnf-system             nnf-node-manager-jhglm                               1/1     Running                     0                 61m     10.85.71.11       ee50   <none>           <none>
```

Then query the Redfish API to view the `AllocatedBytes` and `GuaranteedBytes`:

```console
[richerso@ee1:~]$ kubectl exec --stdin --tty -n nnf-system nnf-node-manager-jhglm -- curl -S localhost:50057/redfish/v1/StorageServices/NNF/CapacitySource | jq
{
  "@odata.id": "/redfish/v1/StorageServices/NNF/CapacitySource",
  "@odata.type": "#CapacitySource.v1_0_0.CapacitySource",
  "Id": "0",
  "Name": "Capacity Source",
  "ProvidedCapacity": {
    "Data": {
      "AllocatedBytes": 128849888,
      "ConsumedBytes": 128849888,
      "GuaranteedBytes": 307132496928,
      "ProvisionedBytes": 307261342816
    },
    "Metadata": {},
    "Snapshot": {}
  },
  "ProvidedClassOfService": {},
  "ProvidingDrives": {},
  "ProvidingPools": {},
  "ProvidingVolumes": {},
  "Actions": {},
  "ProvidingMemory": {},
  "ProvidingMemoryChunks": {}
}
```

## Total Orphaned or Leaked Space

To determine the amount of orphaned space, look at the Rabbit node when there are no allocations on it. If there are no allocations then there should be no `NnfNodeBlockStorages` in the k8s namespace with the Rabbit's name:

```console
[richerso@ee1:~]$ kubectl get nnfnodeblockstorage -n ee50
No resources found in ee50 namespace.
```

To check that there are no orphaned namespaces, you can use the nvme command while logged into that Rabbit node:

```console
[root@ee50:~]# nvme list
Node                  SN                   Model                                    Namespace Usage                      Format           FW Rev
--------------------- -------------------- ---------------------------------------- --------- -------------------------- ---------------- --------
/dev/nvme0n1          S666NN0TB11877       SAMSUNG MZ1L21T9HCLS-00A07               1           8.57  GB /   1.92  TB    512   B +  0 B   GDC7302Q
```

There should be no namespaces on the kioxia drives:

```console
[root@ee50:~]# nvme list | grep -i kioxia
[root@ee50:~]#
```

If there are namespaces listed, and there weren't any `NnfNodeBlockStorages` on the node, then they need to be deleted through the Rabbit software. The `NnfNodeECData` resource is a persistent data store for the allocations that should exist on the Rabbit. By deleting it, and then deleting the nnf-node-manager pod, it causes nnf-node-manager to delete the orphaned namespaces. This can take a few minutes after you actually delete the pod:

```console
kubectl delete nnfnodeecdata ec-data -n ee50
kubectl delete pod -n nnf-system nnf-node-manager-jhglm
```
