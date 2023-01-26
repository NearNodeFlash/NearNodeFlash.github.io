---
authors: Tony Floeder <anthony.floeder@hpe.com>, Nate Thornton <nate.thornton@hpe.com>
categories: setup
---

# Firmware Upgrade Procedures

This guide presents the firmware upgrade procedures to upgrade firmware from the Rabbit using tools present in the operating system.

## PCIe Switch Firmware Upgrade

In order to upgrade the firmware on the PCIe switch, the `switchtec` kernel driver and utility of the same name must be installed. Rabbit hardware consists of two PCIe switches, which can be managed by devices typically located at `/dev/switchtec0` and `/dev/switchtec1`.

!!! danger
    Upgrading the switch firmware will cause the switch to reset. Prototype Rabbit units not supporting hotplug should undergo a power-cycle to ensure switch initialization following firmware uprade. Similarily, compute nodes not supporting hotplug may lose connectivity after firmware upgrade and should also be power-cycled.

```bash
IMAGE=$1 # Provide the path to the firmware image file
SWITCHES=("/dev/switchtec0" "/dev/switchtec1")
for SWITCH in $SWITCHES; do switchtec fw-update $SWITCH $IMAGE; done
```


## NVMe Drive Firmware Upgrade

In order to upgrade the firmware on NVMe drives attached to Rabbit, the `switchtec` and `switchtec-nvme` executables must be installed. All firmware downloads to drives are sent to the physical function of the drive which is accessible only using the `switchtec-nvme` executable.

### Batch Method

#### Download and Commit New Firmware

The [nvme.sh](https://github.com/NearNodeFlash/nnf-ec/blob/master/tools/nvme.sh) helper script applies the same command to each physical device fabric ID in the system. It provides a convenient way to upgrade the firmware on all drives in the system. Please see [fw-download](https://www.mankier.com/1/nvme-fw-download) and [fw-commit](https://www.mankier.com/1/nvme-fw-commit) for details about the individual commands.

```bash
# Download firmware to all drives
./nvme.sh cmd fw-download --fw=</path/to/nvme.fw>

# Commit the new firmware
# action=3: The image is requested to be activated immediately
./nvme.sh cmd fw-commit --action=3
```

#### Rebind the PCIe Connections

In order to use the drives at this point, they must be unbound and bound to the PCIe fabric to reset device connections. The [bind.sh](https://github.com/NearNodeFlash/nnf-ec/blob/master/tools/bind.sh) helper script performs these two actions. Its use is illustrated below.

```bash
# Unbind all drives from the Rabbit to disconnect the PCIe connection to the drives
./bind.sh unbind

# Bind all drives to the Rabbit to reconnect the PCIe bus
./bind.sh bind

# At this point, your drives should be running the new firmware.
# Verify the firmware...
./nvme.sh cmd id-ctrl | grep -E "^fr "
```

### Individual Drive Method

#### Determine Physical Device Fabric ID

The first step is to determine a drive's unique Physical Device Fabric Identifier (PDFID). The following code fragment demonstrates one way to list the physcial device fabric ids of all the NVMe drives in the system.

```bash
#!/bin/bash

SWITCHES=("/dev/switchtec0" "/dev/switchtec1")
for SWITCH in "${SWITCHES[@]}";
do
    mapfile -t PDFIDS < <(sudo switchtec fabric gfms-dump "${SWITCH}" | grep "Function 0 " -A1 | grep PDFID | awk '{print $2}')
    for INDEX in "${!PDFIDS[@]}";
    do
        echo "${PDFIDS[$INDEX]}@$SWITCH"
    done
done
```

```bash
# Produces a list like this:
0x1300@/dev/switchtec0
0x1600@/dev/switchtec0
0x1700@/dev/switchtec0
0x1400@/dev/switchtec0
0x1800@/dev/switchtec0
0x1900@/dev/switchtec0
0x1500@/dev/switchtec0
0x1a00@/dev/switchtec0
0x4100@/dev/switchtec1
0x3c00@/dev/switchtec1
0x4000@/dev/switchtec1
0x3e00@/dev/switchtec1
0x4200@/dev/switchtec1
0x3b00@/dev/switchtec1
0x3d00@/dev/switchtec1
0x3f00@/dev/switchtec1
```

#### Download Firmware

Using the physical device fabric identifier, the following commands update the firmware for specified drive.

```bash
# Download firmware to the drive
sudo switchtec-nvme fw-download <PhysicalDeviceFabricID> --fw=</path/to/nvme.fw>

# Activate the new firmware
# action=3: The image is requested to be activated immediately without reset.
sudo switchtec-nvme fw-commit --action=3
```

#### Rebind PCIe Connection

Once the firmware has been downloaded and committed, the PCIe connection from the Rabbit to the drive must be unbound and rebound. Please see [bind.sh](https://github.com/NearNodeFlash/nnf-ec/blob/master/tools/bind.sh) for details.
