# NNF User Containers

NNF User Containers are a mechanism to allow user-defined containerized
applications to be run on Rabbit nodes with access to NNF ephemeral and persistent storage.

!!! note

    The following is a limited look at User Containers.  More content will be
    provided after the RFC has been finalized. This is a work in progress.

## Environment Variables

Two sets of environment variables are available with container workflows: Container and Compute Node. The former are the variables that are available inside the user containers. The latter are the variables that are provided back to the DWS workflow, which in turn are collected by the WLM and provided to compute nodes. See the WLM documentation for more details.

### Container Environment Variables

These variables are provided for use inside the container. They can be used as part of the
container command in the NNF Container Profile or within the container itself.

#### Container Hostnames and Domains

Containers can contact one another via Kubernetes cluster networking. This functionality is provided by DNS. Environment variables are provided that allow a user to be able to piece together the FQDN so that the other containers can be contacted.

This example demonstrates an MPI container workflow, with two worker pods. Two worker pods means two pods/containers running on two NNF nodes.

```console
mpiuser@my-container-workflow-launcher:~$ env | grep NNF
NNF_CONTAINER_HOSTNAMES=my-container-workflow-launcher my-container-workflow-worker-0 my-container-workflow-worker-1
NNF_CONTAINER_DOMAIN=default.svc.cluster.local
NNF_CONTAINER_SUBDOMAIN=my-container-workflow-worker
```

The container FQDN consists of the following: `<HOSTNAME>.<SUBDOMAIN>.<DOMAIN>`. To contact the other worker container from worker 0, `my-container-workflow-worker-1.my-container-workflow-worker.default.svc.cluster.local` would be used.

For MPI-based containers, an alternate way to retrieve this information is to look at the default `hostfile`, provided by `mpi-operator`. This file lists out all the worker nodes' FQDNs:

```console
mpiuser@my-container-workflow-launcher:~$ cat /etc/mpi/hostfile
my-container-workflow-worker-0.my-container-workflow-worker.default.svc slots=1
my-container-workflow-worker-1.my-container-workflow-worker.default.svc slots=1
```

### Compute Node Environment Variables

These environment variables are provided to the compute node via the WLM by way of the DWS Workflow. Note that these environment variables are consistent across all the compute nodes for a given workflow.

#### `NNF_CONTAINER_PORTS`

If the NNF Container Profile requests container ports, then this environment variable provides the allocated ports for the container. This is a comma separated list of ports if multiple ports are requested.

This allows an application on the compute node to contact the user container running on its local NNF node via these port numbers. The compute node must have proper routing to the NNF Node and needs a generic way of contacting the NNF node. It is suggested than a DNS entry is provided via `/etc/hosts`, or similar.

For cases where one port is requested, the following can be used to contact the user container running on the NNF node (assuming an entry for `local-rabbit` is provided via `/etc/hosts`).

```console
local-rabbit:$(NNF_CONTAINER_PORTS)
```

## Container Ports

NNF Container Profiles allow for ports to be reserved for a container workflow. `numPorts` can be used to specify the number of ports needed for a container workflow:

```yaml
kind: NnfContainerProfile
metadata:
  name: sample-nnfcontainerprofile
  namespace: nnf-system
data:
  # Request the number of ports to open on the targeted rabbits. These ports are accessible outside
  # of the k8s cluster.  The requested ports are made available as environment variables inside the
  # container and in the DWS workflow (NNF_CONTAINER_PORTS).
  numPorts: 1
```

The allocated port numbers are made available via the [`NNF_CONTAINER_PORTS`](#nnf_container_ports) environment variable.

The workflow requests this number of ports from the `NnfPortManager`, which is responsible for managing the ports allocated to container workflows. This resource can be inspected to see which ports are allocated.

These ports are opened on the NNF Nodes that are targeted by the container workflow. When a port is assigned, it becomes "reserved" for all NNF Nodes in the system. This reservation occurs even if the port is unused by the NNF Nodes not involved in the specific container workflow. To clarify, if port 4001 is employed by a container workflow that targets 6 out of 10 NNF Nodes within the system, any subsequent workflow cannot utilize port 4001 on the remaining 4 NNF Nodes.

!!! note

    The `SystemConfiguration` must be configured to allow for a range of ports, otherwise container workflows will fail in the `Setup` state due to insufficient resources. See [SystemConfiguration Setup](#systemconfiguration-setup).

### SystemConfiguration Setup

In order for container workflows to request ports from the `NnfPortManager`, the `SystemConfiguration` must be configured for a range of ports:

```yaml
kind: SystemConfiguration
metadata:
  name: default
  namspace: default
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

Multiple port ranges can be specified in this list, as well as single integers. This must be a safe port range that does not interfere with the ephemeral port range of the Linux kernel. The range should also account for the estimated number of simultaneous users that are running container workflows.

Once a container workflow is done, the port is released and the `NnfPortManager` will not allow reuse of the port until the amount of time specified by `portsCooldownInSeconds` has elapsed. Then the port can be reused by another container workflow.

## Custom NnfContainerProfile

The author of a containerized application will work with the administrator to
define a pod specification template for the container and to create an
appropriate NnfContainerProfile resource for the container.  The image and tag
for the user's container will be specified in the profile.

New NnfContainerProfile resources may be created by copying one of the provided
example profiles from the `nnf-system` namespace.  The examples may be found by listing them with `kubectl`:

```console
kubectl get nnfcontainerprofiles -n nnf-system
```

### Workflow Job Specification

The user's workflow will specify the name of the NnfContainerProfile in a DW
directive.  If the custom profile is named `red-rock-slushy` then it will be
specified in the "#DW container" directive with the "profile" parameter.

```bash
#DW container profile=red-rock-slushy  [...]
```

### Restricting To User ID or Group ID

New NnfContainerProfile resources may be restricted to a specific user ID
or group ID.  When a `data.userID` or `data.groupID` is specified in the profile, only
those Workflow resources having a matching user ID or group ID will be allowed to
use that profile.  If the profile specifies both of these IDs, then the Workflow
resource must match both of them.

## Using a Private Container Repository

The user's containerized application may be placed in a private repository.  In
this case, the user must define an access token to be used with that repository,
and that token must be made available to the Rabbit's Kubernetes environment
so that it can pull that container from the private repository.

See [Pull an Image from a Private Registry](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/) in the Kubernetes documentation
for more information.

### About the Example

Each container registry will have its own way of letting its users create tokens to
be used with their repositories.  Docker Hub will be used for the private repository in this example, and the user's account on Docker Hub will be "dean".

### Preparing the Private Repository

The user's application container is named "red-rock-slushy".  To store this container
on Docker Hub the user must log into docker.com with their browser and click the "Create repository" button to create a repository named "red-rock-slushy", and the user must check the box that marks the repository as private.  The repository's name will be displayed as "dean/red-rock-slushy" with a lock icon to show that it is private.

### Create and Push a Container

The user will create their container image in the usual ways, naming it for their private repository and tagging it according to its release.

Prior to pushing images to the repository, the user must complete a one-time login to the Docker registry using the docker command-line tool.

```console
docker login -u dean
```

After completing the login, the user may then push their images to the repository.

```console
docker push dean/red-rock-slushy:v1.0
```

### Generate a Read-Only Token

A read-only token must be generated to allow Kubernetes to pull that container
image from the private repository, because Kubernetes will not be running as
that user.  **This token must be given to the administrator, who will use it to create a Kubernetes secret.**

To log in and generate a read-only token to share with the administrator, the user must follow these steps:

- Visit docker.com and log in using their browser.
- Click on the username in the upper right corner.
- Select "Account Settings" and navigate to "Security".
- Click the "New Access Token" button to create a read-only token.
- Keep a copy of the generated token to share with the administrator.

### Store the Read-Only Token as a Kubernetes Secret

The adminstrator must store the user's read-only token as a kubernetes secret.  The
secret must be placed in the `default` namespace, which is the same namespace
where the user containers will be run.  The secret must include the user's Docker
Hub username and the email address they have associated with that username.  In
this case, the secret will be named `readonly-red-rock-slushy`.

```console
USER_TOKEN=users-token-text
USER_NAME=dean
USER_EMAIL=dean@myco.com
SECRET_NAME=readonly-red-rock-slushy
kubectl create secret docker-registry $SECRET_NAME -n default --docker-server="https://index.docker.io/v1/" --docker-username=$USER_NAME --docker-password=$USER_TOKEN --docker-email=$USER_EMAIL
```

### Add the Secret to the NnfContainerProfile

The administrator must add an `imagePullSecrets` list to the NnfContainerProfile
resource that was created for this user's containerized application.

The following profile shows the placement of the `readonly-red-rock-slushy` secret
which was created in the previous step, and points to the user's
`dean/red-rock-slushy:v1.0` container.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
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

Now any user can select this profile in their Workflow by specifying it in a
`#DW container` directive.

```bash
#DW container profile=red-rock-slushy  [...]
```

### Using a Private Container Repository for MPI Application Containers

If our user's containerized application instead contains an MPI application,
because perhaps it's a private copy of [nnf-mfu](https://github.com/NearNodeFlash/nnf-mfu),
then the administrator would insert two `imagePullSecrets` lists into the
`mpiSpec` of the NnfContainerProfile for the MPI launcher and the MPI worker.

```yaml
apiVersion: nnf.cray.hpe.com/v1alpha1
kind: NnfContainerProfile
metadata:
  name: mpi-red-rock-slushy
  namespace: nnf-system
data:
  mpiSpec:
    mpiImplementation: OpenMPI
    mpiReplicaSpecs:
      Launcher:
        template:
          spec:
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
      Worker:
        template:
          spec:
            imagePullSecrets:
            - name: readonly-red-rock-slushy
            containers:
            - image: dean/red-rock-slushy:v2.0
              name: red-rock-worker
    runPolicy:
      cleanPodPolicy: Running
      suspend: false
    slotsPerWorker: 1
    sshAuthMountPath: /root/.ssh
  pinned: false
  retryLimit: 6
  storages:
  - name: DW_JOB_foo_local_storage
    optional: false
  - name: DW_PERSISTENT_foo_persistent_storage
    optional: true
```

Now any user can select this profile in their Workflow by specifying it in a
`#DW container` directive.

```bash
#DW container profile=mpi-red-rock-slushy  [...]
```
