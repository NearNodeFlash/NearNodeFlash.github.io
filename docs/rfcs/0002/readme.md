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

The proposal below outlines the high level behavior of using containers:

1. The AUTHOR writes their application expecting NNF Storage at specific locations. For each storage requirement, they define:
    1. a unique name for the storage which can be referenced in the 'container' directive
    2. the expected storage types; if necessary
    3. the required mount path or mount path prefix
    4. other constraints or storage requirements (e.g. minimum capacity)
2. The AUTHOR works with the ADMINISTRATOR to define:
    1. a unique name for the program to be referred by USER
    2. the pod template specification for executing their program
    3. the NNF storage requirements described above.
3. The ADMINISTRATOR creates a corresponding _NNF Container Profile_ custom kubernetes resource with the necessary NNF storage requirements and pod specification as described by the AUTHOR
4. The USER who desires to use the application works with the AUTHOR and the related NNF Container Profile to understand the storage requirements
5. The USER submits a WLM job with the #DW container fields populated
6. WLM runs the job and drives the job through the following stages...
    1. `Proposal`: RABBIT validates the #DW container directive by comparing the supplied values to what is listed in the NNF Container Profile. If the USER fails to meet the requirements, the job fails
    2. `Setup`: RABBIT creates a pinned container profile for the workflow based on the supplied profile
    3. `PreRun`: RABBIT software will:
        1. create a config map reflecting the storage requirements and any runtime parameters; this is provided to the container at the volume mount named `nnf-config`, if specified
        2. duplicate the pod template specification from the Container Profile and patches the necessary Volumes and the config map. The spec is used as the basis for starting the necessary pods and containers.
        3. pods will be deployed using Jobs (1 job for each targeted Rabbit node) to allow for automated re-deployments upon failure
    4. The containerized application(s) executes. The expected mounts are available per the requirements and celebration occurs. Via jobs, the pods will continue to run until:
       1. the pod completes successfully
       2. timeout (i.e. `activeDeadlineSeconds`) is hit (optional)
       3. the max number of pod retries (i.e. `backoffLimit`) is hit (indicating failure and new retry pods)
          1. Note: retry limit is non-optional per Kubernetes Job configuration
          2. If retries are not desired, this number could be set to disable any retry attempts.
    5. `PostRun`: RABBIT software will:
       1. Roll up the Job completions for each Rabbit node to determine if the jobs/pods are ready to be removed
       2. Mark the stage as `Ready` if the Jobs are successful. This includes any successful retries after preceding failures
       3. Leave all jobs/pods around for log inspection
    6. `Teardown`: RABBIT software will remove the jobs and pods

### Communication Details

Other than mounts, the following subsections outline the proposed communication between the Rabbit nodes themselves and the Compute nodes.

#### Rabbit-to-Rabbit Communication

A headless kubernetes services will be deployed to connect the pods. This service will be unique to each container workflow. Each rabbit node would be
reached via `<host-name>.<service-name>`. The service-name would be provided to the application via a well-known environmental variable.
This has been prototyped and has proven to be successful.

#### Compute-to-Rabbit Communication

For Compute to Rabbit communication, the proposal is to use an open port between the nodes, so the applications could communicate using IP.
The port number would be assigned by the Rabbit software and included in the workflow resource's environmental variables after the Setup state (similar to workflow name & namespace).
Flux should provide the port number to the compute application via an environmental variable or command line argument. The containerized application
would always see the same port number using the `hostPort`/`containerPort` mapping functionality included in Kubernetes. To clarify, the Rabbit software is picking
and managing the ports picked for `hostPort`.

This would require a range of ports, to be listed as open in the firewall configuration and specified in the rabbit system configuration.
The fewer ports available would increase the chances of port reservation conflicts that could fail a job.

For safe port reusability, this port range must be large enough to account for the anticipated number of containerized jobs running concurrently. This allows time for the Linux kernel
to prepare a port for reusability. The kernel must take this port range into considering when defining the ephemeral port range.

#### Rabbit-to-Compute Communication

Same approach as above.

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
    activeDeadlineSeconds: 300
    backoffLimit: 3
    storages:
    - name: JOB_DW_foo-local-storage
      optional: false
    - name: PERSISTENT_DW_foo-persistent-storage
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
    JOB_DW_foo-local-storage=my-gfs2                  \
    PERSISTENT_DW_foo-persistent-storage=some-lustre
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
                JOB_DW_foo-local-storage:             type=gfs2   mount-type=indexed-mount
                PERSISTENT_DW_foo-persistent-storage: type=lustre mount-type=mount-point
        ```

    2. Rabbit software creates a Job and duplicates the `foo` pod template spec in the NNF Container Profile and fills in the necessary volumes and config map. 

        ```yaml
            kind: Job
            apiVersion: batch/v1
            metadata:
                name: my-job-container-my-foo
            spec:
              activeDeadlineSeconds: 300
              backoffLimit: 3
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
   1. Rabbit will wait for all jobs/pods to finish
   2. If all Jobs are successful, Post-Run will be marked as `Ready`
   3. If any Jobs is not successful, Post-Run will not be marked as `Ready`
5. Teardown:
   1. Jobs/Containers will be removed.

## Security

Kubernetes allows for a way to define permissions for a container using a [Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/). This can be seen in the pod template spec above. The user and group IDs will be inherited from the Workflow's spec.

## Special Note: Indexed-Mount Type

When using a file system like XFS or GFS2, each compute is allocated its own Rabbit volume. The Rabbit software mounts a collection of mount paths with a common prefix and an ending indexed value.

Application AUTHORS must be aware that their desired mount-point really contains a collection of directories, one for each compute node. The mount point type can be known by consulting the config map values.

If we continue the example from above, the `foo` application would expect the foo-local-storage path of `/foo/local` to contain several directories

```shell
$ ls /foo/local/*

node-0
node-1
node-2
...
node-N
```

Node positions are _not_absolute locations. WLM could, in theory, select 6 physical compute nodes at physical location 1, 2, 3, 5, 8, 13, which would appear as directories `/node-0` through `/node-5` in the container path.

Symlinks will be added to support the physical compute node names. Assuming a compute node hostname of `compute-node-1` from the example above, it would link to `node-0`, `compute-node-2` would link to `node-1`, etc.

Additionally, not all container instances could see the same number of compute nodes in an indexed-mount scenario. If 17 compute nodes are required for the job, WLM may assign 16 nodes to run one Rabbit, and 1 node to another Rabbit.
