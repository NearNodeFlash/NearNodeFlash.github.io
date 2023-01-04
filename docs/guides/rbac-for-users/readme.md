---
authors: Matt Richerson <matthew.richerson@hpe.com>
categories: setup
---

# RBAC for Users

This document shows how to create a kubeconfig file with RBAC set up to only allow viewing resources.

## Overview

RBAC (Role Based Access Control) sets what operations a user or service can perform on a list of kubernetes resources. RBAC affects everything that interacts with the kube-apiserver (both users and services internal or external to the cluster). More information about RBAC can be found in the kubernetes [***documentation***](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

User access to a kubernetes cluster is defined through a kubeconfig file. This file contains the address of the kube-apiserver as well as the key and certificate for the user. Typically this file is located in `~/.kube/config`. When a kubernetes cluster is created, a config file is generated for the admin that allows access to all resources in the cluster. This is the equivalent of `root` on a Linux system.

The goal of this document is to create a new kubeconfig file that only allows read access to kubernetes resources. This kubeconfig file can be shared between the HPE employees to investigate issues on the system. This involves:

- Generating a new key/cert pair for an "hpe" user
- Creating a new kubeconfig file
- Adding RBAC rules for the "hpe" user to allow read access

## Generate a Key and Certificate

The first step is to create a new key and certificate so that HPE employees can authenticate as the "hpe" user. This will likely be done on one of the master nodes. The `openssl` command needs access to the certificate authority file. This is typically located in `/etc/kubernetes/pki`.

```bash

# make a temporary work space
mkdir /tmp/hpe
cd /tmp/hpe

# generate a new key
openssl genrsa -out hpe.key 2048

# create a certificate signing request for the "hpe" user
openssl req -new -key hpe.key -out hpe.csr -subj "/CN=hpe"

# generate a certificate using the certificate authority on the k8s cluster. This certificate lasts 500 days
openssl x509 -req -in hpe.csr -CA /etc/kubernetes/pki/ca.crt -CAkey /etc/kubernetes/pki/ca.key -CAcreateserial -out hpe.crt -days 500

```

## Create a kubeconfig

After the keys have been generated, a new kubeconfig file can be created for the "hpe" user. The admin kubeconfig `/etc/kubernetes/admin.conf` can be used to determine the cluster name kube-apiserver address.

```bash

# create a new kubeconfig with the server information
kubectl config set-cluster {CLUSTER_NAME} --kubeconfig=/tmp/hpe/hpe.conf --server={SERVER_ADDRESS} --certificate-authority=/etc/kubernetes/pki/ca.crt --embed-certs=true

# add the key and cert for the "hpe" user to the config
kubectl config set-credentials hpe --kubeconfig=/tmp/hpe/hpe.conf --client-certificate=/tmp/hpe/hpe.crt --client-key=/tmp/hpe/hpe.key --embed-certs=true

# add a context
kubectl config set-context hpe-context --kubeconfig=/tmp/hpe/hpe.conf --cluster={CLUSTER_NAME} --user=hpe
```

The kubeconfig file should be placed in a location where HPE employees have read access to it.

## Create ClusterRole and ClusterRoleBinding

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

## Testing

Get, List, Create, Delete, and Modify operations can be tested as the "hpe" user by setting the KUBECONFIG environment variable to use the new kubeconfig file. Get and List should be the only allowed operations. Other operations should fail with a "forbidden" error.

```bash
export KUBECONFIG=/tmp/hpe/hpe.conf
```
