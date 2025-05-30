# NNF User Containers

NNF User Containers are a mechanism to allow user-defined containerized applications to be run on
Rabbit nodes with access to NNF ephemeral and persistent storage.

## Overview

Container workflows are orchestrated through the use of two components: Container Profiles and
Container Directives. A Container Profile defines the container to be executed. Most
importantly, it allows you to specify which NNF storages are accessible within the container and
which container image to run. The containers are executed on the NNF nodes that are allocated to
your container workflow. These containers can be executed in either of two modes: Non-MPI and MPI.

For Non-MPI applications, the image and command are launched across all the targeted NNF Nodes
in a uniform manner. This is useful in simple applications, where non-distributed behavior is
desired.

For MPI applications, a single launcher container serves as the point of contact, responsible for
distributing tasks to various worker containers. Each of the NNF nodes targeted by the workflow
receives its corresponding worker container. The focus of this documentation will be on MPI
applications.

To see a full working example before diving into these docs, see [Putting It All
Together](#putting-it-all-together).

## Before Creating a Container Workflow

Before creating a workflow, a working `NnfContainerProfile` must exist. This profile is referenced
in the container directive supplied with the workflow.

### Container Profiles

The author of a containerized application will work with the administrator to define a pod
specification template for the container and to create an appropriate `NnfContainerProfile` resource
for the container. The image and tag for the user's container will be specified in the profile.

The image must be available in a registry that is available to your system. This could be docker.io,
ghcr.io, etc., or a private registry. Note that for a private registry, some additional setup is
required. See [here](#using-a-private-container-repository) for more info.

The image itself has a few requirements. See [here](#creating-images) for more info on building images.

New `NnfContainerProfile` resources may be created by copying one of the provided example profiles
from the `nnf-system` namespace . The examples may be found by listing them with `kubectl`:

```console
kubectl get nnfcontainerprofiles -n nnf-system
```

The next few subsections provide an overview of the primary components comprising an
`NnfContainerProfile`. However, it's important to note that while these sections cover the key
aspects, they don't encompass every single detail. For an in-depth understanding of the capabilities
offered by container profiles, we recommend referring to the following resources:

- [Type definition](https://github.com/NearNodeFlash/nnf-sos/blob/master/api/v1alpha7/nnfcontainerprofile_types.go#L36) for `NnfContainerProfile`
- [Examples](https://github.com/NearNodeFlash/nnf-sos/blob/master/config/examples/nnf_nnfcontainerprofiles.yaml) for `NnfContainerProfile` (same as `kubectl get` above)

#### Container Storages

The `Storages` defined in the profile allow NNF filesystems to be made available inside the
container. These storages need to be referenced in the container workflow unless they are marked as
optional.

There are three types of storages available to containers:

- local non-persistent storage (created via `#DW jobdw` directives)
- persistent storage (created via `#DW create_persistent` directives)
- global lustre storage (defined by `LustreFilesystems`)

For local and persistent storage, only GFS2 and Lustre filesystems are supported. Raw and XFS
filesystems cannot be mounted more than once, so they cannot be mounted inside of a container while
also being mounted on the NNF node itself.

For each storage in the profile, the name must follow these patterns (depending on the storage type):

- `DW_JOB_<storage_name>`
- `DW_PERSISTENT_<storage_name>`
- `DW_GLOBAL_<storage_name>`

`<storage_name>` is provided by the user and needs to be a name compatible with Linux environment
variables (so underscores must be used, not dashes), since the storage mount directories are
provided to the container via environment variables.

This storage name is used in container workflow directives to reference the NNF storage name that
defines the filesystem. Find more info on that in [Creating a Container
Workflow](#creating-a-container-workflow).

Storages may be deemed as `optional` in a profile. If a storage is not optional, the storage name
must be set to the name of an NNF filesystem name in the container workflow.

For global lustre, there is an additional field for `pvcMode`, which must match the mode that is
configured in the `LustreFilesystem` resource that represents the global lustre filesystem. This
defaults to `ReadWriteMany`.

Example:

```yaml
  storages:
  - name: DW_JOB_foo_local_storage
    optional: false
  - name: DW_PERSISTENT_foo_persistent_storage
    optional: true
  - name: DW_GLOBAL_foo_global_lustre
    optional: true
    pvcMode: ReadWriteMany
```

#### Container Spec

As mentioned earlier, container workflows can be categorized into two types: MPI and Non-MPI. It is
essential to choose and define only one of these types within the container profile. Regardless of
the chosen type, the same data structure is used to implement the specification.

An
[`NnfPodSpec`](https://github.com/NearNodeFlash/nnf-sos/blob/master/api/v1alpha7/nnfcontainerprofile_types.go#L93)
is used to define the specification for the pod and its containers. Inside the `NnfPodSpec` is an
[`NnfContainer`](https://github.com/NearNodeFlash/nnf-sos/blob/master/api/v1alpha7/nnfcontainerprofile_types.go#L145).

Both `NnfPodSpec` and `NnfContainer` are simplified versions of Kubernetes
[`PodSpec`](https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/#PodSpec).

- **Non-MPI Containers**: The specification utilizes the `spec` resource.
- **MPI Containers**: The `mpiSpec` resource is used. Unlike Non-MPI containers, `mpiSpec` includes
two `NnfPodSpec` definitions: one for the MPI Launcher and another for the Workers. The MPI Launcher
facilitates the execution of MPI applications across worker containers.

For assistance in identifying the Rabbit node running the Launcher, refer to the
`NNF_CONTAINER_LAUNCHER` environment variable below.

See the [`mpiSpec`
definition](https://github.com/NearNodeFlash/nnf-sos/blob/master/api/v1alpha7/nnfcontainerprofile_types.go#L119)
for more details on what can be configured for an MPI application.

Please refer to the examples listed above for more details on container specifications.

#### Container Ports

Container Profiles allow for ports to be reserved for a container workflow. `numPorts` can be used
to specify the number of ports needed for a container workflow. The ports are opened on each
targeted NNF node and are accessible outside the cluster. Users must know how to contact the
specific NNF node. It is recommended that DNS entries are made for this purpose.

In the workflow, the allocated port numbers are made available via the
[`NNF_CONTAINER_PORTS`](#nnf_container_ports) environment variable.

The workflow requests this number of ports from the `NnfPortManager`, which is responsible for
managing the ports allocated to container workflows. This resource can be inspected to see which
ports are allocated.

Once a port is assigned to a workflow, that port number becomes unavailable for use by any other
workflow until it is released.

!!! note

    The `SystemConfiguration` must be configured to allow for a range of ports, otherwise container
    workflows will fail in the `Setup` state due to insufficient resources. See [SystemConfiguration
    Setup](#systemconfiguration-setup).

### Rabbit Hostname Setup

On each compute node there must be a file named `/etc/local-rabbit.conf` that contains the hostname of the compute's matching rabbit node. Compute node applications use this to communicate with the server in the user container. This is generally used for the non-MPI case.

For the MPI case, see `NNF_CONTAINER_LAUNCHER` below.

### SystemConfiguration Setup

In order for container workflows to request ports from the `NnfPortManager`, the
`SystemConfiguration` must be configured for a range of ports:

```yaml
kind: SystemConfiguration
metadata:
  name: default
  namespace: default
spec:
  # Ports is the list of ports available for communication between nodes in the
  # system. Valid values are single integers, or a range of values of the form
  # "START-END" where START is an integer value that represents the start of a
  # port range and END is an integer value that represents the end of the port
  # range (inclusive).
  ports:
    - 4000-4999
  # PortsCooldownInSeconds is the number of seconds to wait before a port can be
  # reused. Defaults to 60 seconds (to match the typical value for the kernel's
  # TIME_WAIT). A value of 0 means the ports can be reused immediately.
  # Defaults to 60s if not set.
  portsCooldownInSeconds: 60
```

`ports` is empty by default, and **must** be set by an administrator.

Multiple port ranges can be specified in this list, as well as single integers. This must be a safe
port range that does not interfere with the ephemeral port range of the Linux kernel. The range
should also account for the estimated number of simultaneous users that are running container
workflows.

Once a container workflow is done, the port is released and the `NnfPortManager` will not allow
reuse of the port until the amount of time specified by `portsCooldownInSeconds` has elapsed. Then
the port can be reused by another container workflow.

#### Restricting To User ID or Group ID

New NnfContainerProfile resources may be restricted to a specific user ID or group ID . When a
`data.userID` or `data.groupID` is specified in the profile, only those Workflow resources having a
matching user ID or group ID will be allowed to use that profile . If the profile specifies both of
these IDs, then the Workflow resource must match both of them.

## Creating a Container Workflow

The user's workflow will specify the name of the `NnfContainerProfile` in a DW directive. If the
custom profile is named `red-rock-slushy` then it will be specified in the `#DW container` directive
with the `profile` parameter.

```bash
#DW container profile=red-rock-slushy  [...]
```

Furthermore, to set the container storages for the workflow, storage parameters must also be
supplied in the workflow. This is done using the `<storage_name>` (see [Container
Storages](#container-storages)) and setting it to the name of a storage directive that defines an
NNF filesystem. That storage directive must already exist as part of another workflow (e.g.
persistent storage) or it can be supplied in the same workflow as the container. For global lustre,
the `LustreFilesystem` must exist that represents the global lustre filesystem.

In this example, we're creating a GFS2 filesystem to accompany the container directive. We're using
the `red-rock-slushy` profile which contains a non-optional storage called `DW_JOB_local_storage`:

```yaml
kind: NnfContainerProfile
metadata:
  name: red-rock-slushy
data:
  storages:
  - name: DW_JOB_local_storage
    optional: false
  mpiSpec:
    ...
```

The resulting container directive looks like this:

```bash
#DW jobdw name=my-gfs2 type=gfs2 capacity=100GB"
#DW container name=my-container profile=red-rock-slushy DW_JOB_local_storage=my-gfs2
```

Once the workflow progresses, this will create a 100GB GFS2 filesystem that is then mounted into the
container upon creation. An environment variable called `DW_JOB_local_storage` is made available
inside of the container and provides the path to the mounted NNF GFS2 filesystem. An application
running inside of the container can then use this variable to get to the filesystem mount directory.
See [here](#container-environment-variables).

Multiple storages can be defined in the container directives. Only one container directive is
allowed per workflow.

!!! note
    GFS2 filesystems have special considerations since the mount directory contains directories for
    every compute node. See [GFS2 Index Mounts](#gfs2-index-mounts) for more info.

### Targeting Nodes

For container directives, compute nodes must be assigned to the workflow. The NNF software will
trace the compute nodes back to their local NNF nodes and the containers will be executed on those
NNF nodes. The act of assigning compute nodes to your container workflow instructs the NNF software
to select the NNF nodes that run the containers.

For the `jobdw` directive that is included above, the servers (i.e. NNF nodes) must also be assigned
along with the computes.

## Running a Container Workflow

Once the workflow is created, the WLM progresses it through the following states. This is a quick
overview of the container-related behavior that occurs:

- Proposal: Verify [storages](#container-storages) are provided according to the container profile.
- Setup: If applicable, [request ports](#container-ports) from NnfPortManager.
- DataIn: No container related activity.
- PreRun: Appropriate `MPIJob` or `Job(s)` are created for the workflow. In turn, user containers
are created and launched by Kubernetes. Containers are expected to start in this state.
- PostRun: Once in PostRun, user containers are expected to complete (non-zero exit)
successfully.
- DataOut: No container related activity.
- Teardown: Ports are released; `MPIJob` or `Job(s)` are deleted, which in turn deletes the user
containers.

The two main states of a container workflow (i.e. PreRun, PostRun) are discussed further in the
following sections.

### PreRun

In PreRun, the containers are created and expected to start. Once the containers reach a
non-initialization state (i.e. Running), the containers are considered to be started and the
workflow can advance.

By default, containers are expected to start within 60 seconds. If not, the workflow reports an
Error that the containers cannot be started. This value is configurable via the
`preRunTimeoutSeconds` field in the container profile.

To summarize the PreRun behavior:

- If the container starts successfully (running), transition to `Completed` status.
- If the container fails to start, transition to the `Error` status.
- If the container is initializing and has not started after `preRunTimeoutSeconds` seconds,
terminate the container and transition to the `Error` status.

#### Init Containers

The NNF Software injects [Init
Containers](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/) into the container
specification to perform initialization tasks. These containers must run to completion before the
main container can start.

These initialization tasks include:

- Ensuring the proper permissions (i.e. UID/GID) are available in the main container
- For MPI jobs, ensuring the launcher pod can contact each worker pod via DNS

### PreRun Completed

Once PreRun has transitioned to `Completed` status, the user container is now running and the WLM
should initiate applications on the compute nodes. Utilizing [container ports](#container-ports),
the applications on the compute nodes can establish communication with the user containers, which
are running on the local NNF node attached to the computes.

This communication allows for the compute node applications to drive certain behavior inside of the
user container. For example, once the compute node application is complete, it can signal to the
user container that it is time to perform cleanup or data migration action.

### PostRun

In PostRun, the containers are expected to exit cleanly with a zero exit code. If a container fails to
exit cleanly, the Kubernetes software attempts a number of retries based on the
configuration of the container profile. It continues to do this until the container exits
successfully, or until the `retryLimit` is hit - whichever occurs first. In the latter case, the
workflow reports an Error.

Read up on the [Failure Retries](#failure-retries) for more information on retries.

Furthermore, the container profile features a `postRunTimeoutSeconds` field. If this timeout is
reached before the container successfully exits, it triggers an `Error` status. The timer for this
timeout begins upon entry into the PostRun phase, allowing the containers the specified period to
execute before the workflow enters an `Error` status.

#### Long-Running Processes

Some containers may run applications that are intended to run indefinitely (for example, an HTTP
server listening for requests). The copy-offload user container is one such example. These
long-running containers need a mechanism for a caller to stop them; otherwise, the `postRunTimeoutSeconds`
timeout will be reached, resulting in a workflow error.

During the PostRun phase, if containers are still running, the NNF software will attempt to send an
HTTPS POST request to the `/shutdown` endpoint on each user container. This process will continue
until the container receives the request and gracefully exits, or until the timeout is reached.

The software inside the container **must** be able to handle this request. The copy-offload user
container includes this functionality. If this functionality is not present, the container will need
to be terminated by some other means outside the container (for example, by the compute node
application when it is time to stop). The request is defined in the next section.

Alternatively, if `postRunTimeoutSeconds` is set to 0, the container exit codes will not be checked.
The software will ignore the result of the containers and proceed to the Teardown phase, where the
containers will be destroyed. This can be useful for long-running processes where the exit code is
not important.

#### Shutdown Request via `/shutdown` endpoint

The request is sent using HTTPS (TLS required; client verifies server using a CA certificate from
the Kubernetes `nnf-dm-usercontainer-server-tls` secret).

The token is taken from the workflow-specific token generated by the NNF software, if specified. See
the `requires=user-container-auth` argument in [Command
Arguments](../user-interactions/readme.md#command-arguments). Using this keyword in your directive
instructs the NNF software to create a workflow-specific token that is used here. If the `requires`
argument is not used, then no token will be generated, and no authorization will be sent in the
request.

Headers:

| Header           | Required | Example Value       | Description                                                         |
|------------------|----------|---------------------|---------------------------------------------------------------------|
| Content-Type     | Yes      | application/json    | Indicates the request body is JSON                                  |
| Authorization    | Optional | Bearer TOKEN...     | Bearer token for authentication (if token is requested by workflow) |
| X-Auth-Type      | Optional | XOAUTH2             | Indicates XOAUTH2 token type (if token is requested by workflow)    |

Request body:

```json
{
  "message": "shutdown"
}
```

The following is an example request that is sent to the copy-offload user containers using TLS:

```http
POST /shutdown HTTP/1.1
Host: nnf-node1:8080
Content-Type: application/json
Authorization: Bearer eyJhbG...
X-Auth-Type: XOAUTH2
Content-Length: 23

{"message": "shutdown"}
```

#### Recap

To recap the PostRun behavior:

- If the container exits successfully, transition to `Completed` status.
- If the container exits unsuccessfully after `retryLimit` number of retries, transition to the
  `Error` status.
- If the container is running and has not exited after `postRunTimeoutSeconds` seconds, terminate
  the container and transition to the `Error` status.
- If the container is running, a POST Request will be sent to the `/shutdown` endpoint on each
  container to attempt a graceful shutdown.
- If `postRunTimeoutSeconds` is set to zero, the container result will not be checked.

### Failure Retries

If a container fails (non-zero exit code), the Kubernetes software implements retries. The number of
retries can be set via the `retryLimit` field in the container profile. If a non-zero exit code is
detected, the Kubernetes software creates a new instance of the pod and retries. The
default number of retries for `retryLimit` is set to 6, which is the default value for Kubernetes
Jobs. This means that if the pods fails every single time, there will be 7 failed pods in total
since it attempted 6 retries after the first failure.

To understand this behavior more, see [Pod backoff failure
policy](https://kubernetes.io/docs/concepts/workloads/controllers/job/#pod-backoff-failure-policy)
in the Kubernetes documentation. This explains the retry (i.e. backoff) behavior in more detail.

It is important to note that due to the configuration of the `MPIJob` and/or `Job` that is created
for User Containers, the container retries are immediate - there is no backoff timeout between
retires. This is due to the NNF Software setting the `RestartPolicy` to `Never`, which causes a new
pod to spin up after every failure rather than re-use (i.e. restart) the previously failed pod. This
allows a user to see a complete history of the failed pod(s) and the logs can easily be obtained.
See more on this at [Handling Pod and container
failures](https://kubernetes.io/docs/concepts/workloads/controllers/job/#handling-pod-and-container-failures)
in the Kubernetes documentation.

## Putting it All Together

See the [NNF Container Example](https://github.com/NearNodeFlash/nnf-container-example) for a
working example of how to run a simple MPI application inside of an NNF User Container and run it
through a Container Workflow.

## Reference

### Environment Variables

Two sets of environment variables are available with container workflows: Container and Compute
Node. The former are the variables that are available inside the user containers. The latter are the
variables that are provided back to the DWS workflow, which in turn are collected by the WLM and
provided to compute nodes. See the WLM documentation for more details.

#### Container Environment Variables

These variables are provided for use inside the container. They can be used as part of the
container command in the NNF Container Profile or within the container itself.

##### Storages

Each storage defined by a container profile and used in a container workflow results in a
corresponding environment variable. This variable is used to hold the mount directory of the
filesystem.

###### GFS2 Index Mounts

When using a GFS2 file system, each compute is allocated its own NNF volume. The NNF software mounts
a collection of directories that are indexed (e.g. `0/`, `1/`, etc) to the compute nodes.

Application authors must be aware that their desired GFS2 mount-point really a collection of
directories, one for each compute node. It is the responsibility of the author to understand the
underlying filesystem mounted at the storage environment variable (e.g. `$DW_JOB_my_gfs2_storage`).

Each compute node's application can leave breadcrumbs (e.g. hostnames) somewhere on the GFS2
filesystem mounted on the compute node. This can be used to identify the index mount directory to a
compute node from the application running inside of the user container.

Here is an example of 3 compute nodes on an NNF node targeted in a GFS2 workflow:

```shell
$ ls $DW_JOB_my_gfs2_storage/*
/mnt/nnf/3e92c060-ca0e-4ddb-905b-3d24137cbff4-0/0
/mnt/nnf/3e92c060-ca0e-4ddb-905b-3d24137cbff4-0/1
/mnt/nnf/3e92c060-ca0e-4ddb-905b-3d24137cbff4-0/2
```

Node positions are _not_ absolute locations. The WLM could, in theory, select 6 physical compute
nodes at physical location 1, 2, 3, 5, 8, 13, which would appear as directories `/0` through `/5` in
the container mount path.

Additionally, not all container instances could see the same number of compute nodes in an
indexed-mount scenario. If 17 compute nodes are required for the job, WLM may assign 16 nodes to run
one NNF node, and 1 node to another NNF. The first NNF node would have 16 index directories, whereas
the 2nd would only contain 1.

##### Hostnames and Domains

Containers can contact one another via Kubernetes cluster networking. This functionality is provided
by DNS. Environment variables are provided that allow a user to be able to piece together the FQDN
so that the other containers can be contacted.

This example demonstrates an MPI container workflow, with two worker pods. Two worker pods means two
pods/containers running on two NNF nodes.

##### Ports

See the `NNF_CONTAINER_PORTS`[](#nnf_container_ports) section under [Compute Node Environment
Variables](#compute-node-environment-variables).

```console
mpiuser@my-container-workflow-launcher:~$ env | grep NNF
NNF_CONTAINER_HOSTNAMES=my-container-workflow-launcher my-container-workflow-worker-0 my-container-workflow-worker-1
NNF_CONTAINER_DOMAIN=default.svc.cluster.local
NNF_CONTAINER_SUBDOMAIN=my-container-workflow-worker
```

The container FQDN consists of the following: `<HOSTNAME>.<SUBDOMAIN>.<DOMAIN>`. To contact the
other worker container from worker 0,
`my-container-workflow-worker-1.my-container-workflow-worker.default.svc.cluster.local` would be
used.

For MPI-based containers, an alternate way to retrieve this information is to look at the default
`hostfile`, provided by `mpi-operator`. This file lists out all the worker nodes' FQDNs:

```console
mpiuser@my-container-workflow-launcher:~$ cat /etc/mpi/hostfile
my-container-workflow-worker-0.my-container-workflow-worker.default.svc slots=1
my-container-workflow-worker-1.my-container-workflow-worker.default.svc slots=1
```

#### Compute Node Environment Variables

These environment variables are provided to the compute node via the WLM by way of the DWS Workflow.
Note that these environment variables are consistent across all the compute nodes for a given
workflow.

!!! Note

    It's important to note that the variables presented here pertain exclusively to User
    Container-related variables. This list does not encompass the entirety of NNF environment
    variables accessible to the compute node through the Workload Manager (WLM)

#### `NNF_CONTAINER_PORTS`

If the NNF Container Profile requests container ports, then this environment variable provides the
allocated ports for the container. This is a comma separated list of ports if multiple ports are
requested.

This allows an application on the compute node to contact the user container running on its local
NNF node via these port numbers. The compute node must have proper routing to the NNF Node and needs
a generic way of contacting the NNF node.

For cases where one port is requested, the following can be used to contact the user container
running on the NNF node, assuming a hostname entry for the local rabbit is provided via `/etc/local-rabbit.conf` as described above:

```console
RABBIT=$(cat /etc/local-rabbit.conf)
$RABBIT:$(NNF_CONTAINER_PORTS)
```

Additionally, environment variables are also provided for each container defined in the container
profile. These variables include the name of the container.

```console
$NNF_CONTAINER_PORTS_my_container_name
$NNF_CONTAINER_PORTS_my_other_container_name
```

#### `NNF_CONTAINER_LAUNCHER`

If the NNF Container Profile is using `mpiSpec`, then this environment variable provides the name of the rabbit that is running the MPI Launcher pod.

This allows an application on the compute node to contact the user container running a server that may be in the MPI Launcher. The [copy-offload server](../data-movement/copy-offload.md) is an example of such an MPI application.

### Creating Images

For details, refer to the [NNF Container Example
Readme](https://github.com/NearNodeFlash/nnf-container-example#making-a-container-image). However,
in broad terms, an image that is capable of supporting MPI necessitates the following components:

- User Application: Your specific application
- Open MPI: Incorporate Open MPI to facilitate MPI operations
- SSH Server: Including an SSH server to enable communication
- nslookup: To validate Launcher/Worker container communication over the network

By ensuring the presence of these components, users can create an image that supports MPI operations
on the NNF platform.

The [nnf-mfu image](https://github.com/NearNodeFlash/nnf-mfu) serves as a suitable base image,
encompassing all the essential components required for this purpose.

### Using a Private Container Repository

The user's containerized application may be placed in a private repository . In
this case, the user must define an access token to be used with that repository,
and that token must be made available to the Rabbit's Kubernetes environment
so that it can pull that container from the private repository.

See [Pull an Image from a Private
Registry](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/) in
the Kubernetes documentation for more information.

#### About the Example

Each container registry will have its own way of letting its users create tokens to
be used with their repositories . Docker Hub will be used for the private repository in this
example, and the user's account on Docker Hub will be "dean".

#### Preparing the Private Repository

The user's application container is named "red-rock-slushy" . To store this container on Docker Hub
the user must log into docker.com with their browser and click the "Create repository" button to
create a repository named "red-rock-slushy", and the user must check the box that marks the
repository as private . The repository's name will be displayed as "dean/red-rock-slushy" with a
lock icon to show that it is private.

#### Create and Push a Container

The user will create their container image in the usual ways, naming it for their private repository
and tagging it according to its release.

Prior to pushing images to the repository, the user must complete a one-time login to the Docker
registry using the docker command-line tool.

```console
docker login -u dean
```

After completing the login, the user may then push their images to the repository.

```console
docker push dean/red-rock-slushy:v1.0
```

#### Generate a Read-Only Token

A read-only token must be generated to allow Kubernetes to pull that container
image from the private repository, because Kubernetes will not be running as that user . **This
token must be given to the administrator, who will use it to create a Kubernetes secret.**

To log in and generate a read-only token to share with the administrator, the user must follow these
steps:

- Visit docker.com and log in using their browser.
- Click on the username in the upper right corner.
- Select "Account Settings" and navigate to "Security".
- Click the "New Access Token" button to create a read-only token.
- Keep a copy of the generated token to share with the administrator.

#### Store the Read-Only Token as a Kubernetes Secret

The administrator must store the user's read-only token as a kubernetes secret . The secret must be
placed in the `default` namespace, which is the same namespace where the user containers will be
run . The secret must include the user's Docker Hub username and the email address they have
associated with that username . In this case, the secret will be named `readonly-red-rock-slushy`.

```console
USER_TOKEN=users-token-text
USER_NAME=dean
USER_EMAIL=dean@myco.com
SECRET_NAME=readonly-red-rock-slushy
kubectl create secret docker-registry $SECRET_NAME -n default --docker-server="https://index.docker.io/v1/" --docker-username=$USER_NAME --docker-password=$USER_TOKEN --docker-email=$USER_EMAIL
```

#### Add the Secret to the NnfContainerProfile

The administrator must add an `imagePullSecrets` list to the NnfContainerProfile resource that was
created for this user's containerized application.

The following profile shows the placement of the `readonly-red-rock-slushy` secret which was created
in the previous step, and points to the user's `dean/red-rock-slushy:v1.0` container.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha7
kind: NnfContainerProfile
metadata:
  name: red-rock-slushy
  namespace: nnf-system
data:
  pinned: false
  retryLimit: 6
  spec:
    imagePullSecrets:
    - name: readonly-red-rock-slushy
    containers:
    - command:
      - /users-application
      image: dean/red-rock-slushy:v1.0
      name: red-rock-app
  storages:
  - name: DW_JOB_foo_local_storage
    optional: false
  - name: DW_PERSISTENT_foo_persistent_storage
    optional: true
```

Now any user can select this profile in their Workflow by specifying it in a `#DW container`
directive.

```bash
#DW container profile=red-rock-slushy  [...]
```

#### Using a Private Container Repository for MPI Application Containers

If our user's containerized application instead contains an MPI application, because perhaps it's a
private copy of [nnf-mfu](https://github.com/NearNodeFlash/nnf-mfu), then the administrator would
insert two `imagePullSecrets` lists into the `mpiSpec` of the NnfContainerProfile for the MPI
launcher and the MPI worker.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha7
kind: NnfContainerProfile
metadata:
  name: mpi-red-rock-slushy
  namespace: nnf-system
data:
  mpiSpec:
    launcher:
      imagePullSecrets:
      - name: readonly-red-rock-slushy
      containers:
      - command:
        - mpirun
        - dcmp
        - $(DW_JOB_foo_local_storage)/0
        - $(DW_JOB_foo_local_storage)/1
        image: dean/red-rock-slushy:v2.0
        name: red-rock-launcher
    worker:
      imagePullSecrets:
      - name: readonly-red-rock-slushy
      containers:
      - image: dean/red-rock-slushy:v2.0
        name: red-rock-worker
    slotsPerWorker: 1
  pinned: false
  retryLimit: 6
  storages:
  - name: DW_JOB_foo_local_storage
    optional: false
  - name: DW_PERSISTENT_foo_persistent_storage
    optional: true
```

Now any user can select this profile in their Workflow by specifying it in a `#DW container`
directive.

```bash
#DW container profile=mpi-red-rock-slushy  [...]
```
