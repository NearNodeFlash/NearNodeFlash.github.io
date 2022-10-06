Rabbit storage for containerized applications
=============================================

**authors**: Nate Roiger <nate.roiger@hpe.com> |
**state**: ideation

---

For Rabbit to provide storage to a containerized application there needs to be _some_ mechanism. The remainder of this RFC proposes that mechanism.

Actors
------

There are several different actors involved

- The AUTHOR of the containerized application
- The ADMINISTRATOR who works with the author to determine the application requirements for execution
- The USER who intends to to use the application using the 'container' directive in their job specification
- The RABBIT software that interprets the #DWs and starts the container during execution of the job

There are multiple relationships between the actors:
- AUTHOR to ADMINISTRATOR: The author defines how their application is executed and the NNF storage requirements
- Between the AUTHOR and USER: The application expects certain storage, and the #DW must meet those expectations.
- ADMINISTRATOR to RABBIT: Admin tells Rabbit how to run the container
- Between USER and RABBIT: User provides the #DW container directive in the job specification, and Rabbit validates & interprets the directive.

Proposal
--------

The proposal below might take a couple of read-throughs; I've also added a concrete example afterward that might help.

1. The AUTHOR writes their application expecting NNF Storage at specific locations. For each storage requirement, they define...
    1. a unique name for the storage which can be referenced in the 'container' directive
    2. the expected storage types; if necessary
    3. the required mount path or mount path prefix
    4. other constraints or storage requirements (i.e. minimum capacity)
2. The AUTHOR works with the ADMINISTRATOR to define, a unique name for the program, the pod specification for executing their program, and the NNF storage requirements described above. The ADMINISTRATOR creates a corresponding _NNF Container Profile_ custom kubernetes resource.
3. The USER who desires to use the application works with the AUTHOR and the related Container Profile to understand the storage requirements.
4. The USER submits a WLM job with the #DW container fields populated
5. WLM runs the job and drives the job through the following stages...
    1. Proposal: RABBIT validates the #DW container directive by comparing the supplied values to what is listed in the Container Profile. If the USER fails to meet the requirements, the job fails.
    2. Pre-run: RABBIT software...
        1. creates a config map reflecting the storage requirements and any runtime parameters
        2. duplicates the pod specification from the Container Profile and patches the necessary Volumes and the config map. The spec is used as the basis for starting the necessary pods and containers.
    3. The containerized application executes. The expected mounts are available per the requirements and celebration occurs.

Example
-------

Say I authored a simple application, `foo`, that requires Rabbit local GFS2 storage and a persistent Lustre storage volume. As the author, my program is coded to expect the GFS2 volume is mounted at `/foo/local` and the Lustre volume is mounted at `/foo/persistent`

Working with an administrator, my applications storage requirements and pod specification are placed in an NNF Container Profile `foo`

```yaml
kind: NnfContainerProfile
apiVersion: v1alpha1
metadata:
    name: foo
    namespace: default
spec:
    storages:
    - name: $JOB_DW_foo-local-storage
      type: gfs2
    - name: $PERSISTENT_DW_foo-persistent-storage
      type: lustre
    podSpec:
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
```

Say Peter wants to use `foo` as part of his job specification. Peter would submit the job with the below directives

```
#DW jobdw name=my-gfs2 type=gfs2 capacity=1TB

#DW persistentdw name=some-lustre

#DW container name=my-foo profile=foo               \
    $JOB_DW_foo-local-storage=my-gfs2                 \
    $PERSISTENT_DW_foo-persistent-storage=some-lustre
```

Peter submits the job to the WLM. WLM guides the job through the workflow states:
1. Proposal: Rabbit software verifies the #DW directives. For the container directive, the requirements of Container Profile `foo`, that is `foo-local-storage` and `foo-persistent-storage`, are provided and correct.
2. Setup: Since there is a jobdw `my-gfs2`, Rabbit software provisions this storage.
3. Pre-Run:
    1. Rabbit software generates a config map that corresponds to the storage requirements and runtime parameters.

    ```yaml
    kind: ConfigMap
    apiVersion: v1
    metadata:
        name: my-job-container-my-foo
    data:
        $JOB_DW_foo-local-storage:             type=gfs2   mount-type=indexed-mount
        $PERSISTENT_DW_foo-persistent-storage: type=lustre mount-type=mount-point
    ```
    2. Rabbit software duplicates the `foo` pod spec in the Container Profile and fills in the necessary volumes and config map.

    ```yaml
    kind: Pod
    apiVersion: v1
    metadata:
        name: my-job-container-my-foo
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
        
          # This volumeMount added by Rabbit software
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



Special Note: Indexed-Mount type
--------------------------------

When using a file system like GFS2, each compute is allocated its own Rabbit volume. The Rabbit software mounts a collection of mount paths with a common prefix and an ending indexed value. 

Application authors must be aware that their desired mount-point really contains a collection of directories, one for each compute node. The mount point type can be known by consulting the config map values

If we continue the example from above, the `foo` application would expect the foo-local-storage path of `/foo/local` to contain several directories

```
# ls /foo/local/*

node-0
node-1
node-2
...
node-N
```

Node positions are ***not*** absolute locations. WLM could, in theory, select physical 6 compute nodes at physical location 1, 2, 3, 5, 8, 13, which would appear as directories /node-0 through /node-5