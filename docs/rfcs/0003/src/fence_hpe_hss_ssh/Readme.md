# fence_hpe_hss_ssh.py

## Overview
fence_hpe_hss_ssh.py is a fencing agent intended to run in a PaceMaker cluster environment.  This agent uses SSH to interact with the HSS redfish CLI to power a given node on or off.  The HSS redfish CLI offers the following usage:

    redfish node status
    redfish node [0-3] [on|off|forceoff]

It makes use of the fencing agent python library created by ClusterLabs to abstract much of the boilerplate so that only the actual fencing logic appears in the agent code.  The ClusterLabs github repository is located here:

https://github.com/ClusterLabs/fence-agents

The fencing library tends to live in /usr/share/fence, however installation locations may vary:

    # ls -l /usr/share/fence/fenc*
    -rwxr-xr-x. 1 root root 52344 Feb 11  2022 /usr/share/fence/fencing.py
    -rwxr-xr-x. 1 root root  3753 Feb 11  2022 /usr/share/fence/fencing_snmp.py

This agent works with Pacemaker 2.1 on TOSS 4.x
    # stonith_admin --version
    Pacemaker 2.1.0-8.el8
    # uname -a
    Linux rabbit-compute-3 4.18.0-348.20.1.2toss.t4.x86_64 #1 SMP Wed Apr 6 17:46:46 PDT 2022 x86_64 x86_64 x86_64 GNU/Linux    

## Installation    

It is recommended that you install the fencing agent package, which will include the appropriate python modules.

    dnf install fence-agents-common

To list recognized stonith agents:

    # pcs stonith list
    fence_ssh - Basic fencing agent that uses SSH
    fence_watchdog - Dummy watchdog fence agent


For a TOSS system, copy the fencing agent into /usr/sbin and make it executable.

    #
    # cp fence_hpe_hss_ssh.py /usr/sbin/fence_hpe_hss_ssh
    # chmod 755 /usr/sbin/fence_hpe_hss_ssh
    #
    # pcs stonith list
    fence_hpe_hss_ssh - Fence agent for HP HSS over SSH
    fence_ssh - Basic fencing agent that uses SSH
    fence_watchdog - Dummy watchdog fence agent


Typically the fencing agent is selected and setup using the PaceMaker CLI tool in the following fashion:

    # pcs stonith create gfs2_rabbit_hss fence_hpe_hss_ssh ip="10.1.1.6" pcmk_host_list="rabbit-node-1" ssh=1 username="<username>" password="<password>" op monitor interval=30s
    # pcs stonith status
      * rabbit-node-1       (stonith:fence_ssh):     Started rabbit-compute-2
      * rabbit-compute-2    (stonith:fence_ssh):     Started rabbit-compute-3
      * rabbit-compute-3    (stonith:fence_ssh):     Started rabbit-node-1
      * gfs2_rabbit_hss     (stonith:fence_hpe_hss_ssh):     Started rabbit-compute-3 (Monitoring)

