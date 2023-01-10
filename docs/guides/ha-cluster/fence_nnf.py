#!@PYTHON@

# Fence agent for Near Node Flash devices

import sys
import logging
import atexit

sys.path.append("@FENCEAGENTSLIBDIR@")

from fencing import *
from fencing import fail, fail_usage, run_delay

try:
    from kubernetes import client
except ImportError:
    logging.error("Couldn't import kubernetes.client - not found or not accessible")

def get_power_status(api_client, options):
    # Power status is the status of the Kubernetes Node resource if it is down, or
    # the Fencing status of the NNF Node resource if the Kubernetes Node is up.

    name = options.get("--nnf-node-name")
    logging.debug("Reading node resource %s", name)

    try:
        node = client.CoreV1Api(api_client).read_node(name)

    except client.exceptions.ApiException as e:
        logging.debug("Exception when reading node: %s %s", e, type(e))
        if e.status == 401:
            fail(EC_LOGIN_DENIED)
        elif e.status == 404:
            fail(EC_STATUS)

        logging.error("Exception when reading node: %s %s", e, type(e))

    for condition in node.status.conditions:
        if condition.type == "Ready" and condition.status == "True":
            return _get_nnf_node_power_status(api_client, options)

    logging.info("Node %s is not ready", name)
    return "off"

def _get_nnf_node_power_status(api_client, options):

    version = options.get("--api-version")
    namespace = options.get("--nnf-node-name")
    logging.debug("Reading NNF node resource %s/%s", version, namespace)

    try:
        node = client.CustomObjectsApi(api_client).get_namespaced_custom_object(
            "nnf.cray.hpe.com",
            version,
            namespace,
            "nnfnodes",
            "nnf-nlc"
        )

    except client.exceptions.ApiException as e:
        logging.debug("Exception when reading NNF node: %s %s", e, type(e))
        if e.status == 404:
            fail(EC_STATUS)

        logging.error("Exception when reading NNF node: %s %s", e, type(e))

    fenced = node["status"].get("fenced", False)
    logging.info("NNF Node fenced status: %s", fenced)

    return "off" if fenced else "on"

def set_power_status(api_client, options):

    if options.get("--action") == "on":
        # NNF Fencing Agent is not permitted to enable the power status; that is done via
        # adminsitrator actions.
        return

    api_object = client.CustomObjectsApi(api_client)

    version = options.get("--api-version")
    namespace = options.get("--nnf-node-name")

    node = api_object.get_namespaced_custom_object(
        "nnf.cray.hpe.com",
        version,
        namespace,
        "nnfnodes",
        "nnf-nlc"
    )

    if not node["status"].get("fenced", False):
        node["status"]["fenced"] = True
        api_object.patch_namespaced_custom_object_status(
            "nnf.cray.hpe.com",
            version,
            namespace,
            "nnfnodes",
            "nnf-nlc",
            node
        )


def define_new_opts():
    all_opt["kubernetes-service-host"] = {
        "getopt" : ":",
        "longopt" : "kubernetes-service-host",
        "help" : "--kubernetes-service-host=[ADDRESS]   The IP Address of the kubeapi server",
        "shortdesc" : "Kubernetes API service IP address or hostname",
        "required" : "0",
        "order" : 1
    }

    all_opt["kubernetes-service-port"] = {
        "getopt" : ":",
        "longopt" : "kubernetes-service-port",
        "help" : "--kubernetes-service-port=[PORT]      The listen port of the kubeapi server",
        "shortdesc" : "Kubernetes API service port",
        "required" : "0",
        "order" : 1
    }

    all_opt["service-token-file"] = {
        "getopt" : ":",
        "longopt" : "service-token-file",
        "help" : "--service-token-file=[PATH]           The path to the service token file",
        "shortdesc" : "Path to the service token file",
        "required" : "1",
        "order" : 2
    }

    all_opt["service-cert-file"] = {
        "getopt" : ":",
        "longopt" : "service-cert-file",
        "help" : "--service-cert-file=[PATH]            The path to the service certificate file",
        "shortdesc" : "Path to the service certificate file",
        "required" : "1",
        "order" : 2
    }

    all_opt["nnf-node-name"] = {
        "getopt" : ":",
        "longopt" : "nnf-node-name",
        "help" : "--nnf-node-name=[PATH]                The name of the NNF node",
        "shortdesc" : "The name of the NNF node as listed in the system configuration",
        "required" : "1",
        "order" : 3
    }

    all_opt["api-version"] = {
        "getopt" : ":",
        "longopt" : "api-version",
        "help" : "--api-version=[VERSION]               Version of the NNF Node API",
        "shortdesc" : "The API Version of the NNF node resource",
        "required" : "0",
        "default" : "v1alpha1",
        "order" : 4
    }

    all_opt["localconfig"] = {
        "getopt" : "",
        "longopt" : "localconfig",
        "help" : "--localconfig                         Use the local kubernetes config",
        "required" : "0",
        "order" : 4
    }

def main():
    atexit.register(atexit_handler)

    device_opt = [
        "kubernetes-service-host", "kubernetes-service-port",
        "service-token-file", "service-cert-file",
        "nnf-node-name",
        "api-version",
        "localconfig",
        "no_password" # signals to fencing.py to disable password requirement
    ]

    define_new_opts()

    opt = process_input(device_opt)
    options = check_input(device_opt, opt)

    docs = {}
    docs["shortdesc"] = "Fencing agent for Near Node Flash"
    docs["longdesc"] = "fence_nnf is a fencing agent for Near Node Flash storage nodes."
    docs["vendorurl"] = "https://nearnodeflash.github.io/"
    show_docs(options, docs)

    run_delay(options)

    if "--localconfig" in options:
        from kubernetes import config
        configuration = config.load_kube_config()
    else:
        configuration = client.Configuration(
            host="https://%s:%s" % (
                options.get("--kubernetes-service-host"),
                options.get("--kubernetes-service-port")
            )
        )

        with open(options.get("--service-token-file"), "r") as f:
            token = f.read()

        configuration.api_key = { "authorization" : token }
        configuration.api_key_prefix = { "authorization" : "Bearer" }
        configuration.ssl_ca_cert = options.get("--service-cert-file")

    with client.ApiClient(configuration) as api_client:
        result = fence_action(api_client, options, set_power_status, get_power_status)

    sys.exit(result)

if __name__ == "__main__":
    main()