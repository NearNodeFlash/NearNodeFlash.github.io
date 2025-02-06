# Kubernetes Auditing

Auditing provides records of each request that arrives in the kube-apiserver. The audit record will indicate what happened and who requested it.

## Enable Auditing

Enable auditing by installing an audit policy configuration file on each k8s master, creating a directory on the master to hold the audit logs, and providing the appropriate commandline options to kube-apiserver.

### Install an audit policy

The audit policy file will be installed on each k8s master node as `/etc/kubernetes/policies/audit-policy.yaml`.

The following is an example audit policy file that captures events for the NNF stack. Other examples can be found later in this document.

```bash
apiVersion: audit.k8s.io/v1
kind: Policy

omitStages:
- RequestReceived

rules:
- level: Metadata
  verbs: ["get", "list", "watch", "create", "patch", "update"]
  resources:

  - group: lus.cray.hpe.com
  - group: dataworkflowservices.github.io
  - group: nnf.cray.hpe.com
  - group: dm.cray.hpe.com
```

### Create a log directory

Create a directory on each k8s master to contain the audit logs.

```console
mkdir /var/log/kubernetes
```

### Configure the kube-apiserver

The following is an example patch to apply to the `/etc/kubernetes/manifests/kube-apiserver.yaml` file on each k8s master node. The arguments in this patch refer to the audit policy file location and audit log location used earlier in this document.

**Do not copy the `kube-apiserver.yaml` file to other master nodes. It contains IP addresses that are specific to one master node.**

After applying this patch to `kube-apiserver.yaml`, clear any extra patch or backup files out of `/etc/kubernetes/manifests` because kubelet will read all of them, regardless of the file suffix.

The kubelet on that master will detect the change to the `kube-apiserver.yaml` file and will restart the kube-apiserver.

```bash
--- a/kube-apiserver.yaml-orig 2024-05-13 12:18:48.256680095 -0700
+++ b/kube-apiserver.yaml 2024-05-28 13:39:50.342694448 -0700
@@ -41,6 +41,9 @@
     - --service-cluster-ip-range=10.96.0.0/12
     - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
     - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
+    - --audit-policy-file=/etc/kubernetes/policies/audit-policy.yaml
+    - --audit-log-path=/var/log/kubernetes/kube-apiserver-audit.log
+    - --audit-log-maxsize=100
     image: registry.k8s.io/kube-apiserver:v1.29.3
     imagePullPolicy: IfNotPresent
     livenessProbe:
@@ -86,6 +89,12 @@
     - mountPath: /etc/kubernetes/pki
       name: k8s-certs
       readOnly: true
+    - mountPath: /etc/kubernetes/policies/audit-policy.yaml
+      name: k8s-policies
+      readOnly: true
+    - mountPath: /var/log/kubernetes/
+      name: k8s-log
+      readOnly: false
   hostNetwork: true
   priority: 2000001000
   priorityClassName: system-node-critical
@@ -105,4 +114,12 @@
       path: /etc/kubernetes/pki
       type: DirectoryOrCreate
     name: k8s-certs
+  - hostPath:
+      path: /etc/kubernetes/policies/audit-policy.yaml
+      type: File
+    name: k8s-policies
+  - hostPath:
+      path: /var/log/kubernetes/
+      type: DirectoryOrCreate
+    name: k8s-log
 status: {}
 ```

## Disable auditing

Disable auditing by editing the `/etc/kubernetes/manifests/kube-apiserver.yaml` on each master to remove the `--audit-*` commandline options from the kube-apiserver configuration. The kubelet on that master will detect the change to the `kube-apiserver.yaml` file and will restart the kube-apiserver.

Clear any extra patch or backup files out of `/etc/kubernetes/manifests` because kubelet will read all of them, regardless of the file suffix.

## Auditing in KIND

The KIND environment that is created by the tools in nnf-deploy already has auditing enabled. See the notes in nnf-deploy's [audit-policy.yaml](https://github.com/NearNodeFlash/nnf-deploy/blob/master/config/audit-policy.yaml) to access the audit log.

## Reading the audit log

The `jq(1)` command can be used to make sense of the audit logs. The following `jq` commands have proven useful to the NNF project:

Pretty-print the log events:

```console
jq -M . kube-apiserver-audit.log | less
```

Dump a quick-to-digest summary of the log events:

```console
jq -M '[.auditID,.verb,.requestURI,.user.username,.responseStatus.code,.stageTimestamp]' kube-apiserver-audit.log | less
```

Extract a specific event record from the log:

```console
jq -M '. | select(.auditID=="d1053ee5-0734-4b40-815f-3f6831f82bac")' kube-apiserver-audit.log | less
```

## Example audit policies

Log all activity from the clientmountd daemon. Extract records from the log with:

```console
jq -M '.|select(.user.username=="system:serviceaccount:nnf-system:nnf-clientmount")' kube-apiserver-audit.log
```

This could also be adjusted to isolate any other ServiceAccount.

```bash
apiVersion: audit.k8s.io/v1
kind: Policy

omitStages:
- RequestReceived

rules:

- level: Metadata
  users: ["system:serviceaccount:nnf-system:nnf-clientmount"]
  resources:
  - group: "" # core
  - group: lus.cray.hpe.com
  - group: dataworkflowservices.github.io
  - group: nnf.cray.hpe.com
  - group: dm.cray.hpe.com
```

A more complex [audit-policy.yaml](https://github.com/NearNodeFlash/nnf-deploy/blob/master/config/audit-policy.yaml) can be found in the nnf-deploy configuration for KIND environments.

## References

### Kubernetes

[Auditing](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)

### nnf-deploy

Nnf-deploy contains a more complex audit policy:
[audit-policy.yaml](https://github.com/NearNodeFlash/nnf-deploy/blob/master/config/audit-policy.yaml)
