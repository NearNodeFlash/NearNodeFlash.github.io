# NNF User Containers

NNF User Containers are a mechanism to allow user-defined containerized
applications to be run on Rabbit nodes with access to NNF ephemeral and persistent storage.

!!! note

    The following is a limited look at User Containers.  More content will be
    provided after the RFC has been finalized.

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
$ USER_TOKEN=users-token-text
$ USER_NAME=dean
$ USER_EMAIL=dean@myco.com
$ SECRET_NAME=readonly-red-rock-slushy
$ kubectl create secret docker-registry $SECRET_NAME -n default --docker-server="https://index.docker.io/v1/" --docker-username=$USER_NAME --docker-password=$USER_TOKEN --docker-email=$USER_EMAIL
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

### Using a Private Version of MPI File Utils

If our user's containerized application instead contains MPI File Utils,
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


