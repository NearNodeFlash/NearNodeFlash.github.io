# Copy-Offload

The copy-offload API allows a user's compute application to specify [Data Movement](../data-movement/readme.md) requests. The user's application utilizes the `libcopyoffload` library to establish a secure connection to the copy-offload API server to initiate, list, query the status of, or cancel data movement requests.

The copy-offload server is implemented as a special kind of [User Container](../user-containers/readme.md). Like all user containers, this is activated by a `DW container` directive in the user's workflow script and runs on the Rabbit nodes that are associated with the compute nodes in the user's job.

## Administrative Configuration

A self-signed TLS certificate and signing key must be created and made available to the copy-offload server and the certificate must also be copied to each compute node. This certificate must have a SAN extension that describes all of the Rabbit nodes.

Tools are available in the `nnf-dm` repository to assist in creating this certificate and its signing key. Begin by confirming that you can access your cluster's `SystemConfiguration` resource using the 'kubectl' command. This resource contains the information about all of the Rabbit nodes and will be used when creating the SAN extension for the certificate:

```console
kubectl get systemconfiguration
```

From your `nnf-deploy` workarea, change into the `nnf-dm` directory and run `tools/mk-usercontainer-secrets.sh`:

```console
cd nnf-dm
tools/mk-usercontainer-secrets.sh
```

That tool creates the certificate and stores it and its signing key in a Kubernetes secret named `nnf-dm-usercontainer-server-tls`. This secret will be mounted into the copy-offload server's pod when it is specified in a user's workflow script.

It will also store the certificate alone in a Kubernetes secret named `nnf-dm-usercontainer-client-tls`. The content of this secret can be retrieved by the administrator and copied to each compute node.

```console
CLIENT_TLS_SECRET=nnf-dm-usercontainer-client-tls
kubectl get secrets $CLIENT_TLS_SECRET -o json | jq -rM '.data."tls.crt"' | base64 -d > cert.pem
```

> [!IMPORTANT]
> Copy the certificate to `/etc/nnf-dm-usercontainer/cert.pem` on each compute node. It must be readable by your users' applications.

## Per-Workflow token



In Workflow. Flux reads it, adds it as an env variable for the compute application. Libcopyoffload knows this env var. This env var is added to the [Compute Node Environment Variables](../user-containers/readme.md#compute-node-environment-variables).

Lifecycle.

## User Configuration

Authentication

   'DW jobdw' with 'requires'



   copy-offload server
      - mounts k8s secret that has TLS cert and signing key
      - mounts k8s secret that has token signing key


Copy-offload NnfContainerProfile



The copy-offload client library.



The hostname of the compute's matching rabbit. Must already be in the compute's
/etc/hosts file as "rabbit". (find other doc here that describes this)
  (it's in user-containers doc)


Lifecycle of the copy-offload server. This is implemented as a user-container,
so it has the same lifecycle as other user-containers (find other doc that
describes this):
  (it's in "Running a Container Workflow" of user-containers doc)

  Proposal does ...
  Setup does ...
  PreRun does...

  Server shuts down at ...


Copy-offload API version, between server and client library.


User-containers

  How to request auth for your own user container application.
  (Find doc that describes user-containers, and update with auth stuff.)


