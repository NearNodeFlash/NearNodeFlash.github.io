---
authors: nate.roiger <nate.roiger@hpe.com>
state: discussion
---
Rabbit storage for containerized applications
=============================================

For Rabbit to provide storage to a containerized application there needs to be _some_ mechanism. The remainder of this RFC proposes that mechanism.

Actors
------

There are several different actors involved

- The AUTHOR of the containerized application
- The ADMINISTRATOR who works with the author to determine the application requirements for execution
- The USER who intends to to use the application using the 'container' directive in their job specification
- The RABBIT software that interprets the #DWs and starts the container during execution of the job

There are multiple relationships between the actors

- AUTHOR to ADMINISTRATOR: The author tells the administrator how their application is executed and the NNF storage requirements.
- Between the AUTHOR and USER: The application expects certain storage, and the #DW must meet those expectations.
- ADMINISTRATOR to RABBIT: Admin tells Rabbit how to run the containerized application with the required storage.
- Between USER and RABBIT: User provides the #DW container directive in the job specification. Rabbit validates and interprets the directive.

Proposal
--------

The proposal below might take a couple of read-throughs; I've also added a concrete example afterward that might help.

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
4. The USER who desires to use the application works with the AUTHOR and the related NNF Container Profile to understand the storage requirements.
5. The USER submits a WLM job with the #DW container fields populated
6. WLM runs the job and drives the job through the following stages...
    1. Proposal: RABBIT validates the #DW container directive by comparing the supplied values to what is listed in the NNF Container Profile. If the USER fails to meet the requirements, the job fails. 
    2. Pre-run: RABBIT software will:
        1. create a config map reflecting the storage requirements and any runtime parameters; this is provided to the container at the volume mount named "nnf-config", if specified.
        2. duplicate the pod template specification from the Container Profile and patches the necessary Volumes and the config map. The spec is used as the basis for starting the necessary pods and containers.
    3. The containerized application executes. The expected mounts are available per the requirements and celebration occurs.

Example
-------

Say I authored a simple application, `foo`, that requires Rabbit local GFS2 storage and a persistent Lustre storage volume. As the author, my program is coded to expect the GFS2 volume is mounted at `/foo/local` and the Lustre volume is mounted at `/foo/persistent`

Working with an administrator, my application's storage requirements and pod specification are placed in an NNF Container Profile `foo`:

```yaml
kind: NnfContainerProfile
apiVersion: v1alpha1
metadata:
    name: foo
    namespace: default
spec:
    storages:
    - name: JOB_DW_foo-local-storage
      type: gfs2
    - name: PERSISTENT_DW_foo-persistent-storage
      type: lustre
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
```

Say Peter wants to use `foo` as part of his job specification. Peter would submit the job with the directives below:

```
#DW jobdw name=my-gfs2 type=gfs2 capacity=1TB

#DW persistentdw name=some-lustre

#DW container name=my-foo profile=foo                 \
    JOB_DW_foo-local-storage=my-gfs2                  \
    PERSISTENT_DW_foo-persistent-storage=some-lustre
```

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
    2. Rabbit software duplicates the `foo` pod template spec in the NNF Container Profile and fills in the necessary volumes and config map.
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
```
    3. Rabbit software starts the pods on Rabbit nodes



Special Note: Indexed-Mount Type
--------------------------------

When using a file system like XFS or GFS2, each compute is allocated its own Rabbit volume. The Rabbit software mounts a collection of mount paths with a common prefix and an ending indexed value. 

Application AUTHORS must be aware that their desired mount-point really contains a collection of directories, one for each compute node. The mount point type can be known by consulting the config map values.

If we continue the example from above, the `foo` application would expect the foo-local-storage path of `/foo/local` to contain several directories

```
# ls /foo/local/*

node-0
node-1
node-2
...
node-N
```

Node positions are ***not*** absolute locations. WLM could, in theory, select 6 physical compute nodes at physical location 1, 2, 3, 5, 8, 13, which would appear as directories `/node-0` through `/node-5` in the container path.

Additionally, not all container instances could see the same number of compute nodes in an indexed-mount scenario. If 17 compute nodes are required for the job, WLM may assign 16 nodes to run one Rabbit, and 1 node to another Rabbit.

Special Note: MPI Applications
------------------------------

A USER who writes an application using MPI can have RABBIT software execute the the application using mpirun. To specify an MPI program, the NNF Container Profile contains the boolean value "mpi" in the specification.

```yaml
kind: NnfContainerProfile
apiVersion: v1alpha1
metadata:
    name: bar-mpi
    namespace: default
spec:
  mpi: "true"
  storages: // ...
  template: // ...
```

A container that specifies MPI uses Kubeflow's [MPI Operator](https://www.kubeflow.org/docs/components/training/mpi/). MPI Workers are started on each Rabbit that is part of the workflow, and an MPI Launcher is used to execute the mpirun command itself.