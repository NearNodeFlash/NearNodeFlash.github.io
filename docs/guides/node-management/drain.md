# Draining A Node

The NNF software consists of a collection of DaemonSets and Deployments. The pods
on the Rabbit nodes are usually from DaemonSets. Because of this, the `kubectl drain`
command is not able to remove the NNF software from a node.  See [Safely Drain a Node](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/) for details about
the limitations posed by DaemonSet pods.

Given the limitations of DaemonSets, the NNF software will be drained by using taints,
as described in
[Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/).

## Drain NNF Pods From A Rabbit Node

Drain the NNF software from a node by applying the `cray.nnf.node.drain` taint.
The CSI driver pods will remain on the node to satisfy any unmount requests from k8s
as it cleans up the NNF pods.

```shell
kubectl taint node $NODE cray.nnf.node.drain=true:NoSchedule cray.nnf.node.drain=true:NoExecute
```

To restore the node to service, remove the `cray.nnf.node.drain` taint.

```shell
kubectl taint node $NODE cray.nnf.node.drain-
```

## The CSI Driver

While the CSI driver pods may be drained from a Rabbit node, it is advisable not to do so.

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
