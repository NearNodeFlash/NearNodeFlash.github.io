---
authors: Matt Richerson <matthew.richerson@hpe.com>
categories: setup
---

# RBAC: Role-Based Access Control

RBAC (Role Based Access Control) determines the operations a user or service can perform on a list of Kubernetes resources. RBAC affects everything that interacts with the kube-apiserver (both users and services internal or external to the cluster). More information about RBAC can be found in the Kubernetes [***documentation***](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

## RBAC for Users

This section shows how to create a kubeconfig file with RBAC set up to restrict access to view only for resources.

### Overview

User access to a Kubernetes cluster is defined through a kubeconfig file. This file contains the address of the kube-apiserver as well as the key and certificate for the user. Typically this file is located in `~/.kube/config`. When a kubernetes cluster is created, a config file is generated for the admin that allows unrestricted access to all resources in the cluster. This is the equivalent of `root` on a Linux system.

The goal of this document is to create a new kubeconfig file that allows view only access to Kubernetes resources. This kubeconfig file can be shared between the HPE employees to investigate issues on the system. This involves:

- Generating a new key/cert pair for an "hpe" user
- Creating a new kubeconfig file
- Adding RBAC rules for the "hpe" user to allow read access

### Generate a Key and Certificate

The first step is to create a new key and certificate so that HPE employees can authenticate as the "hpe" user. This will likely be done on one of the master nodes. The `openssl` command needs access to the certificate authority file. This is typically located in `/etc/kubernetes/pki`.

```bash

# make a temporary work space
mkdir /tmp/rabbit
cd /tmp/rabbit

# Create this user
export USERNAME=hpe

# generate a new key
openssl genrsa -out rabbit.key 2048

# create a certificate signing request for this user
openssl req -new -key rabbit.key -out rabbit.csr -subj "/CN=$USERNAME"

# generate a certificate using the certificate authority on the k8s cluster. This certificate lasts 500 days
openssl x509 -req -in rabbit.csr -CA /etc/kubernetes/pki/ca.crt -CAkey /etc/kubernetes/pki/ca.key -CAcreateserial -out rabbit.crt -days 500

```

### Create a kubeconfig

After the keys have been generated, a new kubeconfig file can be created for this user. The admin kubeconfig `/etc/kubernetes/admin.conf` can be used to determine the cluster name kube-apiserver address.

```bash

# create a new kubeconfig with the server information
kubectl config set-cluster $CLUSTER_NAME --kubeconfig=/tmp/rabbit/rabbit.conf --server=$SERVER_ADDRESS --certificate-authority=/etc/kubernetes/pki/ca.crt --embed-certs=true

# add the key and cert for this user to the config
kubectl config set-credentials $USERNAME --kubeconfig=/tmp/rabbit/rabbit.conf --client-certificate=/tmp/rabbit/rabbit.crt --client-key=/tmp/rabbit/rabbit.key --embed-certs=true

# add a context
kubectl config set-context $USERNAME --kubeconfig=/tmp/rabbit/rabbit.conf --cluster=$CLUSTER_NAME --user=$USERNAME
```

The kubeconfig file should be placed in a location where HPE employees have read access to it.

### Create ClusterRole and ClusterRoleBinding

The next step is to create ClusterRole and ClusterRoleBinding resources. The ClusterRole provided allows viewing all cluster and namespace scoped resources, but disallows creating, deleting, or modifying any resources.

ClusterRole
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: hpe-viewer
rules:
  - apiGroups: [ "*" ]
    resources: [ "*" ]
    verbs: [ get, list ]
```

ClusterRoleBinding
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: hpe-viewer
subjects:
- kind: User
  name: hpe
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: hpe-viewer
  apiGroup: rbac.authorization.k8s.io
```

Both of these resources can be created using the `kubectl apply` command.

### Testing

Get, List, Create, Delete, and Modify operations can be tested as the "hpe" user by setting the KUBECONFIG environment variable to use the new kubeconfig file. Get and List should be the only allowed operations. Other operations should fail with a "forbidden" error.

```bash
export KUBECONFIG=/tmp/hpe/hpe.conf
```

## RBAC for Workload Manager (WLM)

**Note** This section assumes the reader has read and understood the steps described above for setting up `RBAC for Users`.

A workload manager (WLM) such as [Flux](https://github.com/flux-framework) or [Slurm](https://slurm.schedmd.com) will interact with [DataWorkflowServices](https://dataworkflowservices.github.io) as a privileged user. RBAC is used to limit the operations that a WLM can perform on a Rabbit system.

The following steps are required to create a user and a role for the WLM.  In this case, we're creating a user to be used with the Flux WLM:

- Generate a new key/cert pair for a "flux" user
- Creating a new kubeconfig file
- Adding RBAC rules for the "flux" user to allow appropriate access to the DataWorkflowServices API.

### Generate a Key and Certificate

Generate a key and certificate for our "flux" user, similar to the way we created one for the "hpe" user above.  Substitute "flux" in place of "hpe".

### Create a kubeconfig

After the keys have been generated, a new kubeconfig file can be created for the "flux" user, similar to the one for the "hpe" user above.  Again, substitute "flux" in place of "hpe".

### Apply the provided ClusterRole and create a ClusterRoleBinding

DataWorkflowServices has already defined the role to be used with WLMs.  Simply apply the `workload-manager` ClusterRole from DataWorkflowServices to the system:

```console
kubectl apply -f https://github.com/HewlettPackard/dws/raw/master/config/rbac/workload_manager_role.yaml
```

Create and apply a ClusterRoleBinding to associate the "flux" user with the `workload-manager` ClusterRole:

ClusterRoleBinding
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: flux
subjects:
- kind: User
  name: flux
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: workload-manager
  apiGroup: rbac.authorization.k8s.io
```

The WLM should then use the kubeconfig file associated with this "flux" user to access the DataWorkflowServices API and the Rabbit system.
