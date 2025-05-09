# NVMe Disk Replacement Process

## Hardware Process

The Rabbit system does not support hot-swapping NVMe drives, meaning drives cannot be removed or replaced without first powering down the system. In the event of an NVMe drive failure, the Rabbit system must be powered down to replace the faulty drives.

After replacing the NVMe disks and powering the system back on:

- Any NVMe-hosted filesystems without redundancy will be lost.
- Filesystems with redundancy may be recoverable, provided the level of redundancy exceeds the number of NVMe devices replaced.

## Software Initialization

Rabbit-p system initialization launches the Kubernetes PODS. As part of the `nnf-node-manager` POD startup, the `nnf-ec` component initializes and retrieves the list of Storage Pools and Storage Groups previously created. A Storage Pool is a collection of NVMe namespaces, one per NVMe device, created as a set to be combined into either a Volume Group (VG) or zpool. A Storage Group is a mapping of a Storage Pool to a PCI endpoint to which the NVMe namespaces in the Storage Pool are attached.

<!-- add more details about the Storage Pool and Storage Group creation process here -->

## Rebuild Testing Notes

In order to test actions of Rabbit software components and prototype rebuild actions, there are tools configured on the texas:x9000c1j7b0n0 Rabbit-p that aid in testing.

`x9000c1j7b0n0:/mnt/per-host-cfg` is an NFS mount that hosted on `texas:/per-host-cfg`.

- `/per-host-cfg/tools` includes the tools from <https://github.com/NearNodeFlash/nnf-ec/tree/master/tools>
- `/per-host-cfg/scripts` includes the python scripts from <https://github.com/NearNodeFlash/nnf-ec/tree/master/tools>
- `/per-host-cfg/nnf-ec` includes the standalong `nnf-ec` linux binary along with the `nnf.db` directory which contains the `nnf-ec` badger database where the Storage Pools and Storage Groups that have been configured are stored.

### Setup

#### Tmux

You will thank yourself if you take the time to setup and use a `tmux` session. There is a tmux session running on `htx-lustre`.

- Create tmux session in conjunction with iTerm2

    ```shell
    [root@htx-lustre ~]# tmux -CC new -s ajf
    ```

- Reattach to that session later

    ```shell
    [root@htx-lustre ~]# tmux -CC attach -t ajf
    ```

#### Rebuild test setup overview

In order to simulate a drive replacement, the test setup below creates a set of storage pools and storage groups that expose NVMe devices to Rabbit-p. Those NVMe devices are incorporated into either a VG or zpool.

1. Delete one or more NVMe namespaces. This effectively is like removing the drive.
2. Restart `nnf-ec`. This effectively simulates a power cycle of the system.
3. `nnf-ec` recreates the missing namespaces setting up the condition of a Rabbit-p restart with a new drive. You may then test the incorporation of those namespaces into either the VG or the zpool.

#### SSH session setups

- **nnf-ec** - This session is where you run `nnf-ec`. The `-replaceMissingVolumes` parameter tells `nnf-ec` to look for namespaces that were part of a storage pool but are no longer there. If it detects this case, it attempts to find a new NVMe drive where a namespace can be create to replace the missing namespace. If found, `nnf-ec` creates a new namespace and replaces the missing namespace in the storage pool with the new namespace. `nnf-ec` iterates through all missing namespaces in a storage pool in like manner before iterating through the remaining storage pools. Once all namespaces have been replaced, the storage groups associated with modified storage pools are restored which causes new namespaces to be attached to the endpoint specified in the storage group.

    ```shell
    ./nnf-ec -http -deleteUnknownVolumes -replaceMissingVolumes
    ```

- **interactive.py** - This session is where you create your storage pools and storage groups
- **namespace deleter** - This session is where you run the command to delete namespaces out from underneath nnf-ec to simulate a drive loss. The following command deletes 10 namespaces from each of 2 drives.

    ```shell
    [root@x9000c1j7b0n0 tools]# for ((i=1; i<=10; i++)); do switchtec-nvme delete-ns 0x4100@/dev/switchtec1 --namespace-id="$i"; switchtec-nvme delete-ns 0x4200@/dev/switchtec1 --namespace-id="$i"; done
    ```

- **zpools creator**

    ```shell
    # Loop through 1..10 and a..j together
    for i in {1..10}; do
        letter=$(printf "\\x$(printf '%x' $((96 + i)))")
        ./zpool.sh create "$letter" "$i"
    done
    ```

- **vgs creator**

    ```shell
    # Loop through namespaces 1 to 10
    for i in {1..10}; do
        # Generate pool names a to j
        vg_name=$(echo $i | awk '{printf("%c", 96 + $1)}')

        ./lvm.sh create "$vg_name" "$i" raid6
    done

    for i in {1..10}; do
        vg_name=$(echo "$i" | awk '{printf("%c", 96 + $1)}')
    done
    ```

- **find-replacement-nvme-and-update-[vgs|zpools].sh**
These shell scripts look for `vgs|zpools` that are missing elements, then they attempt to assign NVMe namespaces to those `vgs|zpools`. This scripts search for replacement namespaces by size, thus *they are not suitable for production!!*. For production, we must assign a replacement namespace from the same storage pool in nnf-ec. For that, there were be changes to NNF controllers to incorporate.

    ```shell
    [root@x9000c1j7b0n0 tools]# ll find-replacement-nvme-and-update-*
    -rwxr-xr-x 1 root root 30021 May  2 15:09 find-replacement-nvme-and-update-vgs.sh
    -rwxr-xr-x 1 root root 46527 May  2 15:09 find-replacement-nvme-and-update-zpools.sh
    ```

The primary utility these scripts is to look at how to replace a missing namespace.

<!--- Stuff below here is relevant to the actual rebuild production implementation and needs work -->

## Background

Rabbit storage is managed through the interaction of several components within the NNF software stack. All storage-related information is communicated to the NNF software via the `Workflow` resource. This resource includes a `Servers` resource, which is updated to specify the Rabbit systems where storage is required for a given workflow. Once updated, the lower layers of the NNF software stack handle the necessary storage operations.

## Key Components

The following components play a critical role in Rabbit storage management:

- **NnfStorage**: Acts as the central control point for allocating and deallocating storage.
- **nnf-ec**: Manages NVMe namespaces that provide storage for filesystems.
- **NnfNodeBlockStorage**: Reflects information from `nnf-ec`, exposing OS-level device names associated with storage pool namespaces for filesystem creation, mounting, and unmounting.
- **NnfNodeStorage**: Provides a higher-level abstraction of the storage information.

These components work together to ensure efficient and reliable storage management within the Rabbit system.
