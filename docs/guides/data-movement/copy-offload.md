# Copy-Offload

The copy-offload API allows a user's compute application to specify [Data Movement](../data-movement/readme.md) requests. The user's application utilizes the `libcopyoffload` library to establish a secure connection to the copy-offload server to initiate, list, query the status of, or cancel data movement requests. The copy-offload server accepts only those requests that present that Workflow's token.

The copy-offload server is implemented as a special kind of [User Container](../user-containers/readme.md). Like all user containers, this is activated by a `DW container` directive in the user's job script and runs on the Rabbit nodes that are associated with the compute nodes in the user's job.

## Administrative Configuration

### TLS signing key and certificate

A signing key and self-signed TLS certificate must be created and made available to the copy-offload server and the certificate must also be copied to each compute node. This certificate must have a SAN extension that describes all of the Rabbit nodes.

Tools are available in the `nnf-dm` repository to assist in creating this certificate and its signing key. Begin by confirming that the cluster's `SystemConfiguration` resource can be accessed using the 'kubectl' command. This resource contains the information about all of the Rabbit nodes and is used when creating the SAN extension for the certificate:

```console
kubectl get systemconfiguration
```

From the `nnf-deploy` workarea, change into the `nnf-dm` directory and run `tools/mk-usercontainer-secrets.sh`:

```console
cd nnf-dm
tools/mk-usercontainer-secrets.sh
```

That tool creates the signing key and the certificate and stores them in a Kubernetes secret named `nnf-dm-usercontainer-server-tls`. This first secret is mounted into the copy-offload server's pod when it is specified in a user's job script. The certificate is also stored alone in a Kubernetes secret named `nnf-dm-usercontainer-client-tls`. The content of this second secret can be retrieved by the administrator and copied to each compute node.

```console
CLIENT_TLS_SECRET=nnf-dm-usercontainer-client-tls
kubectl get secrets $CLIENT_TLS_SECRET -o json | jq -rM '.data."tls.crt"' | base64 -d > cert.pem
```

> [!IMPORTANT]
> Copy the certificate to `/etc/nnf-dm-usercontainer/cert.pem` on each compute node. It must be readable by all users' compute applications.

### Rabbit hostname in /etc/hosts

Each compute node must know the name of its matching rabbit node. This allows the `libcopyoffload` library, used in the user's compute application, to know which rabbit has the copy-offload server for that job. The library expects to use a generic name, `local-rabbit`, to contact that rabbit.

### WLM and the per-Workflow token

The WLM, such as Flux, must retrieve the per-Workflow token and make it available to the user's compute application as an environment variable named `DW_WORKFLOW_TOKEN`. The token is used by the `libcopyoffload` library to construct the "Bearer Token" for its requests to the copy-offload server. The token becomes invalid after the Workflow enters its teardown state.

The Workflow contains a reference to the name of the Secret that holds the token. The following value returns the name and namespace of the secret:

```console
kubectl get workflow $WORKFLOW_NAME -o json | jq -rM '.status.workflowToken'
```

If information about the token's secret is returned, then read the token from the given secret:

```console
TOKEN=$(kubectl get secret -n $SECRET_NAMESPACE $SECRET_NAME -o json | jq -rM '.data.token' | base64 -d)
```

Create the environment variable for the user's compute application:

```bash
DW_WORKFLOW_TOKEN="$TOKEN"
```

> [!NOTE]
> Per-Workflow tokens are not limited to the copy-offload API. Any user container may request to be configured with the job's per-Workflow token and the TLS certificate. See `requires=user-container-auth` in [User Containers](../user-containers/readme.md). The WLM must always check for the existence of a token secret in the Workflow.

## User Enablement of Copy Offload

Users enable the copy-offload server by requesting it in their job script. The script must contain a `DW container` directive that specifies the desired copy-offload container profile. At least one of the `DW jobdw` or `DW persistentdw` directives in the job script must include the `requires=copy-offload` statement. See [User Interactions](../user-interactions/readme.md) for more details about these directives.

The user's compute application must be linked with the `libcopyoffload` library. This library understands how to find and use the TLS certificate and the per-Workflow token required for communication with the copy-offload server for the user's job.

The copy-offload server and its container profile are specified in the `container` directive. See [User Containers](../user-containers/readme.md) for details about container profiles. The following selects the default copy-offload container profile:

```bash
#DW jobdw name=my-job-name requires=copy-offload [...]
#DW container name=copyoff-container profile=copy-offload-default [...]
```

## Certificate and Per-Workflow Token Details

The per-Workflow token and its signing key are created during the Workflow's `Setup` state, and they are destroyed when the Workflow enters `Teardown` state.

The WLM places the per-Workflow token in an environment variable for the application on the compute node. The variable is named `DW_WORKFLOW_TOKEN`. The application on the compute node can find the TLS certificate in `/etc/nnf-dm-usercontainer/cert.pem`. The `libcopyoffload` library is able to use the per-Workflow token and the TLS certificate to communicate securely with the copy-offload server.

The TLS certficate, its signing key, and the token's signing key, are mounted into the copy-offload server's Pod when it is created during the Workflow's `PreRun` state. The Pod contains the following environment variables which can be used to access the certificate and the signing keys:

| Environment Variable | Value |
|----------------------|-------|
| TLS_CERT_PATH | The pathname to the TLS certificate. |
| TLS_KEY_PATH | The pathname to the signing key for the TLS certificate. |
| TOKEN_KEY_PATH | The pathname to the signing key for the per-Workflow token. |

These pieces are not restricted to the copy-offload API. They can be used by any user container. See `requires=user-container-auth` in [User Containers](../user-containers/readme.md), and [Environment Variables](../user-interactions/readme.md#environment-variables), for details.
