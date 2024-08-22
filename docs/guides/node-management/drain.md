# Disable Or Drain A Node

## Disabling a node

A Rabbit node can be manually disabled, indicating to the WLM that it should not schedule more jobs on the node. Jobs currently on the node will be allowed to complete at the discretion of the WLM.

Disable a node by setting its Storage state to `Disabled`.

```shell
kubectl patch storage $NODE --type=json -p '[{"op":"replace", "path":"/spec/state", "value": "Disabled"}]'
```

When the Storage is queried by the WLM, it will show the disabled status.

```console
$ kubectl get storages
NAME           STATE      STATUS     MODE   AGE
kind-worker2   Enabled    Ready      Live   10m
kind-worker3   Disabled   Disabled   Live   10m
```

To re-enable a node, set its Storage state to `Enabled`.

```shell
kubectl patch storage $NODE --type=json -p '[{"op":"replace", "path":"/spec/state", "value": "Enabled"}]'
```

The Storage state will show that it is enabled.

```console
kubectl get storages
NAME           STATE     STATUS   MODE   AGE
kind-worker2   Enabled   Ready    Live   10m
kind-worker3   Enabled   Ready    Live   10m
```

## Draining a node

The NNF software consists of a collection of DaemonSets and Deployments. The pods
on the Rabbit nodes are usually from DaemonSets. Because of this, the `kubectl drain`
command is not able to remove the NNF software from a node.  See [Safely Drain a Node](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/) for details about
the limitations posed by DaemonSet pods.

Given the limitations of DaemonSets, the NNF software will be drained by using taints,
as described in
[Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/).

This would be used only after the WLM jobs have been removed from that Rabbit (preferably) and there is some reason to also remove the NNF software from it. This might be used before a Rabbit is powered off and pulled out of the cabinet, for example, to avoid leaving pods in "Terminating" state (harmless, but it's noise).

If an admin used this taint before power-off it would mean there wouldn't be "Terminating" pods lying around for that Rabbit. After a new/same Rabbit is put back in its place, the NNF software won't jump back on it while the taint is present. The taint can be removed at any time, from immediately after the node is powered off up to some time after the new/same Rabbit is powered back on.

### Drain NNF pods from a rabbit node

Drain the NNF software from a node by applying the `cray.nnf.node.drain` taint.
The CSI driver pods will remain on the node to satisfy any unmount requests from k8s
as it cleans up the NNF pods.

```shell
kubectl taint node $NODE cray.nnf.node.drain=true:NoSchedule cray.nnf.node.drain=true:NoExecute
```

This will cause the node's `Storage` resource to be drained:

```console
$ kubectl get storages
NAME           STATE     STATUS    MODE   AGE
kind-worker2   Enabled   Drained   Live   5m44s
kind-worker3   Enabled   Ready     Live   5m45s
```

The `Storage` resource will contain the following message indicating the reason it has been drained:

```console
$ kubectl get storages rabbit1 -o json | jq -rM .status.message
Kubernetes node is tainted with cray.nnf.node.drain
```

To restore the node to service, remove the `cray.nnf.node.drain` taint.

```shell
kubectl taint node $NODE cray.nnf.node.drain-
```

The `Storage` resource will revert to a `Ready` status.

### The CSI driver

While the CSI driver pods may be drained from a Rabbit node, it is inadvisable to do so.

**Warning** K8s relies on the CSI driver to unmount any filesystems that may have
been mounted into a pod's namespace. If it is not present when k8s is attempting
to remove a pod then the pod may be left in "Terminating" state. This is most
obvious when draining the `nnf-dm-worker` pods which usually have filesystems
mounted in them.

Drain the CSI driver pod from a node by applying the `cray.nnf.node.drain.csi`
taint.

```shell
kubectl taint node $NODE cray.nnf.node.drain.csi=true:NoSchedule cray.nnf.node.drain.csi=true:NoExecute
```

To restore the CSI driver pods to that node, remove the `cray.nnf.node.drain.csi` taint.

```shell
kubectl taint node $NODE cray.nnf.node.drain.csi-
```

This taint will also drain the remaining NNF software if has not already been
drained by the `cray.nnf.node.drain` taint.
