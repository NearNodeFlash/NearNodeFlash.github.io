# fence_hpe_hss_ssh.py

## This agent is a work in progress and is not currently operational, it requires the following to be complete:
1. Logic to identify the Rabbit node based on the information passed in the pmck_host_list
2. A Kubernetes
   1. Role setup to read/write Storage CRDs
   2. Service Account for this agent
   3. RoleBinding to marry 1 & 2 above
   4. The SA cert & token to enabe access to the Kubernetes API and Storage CR
3. Properly formed k8s request to pull the Storage Spec
4. Logic to update the Storage Spec
5. Properly formed k8s request to update the Storage Spec

## Overview
fence_hpe_nnf.py is a fencing agent intended to run in a PaceMaker cluster environment.  This agent uses the Kubernetes API to mark a specific NNF node as Degrated.

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

*See fence_hpe_hss for more information on installation*

Typically the fencing agent is selected and setup using the PaceMaker CLI tool in the following fashion:

    # pcs stonith create gfs2_rabbit_nnf fence_hpe_nnf ip="10.1.1.6" pcmk_host_list="rabbit-node-1" ssh=1 username="<username>" password="<username>" op monitor interval=30s

    Note:
    * They don't make it easy to pass custom arguments in this framework, so recommend creating a config file under /etc for any additional info such as certs and tokens.

