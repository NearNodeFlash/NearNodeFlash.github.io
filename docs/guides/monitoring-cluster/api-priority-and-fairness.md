# Kubernetes API Priority And Fairness

Kubernetes [API Priority and Fairness](https://kubernetes.io/docs/concepts/cluster-administration/flow-control/) (APF) allows requests to the Kubernetes API server to be classified, isolated, and queued in a fine-grained way.

The APF metrics can be monitored to determine how well the API servers are handling the workload. The metrics are intended to be interpreted by tools like [Prometheus](https://prometheus.io/) or [VictoriaMetrics](https://victoriametrics.com/). This document will use them in their raw form.

The metrics covered by this document are **counter** type. Counters are incremented, never decremented. While sampling counters in raw form, they will appear to bounce but on an idle system a given counter should make its current high value known after it appears in 3-5 samples.

## Concepts

Requests coming into the API server are classified by `FlowSchemas` and assigned to priority levels. The FlowSchema assigns the request to a **flow** and gives it a **flow distinguisher**. The flow distinguisher indicates the origin of the request--a user, service account, controller, namespace, or nothing. A priority level may take requests from multiple flows. The priority level attempts to give equal response time to each flow.

To view FlowSchemas and their assigned priority levels:

```console
kubectl get flowschemas
```

Flowschema sample output:

```bash
NAME                           PRIORITYLEVEL     MATCHINGPRECEDENCE   DISTINGUISHERMETHOD   AGE    MISSINGPL
[...]
system-leader-election         leader-election   100                  ByUser                112d   False
endpoint-controller            workload-high     150                  ByUser                112d   False
workload-leader-election       leader-election   200                  ByUser                112d   False
system-node-high               node-high         400                  ByUser                112d   False
system-nodes                   system            500                  ByUser                112d   False
[...]
```

To view priority levels:

```console
kubectl get prioritylevelconfiguration
```

Priority level sample output:

```bash
NAME              TYPE      NOMINALCONCURRENCYSHARES   QUEUES   HANDSIZE   QUEUELENGTHLIMIT   AGE
[...]
global-default    Limited   20                         128      6          50                 112d
leader-election   Limited   10                         16       4          50                 112d
node-high         Limited   40                         64       6          50                 112d
system            Limited   30                         64       6          50                 112d
workload-high     Limited   40                         128      6          50                 112d
workload-low      Limited   100                        128      6          50                 112d
[...]
```

## Metric types

As noted earlier, the metrics will be viewed in their raw form and they are all of **counter** type. An individual counter must be sampled multiple times before its current high value can be clearly identified.

To view a counter's type:

```console
kubectl get --raw /metrics | grep flowcontrol_rejected | grep '^#'
```

The output will describe the counter and its type:

```bash
# HELP apiserver_flowcontrol_rejected_requests_total [BETA] Number of requests rejected by API Priority and Fairness subsystem
# TYPE apiserver_flowcontrol_rejected_requests_total counter
```

## Examples

A quick way to get a summary of requests by priority level:

```console
kubectl get --raw /debug/api_priority_and_fairness/dump_priority_levels
```

From here one can drill down into the `Flowschemas` that feed a given priority level to see which one is generating the traffic.

View activity that uses the **nnf-clientmount** credentials:

```console
kubectl get --raw /metrics | grep 'flow_schema=\"nnf-clientmount\"' | head -6
```

View activity that uses the **viewer** user credential:

```console
kubectl get --raw /metrics | grep 'flow_schema=\"nodediag-kubectls\"' | head -6
```

## Resources

### Kubernetes

A description of APF:
[API Priority and Fairness](https://kubernetes.io/docs/concepts/cluster-administration/flow-control/)

Debugging guide:
[Flow Control](https://kubernetes.io/docs/reference/debug-cluster/flow-control/)

### Other sources

An excellent, though dated, description of tunables:
[Kubernetes API and flow control: Managing request quantity and queuing procedure](https://blog.palark.com/kubernetes-api-flow-control-management/)

Slide deck that gets into the algorithms:
[Kubernetes API Priority and Fairness](https://speakerdeck.com/ladicle/kubernetes-api-priority-and-fairness)
