# Switch a Node From Worker to Master

In this example, we have htx[40-42] as worker nodes. We will remove htx[40-41] as worker nodes and re-join them as master nodes.

## Remove a k8s worker node

Begin by moving their existing pods to htx42.

Taint the nodes we're going to remove, to prevent new pods from being
SCHEDULED on them (this is different from the taint we'll use in a later step):

```console
NODE=htx40
kubectl taint node $NODE cray.nnf.node.drain=true:NoSchedule
```

Set deploy/dws-webhook to 1 replica. **This must be done via the gitops repo.**
Edit `environments/$ENV/dws/kustomization.yaml`, and add this, then wait
for argocd to put it into effect. Or, force argocd to sync it with `argocd app sync 1-dws`.

```bash
patches:
- target:
    kind: Deployment
    name: dws-webhook
  patch: |-
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: dws-webhook
    spec:
      replicas: 1
```

Taint the nodes we're going to remove, to BUMP EXISTING PODS off them (this
is different from the taint we used earlier). This will bump any DWS, NNF,
ArgoCD, cert-manager, mpi-operator, luster-fs-operator pods. This leaves any
lustre-csi-driver pods in place to assist with any Lustre unmounts that k8s may
request.

```console
kubectl taint node $NODE cray.nnf.node.drain=true:NoExecute
```

Decommission [calico node](https://docs.tigera.io/calico/latest/operations/decommissioning-a-node).

  "If you are running the node controller or using the Kubernetes API datastore
   in policy-only mode, you do not need to manually decommission nodes."

Tell k8s to drain the nodes.

Use the cray.nnf.node taints above before running 'kubectl drain'. Those
  taints allow Workflows to be terminated cleanly, even when they have Lustre
  filesystems mounted in the pods on that node. It's important that the
  lustre-csi-driver pod on that node lives long enough to assist with those
  unmounts to allow K8s to finish pod cleanup.

```console
kubectl drain --ignore-daemonsets $NODE
```

Delete the worker nodes:

```console
kubectl delete node $NODE
```

Verify that the node is deleted from calico and k8s:

```console
kubectl calico get nodes (requires the calico plugin for kubectl)
kubectl get nodes
```

Remove etcd, if it was a master:

```console
(on $NODE) kubeadm reset remove-etcd-member
```

It takes a while for all of the containers on the deleted node to stop, so be
patient.

```console
(on $NODE) crictl ps
```

Reset everything that "kubeadm join" did to that node:

```console
(on $NODE) kubeadm reset cleanup-node
```

## Join a node as a master

Check for expired "kubeadm init" or "kubeadm-certs" tokens, or expired certs:

The certificate-key from 'kubeadm init' is deleted after two hours. Use
  "kubeadm init phase upload-certs --upload-certs" to reload the certs later.
  This is explained in the output of the 'kubeadm init' command.

```console
kubeadm token list
```

The one labeled for "kubeadm init" is used as the token in "kubeadm join"
    commands.
    The one labeled for "managing TTL" controls the lifetime of the
    "kubeadm-certs" secret and the "bootstrap-token-XXX" secret. These secrets,
    and this token, are deleted after the "managing TTL" token expires.
    A worker can still join after that expires; a master cannot.

```console
kubeadm certs check-expiration
```

Re-join that node as a master. When you ran "kubeadm init" to create the
initial master node, you should have saved the output. It contains the "join"
command that you need to create new masters. You want the commandline that
includes the "--control-plane" option:

```console
(on $NODE) kubeadm join ... --control-plane ...
```

If that fails, it may tell you to generate new certs. Run the
'kubeadm init phase' command it specifies, and note the certificate key in
the output. Replace the certificate key from your original join command with
this new key and run the new join command.
