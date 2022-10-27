---
authors: nate.roiger <nate.roiger@hpe.com>
categories: setup
---

# Compute Daemons

Rabbit software requires two daemons be installed and run on each compute node. Each daemon shares similar build, package, and installation processes described below.

- The [***Client Mount***](https://github.com/HewlettPackard/dws/tree/master/mount-daemon) daemon provides the support for mounting Rabbit hosted file systems on compute nodes.
- The [***Data Movement***](https://github.com/NearNodeFlash/nnf-dm/tree/master/daemons/compute) daemon supports creating, monitoring, and managing data movement (copy-offload) operations


## Building from source

Each daemon can be built in their respective repsitories using the `build-daemon` make target. Go version >= 1.19 must be installed to perform local build.

## RPM Package

Each daemon is packaged as part of the commit process. Source and Binary RPMs are available.

## Installation

For manual install, place the binary in the `/usr/bin/` directory.

To install the application as a daemon service, run `/usr/bin/[BINARY-NAME] install`

### Authentication

NNF software defines a Kubernetes Service Account for granting communication privledges between the daemon and the kubeapi server. The token file and certificate file can be obtained by providing the necessary Service Account and Namespace to the below shell script

| Compute Daemon | Service Account | Namespace |
| -------------- | --------------- | --------- |
| Client Mount   | dws-operator-controller-manager | dws-operator-system |
| Data Movement  | nnf-dm-controller-manager | nnf-dm-system |

```bash
#!/bin/bash

SERVICE_ACCOUNT=$1
NAMESPACE=$2

SECRET=$(kubectl get serviceaccount ${SERVICE_ACCOUNT} -n ${NAMESPACE} -o json | jq -Mr '.secrets[].name | select(contains("token"))')
kubectl get secret ${SECRET} -n ${NAMESPACE} -o json | jq -Mr '.data.token' | base64 -D > ./service.token
kubectl get secret ${SECRET} -n ${NAMESPACE} -o json | jq -Mr '.data["ca.crt"]' | base64 -D > ./service.cert
```

The `service.token` and `service.cert` files must be copied to each compute node, typically in the `/etc/[BINARY-NAME]/` directory

### Configuration

Installing the daemon will create a default configuration located at `/etc/systemd/system/[BINARY-NAME].service`

The arguments for execution that can be applied to the service definition or as an override file.

| Argument | Definition | 
| -------- | ---------- | 
| `--kubernetes-service-host=[ADDRESS]` | The IP address or DNS entry of the kubeapi server |
| `--kubernetes-service-port=[PORT]` | The listening port of the kubeapi servier |
| `--service-token-file=[PATH]` | Location of the service token file |
| `--service-cert-file=[PATH]` | Location of the service certificate file |
| `--node-name=[COMPUTE-NODE-NAME]` | Name of this compute node as described in the System Configuration |
| `--nnf-node-name=[RABBIT-NODE-NAME]` | Name of the rabbit node connected to this compute node as described in the System Configuration |

For example

```text title="cat /etc/systemd/system/nnf-dm.service"
[Unit]
Description=Near-Node Flash (NNF) Data Movement Service

[Service]
PIDFile=/var/run/nnf-dm.pid
ExecStartPre=/bin/rm -f /var/run/nnf-dm.pid
ExecStart=/usr/bin/nnf-dm \
   --kubernetes-service-host=172.0.0.1 \
   --kubernetes-service-port=7777 \
   --service-token-file=/path/to/service.token \
   --service-cert-file=/path/to/service.cert \
   --node-name=this-compute-node \
   --nnf-node-name=my-rabbit-node
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Easy Deployment

The nnf-deploy `install` command can be used to run the daemons on a system's set of compute nodes. This option will compile the latest daemon binaries, retrieve the service token and certificates, and will copy and install the daemon's on each of the compute nodes. Refer to the [nnf-deploy](https://github.com/NearNodeFlash/nnf-deploy) repsitory for details.

