---
authors: Tony Floeder <anthony.floeder@hpe.com>, Nate Thornton <nate.thornton@hpe.com>
categories: setup
---

# NVMe Drive Firmware

| Documentation Section  | Link                |
|------------------------|---------------------|
| Required Tools         | [Required Tools](#required-tools) |
| Installed Firmware     | [Querying Firmware](#querying-firmware) |
| Upgrade Procedure      | [Firmware Upgrade Procedure](#firmware-upgrade-procedure) |
| Notes                  | [Upgrade Notes](#upgrade-notes) |
| PAX Firmware           | [PCIe Switch Firmware Upgrade](#pcie-switch-firmware-upgrade) |

This guide presents the firmware upgrade procedures for NVMe drives attached to the Rabbit using tools present in the operating system.

## Required Tools

In order to upgrade the firmware on NVMe drives attached to Rabbit, the `switchtec` and `switchtec-nvme` executables must be installed. All firmware downloads to drives are sent to the physical function of the drive (the main interface of the NVMe device, as opposed to any virtual or secondary functions). The physical function is the primary PCIe endpoint that manages the device and is required for firmware operations. Access to the physical function is possible only using the `switchtec-nvme` executable. The helper script: [nnf-nvme.sh](https://github.com/NearNodeFlash/nnf-ec/blob/master/tools/nnf-nvme.sh) provides the mechanism to update drive firmware and query existing versions. [nnf-switch.sh](https://github.com/NearNodeFlash/nnf-ec/blob/master/tools/nnf-switch.sh) provides additional information about the PAX switch's view of the drive firmware configuration.

## Querying Firmware

Running the `nnf-switch.sh slot-info` command is the simplest method to see the active firmware for each drive.

```sh
./nnf-switch.sh slot-info
DEVICE: /dev/switchtec0 PAX_ID: 1

PDFID: 0x1900 SLOT: 04           KIOXIA YCU0A03H03A1 1TCRS104      /dev/nvme9  0000:83:00.0     Physical Port ID 8 (EP attached):
PDFID: 0x1500 SLOT: 05           KIOXIA YCU0A05Z03A1 1TCRS104     /dev/nvme10  0000:84:00.0     Physical Port ID 10 (EP attached):
PDFID: 0x1800 SLOT: 06           KIOXIA YCU0A02V03A1 1TCRS104     /dev/nvme11  0000:85:00.0     Physical Port ID 12 (EP attached):
PDFID: 0x1400 SLOT: 02           KIOXIA YCU0A04303A1 1TCRS104     /dev/nvme12  0000:86:00.0     Physical Port ID 14 (EP attached):
PDFID: 0x1600 SLOT: 09           KIOXIA YCU0A03B03A1 1TCRS104     /dev/nvme13  0000:88:00.0     Physical Port ID 18 (EP attached):
PDFID: 0x1700 SLOT: 10           KIOXIA YCU0A06103A1 1TCRS104     /dev/nvme14  0000:89:00.0     Physical Port ID 20 (EP attached):
PDFID: 0x1300 SLOT: 11           KIOXIA YCU0A00V03A1 1TCRS104     /dev/nvme15  0000:8a:00.0     Physical Port ID 22 (EP attached):
PDFID: 0x1a00 SLOT: 03           KIOXIA YCT0A06P03A1 1TCRS104     /dev/nvme16  0000:8b:00.0     Physical Port ID 48 (EP attached):

DEVICE: /dev/switchtec1 PAX_ID: 0

PDFID: 0x4200 SLOT: 08           KIOXIA YCT0A00H03A1 1TCRS104      /dev/nvme1  0000:05:00.0     Physical Port ID 8 (EP attached):
PDFID: 0x3d00 SLOT: 07           KIOXIA YCT0A06W03A1 1TCRS104      /dev/nvme2  0000:06:00.0     Physical Port ID 10 (EP attached):
PDFID: 0x3b00 SLOT: 15           KIOXIA YCU0A00F03A1 1TCRS104      /dev/nvme3  0000:07:00.0     Physical Port ID 12 (EP attached):
PDFID: 0x3e00 SLOT: 16           KIOXIA YCU0A05D03A1 1TCRS104      /dev/nvme4  0000:08:00.0     Physical Port ID 14 (EP attached):
PDFID: 0x4000 SLOT: 17           KIOXIA YCT0A00X03A1 1TCRS104      /dev/nvme5  0000:09:00.0     Physical Port ID 16 (EP attached):
PDFID: 0x3f00 SLOT: 18           KIOXIA YCU0A05E03A1 1TCRS104      /dev/nvme6  0000:0a:00.0     Physical Port ID 18 (EP attached):
PDFID: 0x3c00 SLOT: 14           KIOXIA YCT0A07A03A1 1TCRS104      /dev/nvme7  0000:0b:00.0     Physical Port ID 20 (EP attached):
PDFID: 0x4100 SLOT: 12           KIOXIA YCU0A00Z03A1 1TCRS104      /dev/nvme8  0000:0d:00.0     Physical Port ID 48 (EP attached):
```

Each NVMe drive supports three firmware slots, allowing up to three different firmware versions to be installed at once. To check the installed firmware versions on Rabbit drives, use the `nnf-nvme.sh cmd fw-log` command. The example below shows a factory configuration with `1TCRS104` firmware in all three slots; the `afi` value ("Active Firmware Image") indicates which slot is currently active (e.g., `afi : 0x1` means slot 1 is active, `afi : 0x2` means slot 2 is active, etc.).

**Note:** In this document, a "slot" refers to a firmware storage location on the NVMe drive. Each drive can hold up to three firmware images, one per slot.

```sh
./nnf-nvme.sh cmd fw-log
Executing fw-log for each drive on /dev/switchtec0
Executing fw-log for each drive on /dev/switchtec1
Execute on 0x1900@/dev/switchtec0 fw-log
Firmware Log for device:switchtec0
afi  : 0x1
frs1 : 0x3430315352435431 (1TCRS104)
frs2 : 0x3430315352435431 (1TCRS104)
frs3 : 0x3430315352435431 (1TCRS104)

... # The other 7 drives attached to /dev/switchtec0...

Execute on 0x4200@/dev/switchtec1 fw-log
Firmware Log for device:switchtec1
afi  : 0x1
frs1 : 0x3430315352435431 (1TCRS104)
frs2 : 0x3430315352435431 (1TCRS104)
frs3 : 0x3430315352435431 (1TCRS104)

... # The other 7 drives attached to /dev/switchtec1
```

## Firmware Upgrade Procedure

This section documents the drive firmware update procedure.
NOTE: The PAX switch allows a single drive firmware download at a time, but since there are 2 PAX switches in the Rabbit, `nnf-nvme.sh` downloads drive firmware to 2 drives concurrently. The output for the `update-firmware` operation thus waits until all operations complete.

1. **Initiate Firmware Update**

    ```sh
    time ./nnf-nvme.sh update-firmware ./1TCRS105.std --verbose

    KIOXIA NVMe Drive Firmware Update
    =================================

    Firmware file: ./1TCRS105.std
    New version: 105
    Dry run: false
    Verbose: true
    Force update: false

    Starting firmware update for 0x1900@/dev/switchtec0
    Processing device: 0x1900@/dev/switchtec0
    Found 3 firmware slots for 0x1900@/dev/switchtec0:
      Slot 1: 1TCRS104
      Slot 2: 1TCRS104
      Slot 3: 1TCRS104
    Oldest firmware found in slot 1: 1TCRS104
    New firmware version: 105
    Updating firmware on 0x1900@/dev/switchtec0 (slot 1) from 1TCRS104 to 105
    Downloading firmware to 0x1900@/dev/switchtec0...
    Firmware download success
    Firmware downloaded successfully to 0x1900@/dev/switchtec0
    Committing firmware to slot 1 on 0x1900@/dev/switchtec0...
    Success committing firmware action:0 slot:1
    Firmware committed successfully to slot 1 on 0x1900@/dev/switchtec0
    Activating firmware on 0x1900@/dev/switchtec0...
    Success committing firmware action:3 slot:0
    Firmware activated successfully on 0x1900@/dev/switchtec0
    Successfully updated firmware on 0x1900@/dev/switchtec0
    SUCCESS: Firmware update completed for 0x1900@/dev/switchtec0

    ... # The other 7 drives attached to /dev/switchtec0...

    Starting firmware update for 0x4200@/dev/switchtec1
    Processing device: 0x4200@/dev/switchtec1
    Found 3 firmware slots for 0x4200@/dev/switchtec1:
      Slot 1: 1TCRS104
      Slot 2: 1TCRS104
      Slot 3: 1TCRS104
    Oldest firmware found in slot 1: 1TCRS104
    New firmware version: 105
    Updating firmware on 0x4200@/dev/switchtec1 (slot 1) from 1TCRS104 to 105
    Downloading firmware to 0x4200@/dev/switchtec1...
    Firmware download success
    Firmware downloaded successfully to 0x4200@/dev/switchtec1
    Committing firmware to slot 1 on 0x4200@/dev/switchtec1...
    Success committing firmware action:0 slot:1
    Firmware committed successfully to slot 1 on 0x4200@/dev/switchtec1
    Activating firmware on 0x4200@/dev/switchtec1...
    Success committing firmware action:3 slot:0
    Firmware activated successfully on 0x4200@/dev/switchtec1
    Successfully updated firmware on 0x4200@/dev/switchtec1
    SUCCESS: Firmware update completed for 0x4200@/dev/switchtec1

    ... # The other 7 drives attached to /dev/switchtec1...

    real 4m24.395s
    user 0m0.161s
    sys 3m12.450s
    ```

    - This command runs the `update-firmware` function of `nnf-nvme.sh` targeting all drives and using the specified firmware file (`1TCRS105.std`).
    - The `--verbose` flag provides detailed output for each drive.
    - The duration for this operation was `4m 25s`.

2. **Verify Firmware Activation**

    ```sh
    ./nnf-nvme.sh cmd fw-log
    Executing fw-log for each drive on /dev/switchtec0
    Executing fw-log for each drive on /dev/switchtec1
    Execute on 0x1900@/dev/switchtec0 fw-log
    Firmware Log for device:switchtec0
    afi  : 0x1
    frs1 : 0x3530315352435431 (1TCRS105)
    frs2 : 0x3430315352435431 (1TCRS104)
    frs3 : 0x3430315352435431 (1TCRS104)
    ... # The other 7 drives attached to /dev/switchtec0...
    Execute on 0x4200@/dev/switchtec1 fw-log
    Firmware Log for device:switchtec1
    afi  : 0x1
    frs1 : 0x3530315352435431 (1TCRS105)
    frs2 : 0x3430315352435431 (1TCRS104)
    frs3 : 0x3430315352435431 (1TCRS104)
    ... # The other 7 drives attached to /dev/switchtec1

    ```

    - The firmware upgrade installed `1TCRS105` into slot 1.

3. **Power Cycle Rabbit System**

- Power cycle the Rabbit system, including all drives and PAX switches, to ensure reliable initialization.

## Upgrade Notes

`nnf-nvme.sh update-firmware` selects the slot containing the oldest firmware and installs the new drive firmware into that slot. If you run `nnf-nvme.sh update-firmware` 3 times, you would end up overwriting all 3 slots with the newer firmware. This is not recommended, but possible.

## PCIe Switch Firmware Upgrade

The supported approach to upgrade PCIe switch (PAX) firmware is via the redfish endpoint.
