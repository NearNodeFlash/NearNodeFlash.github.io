#! /usr/bin/env bash
# Copyright 2020, 2021, 2022 Hewlett Packard Enterprise Development LP
# Other additional copyright holders may be indicated within.
#
# The entirety of this work is licensed under the Apache License,
# Version 2.0 (the "License"); you may not use this file except
# in compliance with the License.
#
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Default config
KUSTOMIZE=/app/bin/kustomize
REPO_NNFDEPLOY="https://github.com/NearNodeFlash/nnf-deploy.git"
KUBECONFIG=/app/.kube/config
SMOKE_NAMESPACE="nnfsmoketest"
NAMESPACE_CREATED=0

# Operational controls
PREVIEW_MODE=0
IGNORE_DEVELOPER_USE=0
DO_SHOWCONFIG=0
DO_REBUILD=0
DO_DEPLOY=1
DO_UNDEPLOY=1
DO_CHECKS=1
DO_TESTS=1
DO_IGNORE_FAIL=1
DO_CLEANUP=1
VERBOSITY=0
EXIT_STATUS=0

# Error codes
ERR_BAD_ARG=1
ERR_IN_USE=2
ERR_NO_K8S_CONFIG=3
ERR_SMOKE_IN_PROGRESS=4
ERR_NODES_NOT_READY=10
ERR_NNFDEPLOY_MAKE_FAIL=20
ERR_NNFDEPLOY_UNDEPLOY_FAIL=21
ERR_NNFDEPLOY_DEPLOY_FAIL=22

function cleanup() {
    if [[ $NAMESPACE_CREATED -ne 0 ]]; then
        if [[ $PREVIEW_MODE == 1 ]]; then
        output "Delete namespace $SMOKE_NAMESPACE" "PREVIEW"
        else
            kubectl delete namespace $SMOKE_NAMESPACE
        fi
    fi
}

function usage() {
    cat usage.txt
    exit 0
}

function output() {
    PREFIX="${2:-INFO   }"
    date +"%Y-%m-%d %H:%M:%S $PREFIX $1"
}

function error() {
    output "$1" "ERROR  "
}

function fatal_error() {
    error "A fatal error has occurred, aborting run"
    exit $1
}

function debug() {
    if [ $1 -le $VERBOSITY ]
    then
        output $2, "DBG $1  "
    fi
}

function verifyUndeploy() {
    output "Verifying Undeploy"
}

function verifyDeploy() {
    output "Verifying Undeploy"
    
}

output "NearNodeFlash Smoke Test - version 0.6"
CWD=`pwd`
output "Running in folder ${CWD}"

# ***************************************************
# * Establish sane defaults
# ***************************************************
if [ ! -z "$KUBECONFIG" ]
then
    export KUBECONFIG=/app/.kube/config
fi

# ***************************************************
# * Process arguments
# ***************************************************
while [[ $# -gt 0 ]]
do
    debug 3 "ARG $1"
    case $1 in
        "-?"|-h|--help)
            usage
            ;;
        -v)
            VERBOSITY=$((VERBOSITY+1))
            #echo "VERBOSITY increase to $VERBOSITY"
            ;;
        --show-config)
            DO_SHOWCONFIG=1
            output "Ignoring previous failures"
            ;;
        --ignore-dev)
            IGNORE_DEVELOPER_USE=1
            output "Ignoring any developer in use namespaces"
            ;;
        --ignore-fail)
            DO_IGNORE_FAIL=1
            output "Ignoring previous failures"
            ;;
        -k|--kube)
            shift
            KUBECONFIG=$1
            debug 2 "KUBECONFIG=$KUBECONFIG"
            ;;
        --undeploy_only)
            shift
            DO_DEPLOY=0
            DO_CHECKS=0
            DO_TESTS=0
            output "Running in undeploy mode only"
            ;;
        --allways_rebuild)
            shift
            DO_REBUILD=1
            ;;
        --nodeploy)
            shift
            DO_DEPLOY=0
            ;;
        --noundeploy)
            shift
            DO_UNDEPLOY=0
            ;;
        --preview)
            shift
            PREVIEW_MODE=1
            ;;
        *)
            error "Unknown argument: $1"
            EXIT_STATUS=$ERR_BAD_ARG
    esac
    shift
done

# ***************************************************
# * Check mounts / smoke test setup
# ***************************************************
# - expected default directory structure
# -     /app/.kube/config            - Kubernetes configuration file for the environment to be tested
# -        /app/tests                        - Tests to be executed
if [ ! -e "$KUBECONFIG" ]
then
    error "Kubernetes config $KUBECONFIG is missing.  You must set the value of KUBECONFIG to an existing file OR mount /app/.kube/config into the smoke test container."
    EXIT_STATUS=$ERR_NO_K8S_CONFIG
fi

if [ ! -d "/app/tests" ]
then
    output "/app/tests folder has not been mounted, only default test runs will occur.", "WARNING"
fi

if [ $EXIT_STATUS -ne 0 ]
then
    fatal_error $EXIT_STATUS
fi

# Extract the context and server from the k8s config
KCONTEXT=`yq eval '.current-context' $KUBECONFIG`
KSERVER=`yq eval ".clusters[] | select(.name == \"$KCONTEXT\").cluster.server" $KUBECONFIG`
output "k8s context: $KCONTEXT, k8s server: $KSERVER"
if [[ $KSERVER == *"localhost"* || $KSERVER == *"127.0.0.1"* ]]; then
    output "server url points to localhost, this should probably an IP or valid hostname" "WARNING"
fi

# ***************************************************
# * Check cluster state
# ***************************************************
DEVELOPER_NS=`kubectl get ns | awk '{print $1}' | tr '[:upper:]' '[:lower:]' | grep -e dean -e nate -e tony -e blake -e matt`
if [[ $? -eq 0 ]]; then
    output "Cluster is in use by the following developer(s)"
    output "   - $DEVELOPER_NS"
    if [[ $IGNORE_DEVELOPER_USE == 1 ]]; then
        output "...ignoring developer namespace" "WARNING"
    else
           fatal_error $ERR_IN_USE
    fi
fi

SIFS=$IFS
for node in `kubectl get nodes | sed '1d' | awk '{printf "%s,%s\n", \$1,\$2}'`; do
    IFS=","
    read -a nodedetail <<< "$node"
    if [[ ${nodedetail[1]} == "Ready" ]]; then
        output "Node: ${nodedetail[0]} is Ready"
    else
        output "Node: ${nodedetail[0]} is NOT Ready ( ${nodedetail[1]} )"
        EXIT_STATUS=$ERR_NODES_NOT_READY
    fi
done

if [ $EXIT_STATUS -ne 0 ]
then
    fatal_error $EXIT_STATUS
fi

if [[ $DO_SHOWCONFIG == 1 ]]; then
    exit 0
fi

# ***************************************************
# * Check for previous failed tests
# ***************************************************
output "Looking for previous test failures"
kubectl get ns | awk '{print $1}' | tr '[:upper:]' '[:lower:]' | grep -e $SMOKE_NAMESPACE
if [[ $? -eq 0 ]]; then
    if [[ $DO_IGNORE_FAIL == 0 ]]; then
        output "$SMOKE_NAMESPACE exists which indicates previous test failure"
        fatal_error $ERR_SMOKE_IN_PROGRESS
    else
        output "$SMOKE_NAMESPACE exists, IGNORING previous test failure"
    fi
fi

# ***************************************************
# * Prepare clean test environment
# ***************************************************
output "Preparing test environment"
NAMESPACE_CREATED=1
if [[ $PREVIEW_MODE == 1 ]]; then
    output "Creating namespace $SMOKE_NAMESPACE" "PREVIEW"
else
    kubectl create namespace $SMOKE_NAMESPACE
fi

output "Acquiring nnf-deploy"
if [[ -e nnf-deploy ]] && [[ $DO_REBUILD == 1 ]]; then
    output "always_rebuild specified, deleting existing nnf-deploy folder"
    rm -rf nnf-deploy 2>/dev/null
fi

if [[ $PREVIEW_MODE == 0 ]]; then
    if [ -e nnf-deploy ]; then
        output "nnf-deploy folder already exists, skipping git pull"
    else
        git clone $REPO_NNFDEPLOY
    fi
    cd nnf-deploy 
fi

echo "------------ Updating .gitmodules ------------" 
if [[ $PREVIEW_MODE == 0 ]]; then
    sed -i 's/git@github.com:/https:\/\/github.com\//' .gitmodules 
fi

output "Preparing and building nnf-deploy"
if [[ $PREVIEW_MODE == 0 ]]; then
    git submodule init
    git submodule update
    go mod vendor
    go mod tidy
    go build
fi

if [[ $DO_UNDEPLOY == 1 ]]; then
    output "Undeploying previous software"
    if [[ $PREVIEW_MODE -eq 0 ]]; then
       ./nnf-deploy undeploy; RETCODE=$?
       if [[ $RETCODE -ne 0 ]]; then
           error "nnf-deploy Undeploy returned non-zero exit status $RETCODE"
            fatal_error $ERR_NNFDEPLOY_UNDEPLOY_FAIL
       fi
    fi

    # Validate undeployment
    # - PODs
    # - CRs
    # - Namespaces

fi

if [[ $DO_DEPLOY == 1 ]]; then
    output "Building current Rabbit software"
    cd /app/nnf-deploy
    if [[ $PREVIEW_MODE -eq 0 ]]; then
        ./nnf-deploy Make
        if [[ $? -ne 0 ]]; then
            error "nnf-deploy Make returned non-zero exit status"
            fatal_error $ERR_NNFDEPLOY_MAKE_FAIL
        fi
    fi

    output "Deploying current Rabbit software"
    if [[ $PREVIEW_MODE -eq 0 ]]; then
        ./nnf-deploy Deploy
        if [[ $? -ne 0 ]]; then
            error "nnf-deploy Deploy returned non-zero exit status"
            fatal_error $ERR_NNFDEPLOY_DEPLOY_FAIL
        fi
    fi
fi

# ***************************************************
# * Run tests
# ***************************************************
output "Test runs beginning"
if [[ $PREVIEW_MODE == 0 ]]; then
    # TODO: Implement tests
    output "Running test xyz"
fi

# ***************************************************
# * Evaluate exit conditions
# ***************************************************
# TODO: Evaluate test success/failure
output "Test runs complete"

cleanup()

exit 0
