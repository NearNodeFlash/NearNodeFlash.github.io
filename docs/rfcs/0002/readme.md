---
authors: Nate Thornton <nate.thornton@hpe.com>
state: discussion
---
# Rabbit storage for containerized applications

For Rabbit to provide storage to a containerized application there needs to be _some_ mechanism. The remainder of this RFC proposes that mechanism.

## Actors

There are several actors involved:

- The AUTHOR of the containerized application
- The ADMINISTRATOR who works with the author to determine the application requirements for execution
- The USER who intends to use the application using the 'container' directive in their job specification
- The RABBIT software that interprets the #DWs and starts the container during execution of the job

There are multiple relationships between the actors:

- AUTHOR to ADMINISTRATOR: The author tells the administrator how their application is executed and the NNF storage requirements.
- Between the AUTHOR and USER: The application expects certain storage, and the #DW must meet those expectations.
- ADMINISTRATOR to RABBIT: Admin tells Rabbit how to run the containerized application with the required storage.
- Between USER and RABBIT: User provides the #DW container directive in the job specification. Rabbit validates and interprets the directive.

## Proposal

The proposal below outlines the high level behavior of running containers in a workflow:

1. The AUTHOR writes their application expecting NNF Storage at specific locations. For each storage requirement, they define:
    1. a unique name for the storage which can be referenced in the 'container' directive
    2. the expected storage types; if necessary
    3. the required mount path or mount path prefix
    4. other constraints or storage requirements (e.g. minimum capacity)
2. The AUTHOR works with the ADMINISTRATOR to define:
    1. a unique name for the program to be referred by USER
    2. the pod template specification for executing their program
    3. the NNF storage requirements described above.
3. The ADMINISTRATOR creates a corresponding _NNF Container Profile_ Kubernetes custom resource with the necessary NNF storage requirements and pod specification as described by the AUTHOR
4. The USER who desires to use the application works with the AUTHOR and the related NNF Container Profile to understand the storage requirements
5. The USER submits a WLM job with the #DW container directive variables populated
6. WLM runs the workflow and drives it through the following stages...
    1. `Proposal`: RABBIT validates the #DW container directive by comparing the supplied values to those listed in the NNF Container Profile. If the workflow fails to meet the requirements, the job fails
    2. `PreRun`: RABBIT software:
        1. creates a config map reflecting the storage requirements and any runtime parameters; this is provided to the container at the volume mount named `nnf-config`, if specified
        2. duplicates the pod template specification from the Container Profile and patches the necessary Volumes and the config map. The spec is used as the basis for starting the necessary pods and containers
    3. The containerized application(s) executes. The expected mounts are available per the requirements and celebration occurs. The pods continue to run until:
       1. a pod completes successfully (any failed pods will be retried)
       2. the max number of pod retries is hit (indicating failure on all retry attempts)
          1. Note: retry limit is non-optional per Kubernetes configuration
          2. If retries are not desired, this number could be set to 0 to disable any retry attempts
    4. `PostRun`: RABBIT software:
       1. marks the stage as `Ready` if the pods have all completed successfully. This includes a successful retry after preceding failures
       2. starts a timer for any running pods. Once the timeout is hit, the pods will be killed and the workflow will indicate failure
       3. leaves all pods around for log inspection

### Container Assignment to Rabbit Nodes

During `Proposal`, the USER must assign compute nodes for the container workflow. The assigned
compute nodes determine which Rabbit nodes run the containers.

### Communication Details

The following subsections outline the proposed communication between the Rabbit nodes themselves and
the Compute nodes.

#### Rabbit-to-Rabbit Communication

Each rabbit node can be reached via `<hostname>.<subdomain>` using DNS. The hostname is a
combination of the workflow name and Rabbit node name. The workflow name is used for the subdomain.

For example, a workflow name of `foo` that targets `rabbit-node2` would be `foo-rabbit-node2.foo`.

Environment variables are provided to the container and ConfigMap for each rabbit that is targeted
by the container workflow:

```shell
RABBIT_HOSTS=foo-rabbit-node2,foo-rabbit-node3
RABBIT_SUBDOMAIN=foo
RABBIT_DOMAIN=default.svc.cluster.local
```

```yaml
kind: ConfigMap
apiVersion: v1
data:
  rabbitHosts:
    - foo-rabbit-node2
    - foo-rabbit-node3
  rabbitSubdomain: foo
  rabbitDomain: default.svc.cluster.local
```

DNS can then be used to communicate with other Rabbit containers. The FQDN for the container running on rabbit-node2 is `foo-rabbit-node2.foo.default.svc.cluster.local`.

#### Compute-to-Rabbit Communication

For Compute to Rabbit communication, the proposal is to use an open port between the nodes, so the
applications could communicate using IP protocol.  The port number would be assigned by the Rabbit
software and included in the workflow resource's environmental variables after the Setup state
(similar to workflow name & namespace).  Flux should provide the port number to the compute
application via an environmental variable or command line argument. The containerized application
would always see the same port number using the `hostPort`/`containerPort` mapping functionality
included in Kubernetes. To clarify, the Rabbit software is picking and managing the ports picked for
`hostPort`.

This requires a range of ports to be open in the firewall configuration and specified in the rabbit
system configuration. The fewer the number of ports available increases the chances of a port
reservation conflict that would fail a workflow.

Example port range definition in the SystemConfiguration:

```yaml
apiVersion: v1
items:
  - apiVersion: dws.cray.hpe.com/v1alpha1
    kind: SystemConfiguration
      name: default
      namespace: default
    spec:
      containerHostPortRangeMin: 30000
      containerHostPortRangeMax: 40000
      ...
```

## Example

Say I authored a simple application, `foo`, that requires Rabbit local GFS2 storage and a persistent Lustre storage volume. As the author,
my program is coded to expect the GFS2 volume is mounted at `/foo/local` and the Lustre volume is mounted at `/foo/persistent`

Working with an administrator, my application's storage requirements and pod specification are placed in an NNF Container Profile `foo`:

```yaml
kind: NnfContainerProfile
apiVersion: v1alpha1
metadata:
    name: foo
    namespace: default
spec:
    postRunTimeout: 300
    maxRetries: 6
    storages:
    - name: DW_JOB_foo-local-storage
      optional: false
    - name: DW_PERSISTENT_foo-persistent-storage
      optional: false
    template:
        metadata:
            name: foo
            namespace: default
        spec:
            containers:
            - name: foo
              image: foo:latest
              command:
              - /foo
              volumeMounts:
              - name: foo-local-storage
                mountPath: /foo/local
              - name: foo-persistent-storage
                mountPath: /foo/persistent
              - name: nnf-config
                mountPath: /nnf/config
              ports:
              - name: compute
                containerPort: 80
```

Say Peter wants to use `foo` as part of his job specification. Peter would submit the job with the directives below:

```text
#DW jobdw name=my-gfs2 type=gfs2 capacity=1TB

#DW persistentdw name=some-lustre

#DW container name=my-foo profile=foo                 \
    DW_JOB_foo-local-storage=my-gfs2                  \
    DW_PERSISTENT_foo-persistent-storage=some-lustre
```

Since the NNF Container Profile has specified that both storages are not optional (i.e. `optional: false`), they must both be present in the #DW directives along with the `container` directive. Alternatively, if either was marked as optional (i.e. `optional: true`), it would not be required to be present in the #DW directives and therefore would not be mounted into the container.

Peter submits the job to the WLM. WLM guides the job through the workflow states:

1. Proposal: Rabbit software verifies the #DW directives. For the container directive `my-foo` with profile `foo`, the storage requirements listed in the NNF Container Profile are `foo-local-storage` and `foo-persistent-storage`. These values are correctly represented by the directive so it is valid.
2. Setup: Since there is a jobdw, `my-gfs2`, Rabbit software provisions this storage.
3. Pre-Run:
    1. Rabbit software generates a config map that corresponds to the storage requirements and runtime parameters.

        ```yaml
            kind: ConfigMap
            apiVersion: v1
            metadata:
                name: my-job-container-my-foo
            data:
                DW_JOB_foo-local-storage:             type=gfs2   mount-type=indexed-mount
                DW_PERSISTENT_foo-persistent-storage: type=lustre mount-type=mount-point
                ...
        ```

    2. Rabbit software creates a pod and duplicates the `foo` pod template spec in the NNF Container Profile and fills in the necessary volumes and config map.

        ```yaml
            kind: Pod
            apiVersion: v1
            metadata:
                name: my-job-container-my-foo
            template:
                metadata:
                    name: foo
                    namespace: default
                spec:
                    containers:
                    # This section unchanged from Container Profile
                    - name: foo
                      image: foo:latest
                      command:
                        - /foo
                      volumeMounts:
                      - name: foo-local-storage
                        mountPath: /foo/local
                      - name: foo-persistent-storage
                        mountPath: /foo/persistent
                      - name: nnf-config 
                        mountPath: /nnf/config
                      ports:
                        - name: compute
                          hostPort: 9376 # hostport selected by Rabbit software
                          containerPort: 80

                    # volumes added by Rabbit software
                    volumes:
                    - name: foo-local-storage
                      hostPath:
                        path: /nnf/job/my-job/my-gfs2
                    - name: foo-persistent-storage
                      hostPath:
                        path: /nnf/persistent/some-lustre
                    - name: nnf-config
                      configMap:
                        name: my-job-container-my-foo

                    # securityContext added by Rabbit software - values will be inherited from the workflow
                    securityContext:
                      runAsUser: 1000
                      runAsGroup: 2000
                      fsGroup: 2000
        ```

    3. Rabbit software starts the pods on Rabbit nodes
4. Post-Run
   1. Rabbit waits for all pods to finish (or until timeout is hit)
   2. If all pods are successful, Post-Run is marked as `Ready`
   3. If any pod is not successful, Post-Run is not marked as `Ready`

## Security

Kubernetes allows for a way to define permissions for a container using a [Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/). This can be seen in the pod template spec above. The user and group IDs are inherited from the Workflow's spec.

## Special Note: Indexed-Mount Type

When using a file system like XFS or GFS2, each compute is allocated its own Rabbit volume. The Rabbit software mounts a collection of mount paths with a common prefix and an ending indexed value.

Application AUTHORS must be aware that their desired mount-point really contains a collection of directories, one for each compute node. The mount point type can be known by consulting the config map values.

If we continue the example from above, the `foo` application expects the foo-local-storage path of `/foo/local` to contain several directories

```shell
$ ls /foo/local/*

node-0
node-1
node-2
...
node-N
```

Node positions are _not_ absolute locations. WLM could, in theory, select 6 physical compute nodes at physical location 1, 2, 3, 5, 8, 13, which would appear as directories `/node-0` through `/node-5` in the container path.

Symlinks will be added to support the physical compute node names. Assuming a compute node hostname of `compute-node-1` from the example above, it would link to `node-0`, `compute-node-2` would link to `node-1`, etc.

Additionally, not all container instances could see the same number of compute nodes in an indexed-mount scenario. If 17 compute nodes are required for the job, WLM may assign 16 nodes to run one Rabbit, and 1 node to another Rabbit.
